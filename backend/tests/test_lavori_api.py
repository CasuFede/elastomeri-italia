"""Test end-to-end del router Lavori (scheda tecnica, stratigrafia, media multipli e Range 206)."""
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from core.database import CloudflareServices, get_environment, get_services
from core.security import crea_token_sessione
from main import app


class SqliteMockStatement:
    def __init__(self, conn: sqlite3.Connection, query: str):
        self.conn = conn
        self.query = query
        self.params: tuple = ()

    def bind(self, *params):
        self.params = params
        return self

    async def all(self):
        cur = self.conn.execute(self.query, self.params)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        self.conn.commit()

        class Res:
            results = rows

        return Res()

    async def run(self):
        self.conn.execute(self.query, self.params)
        self.conn.commit()
        return None


class SqliteMockD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        mig_dir = Path(__file__).resolve().parent.parent / "migrations"
        self.conn.executescript((mig_dir / "0001_initial.sql").read_text(encoding="utf-8"))
        self.conn.executescript((mig_dir / "0006_lavori_dettagli_media.sql").read_text(encoding="utf-8"))
        self.conn.commit()

    def prepare(self, query: str):
        return SqliteMockStatement(self.conn, query)


class MockR2Head:
    def __init__(self, size: int):
        self.size = size


class MockR2Object:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self) -> bytes:
        return self._data


class MemoryMockR2:
    def __init__(self):
        self.store: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes):
        self.store[key] = bytes(data)

    async def delete(self, key: str):
        self.store.pop(key, None)

    async def head(self, key: str):
        if key not in self.store:
            return None
        return MockR2Head(len(self.store[key]))

    async def get(self, key: str):
        if key not in self.store:
            return None
        return MockR2Object(self.store[key])


class MockEnv:
    def __init__(self):
        self.DB = SqliteMockD1()
        self.UPLOADS = MemoryMockR2()
        self.ADMIN_USERNAME = "admin"
        self.ADMIN_PASSWORD = "testpassword123"
        self.SESSION_SECRET = "testsecret123"


@pytest.fixture
def lavori_client():
    env = MockEnv()
    app.state.env = env
    app.dependency_overrides[get_environment] = lambda: env
    app.dependency_overrides[get_services] = lambda: CloudflareServices(database=env.DB, uploads=env.UPLOADS)
    client = TestClient(app)
    token = crea_token_sessione("admin", "admin", "testsecret123")
    client.cookies.set("poliurea_admin_session", token)
    yield client, env
    client.cookies.clear()
    app.dependency_overrides.clear()
    app.state.env = None


def test_ciclo_completo_lavoro_con_foto_video_e_range(lavori_client):
    client, env = lavori_client

    # 1. Crea lavoro completo via JSON
    payload = {
        "titolo": "Terrazzo condominiale 250 mq — Poliurea a freddo",
        "categoria": "Terrazzi e lastrici",
        "localita": "Genova Albaro",
        "superficie_mq": 250,
        "supporto": "Piastrelle in gres esistenti",
        "ciclo_sistema": "Poliurea a freddo bicomponente",
        "armatura": "Fascia di rinforzo su giunti e risvolti",
        "applicazione": "Rullo e spatola senza demolizione",
        "descrizione": "Impermeabilizzazione completa senza rimozione pavimentazione.",
        "stratigrafia_descrizione": "Primer epossidico, prima mano poliurea a freddo, seconda mano di chiusura anti-UV.",
        "stratigrafia_fasi": [
            {"fase": "01", "titolo": "Preparazione e primer", "dettaglio": "Levigatura e primer epossidico."},
            {"fase": "02", "titolo": "Membrana poliureica", "dettaglio": "Due mani incrociate a freddo."},
        ],
    }
    res_create = client.post("/api/lavori", json=payload)
    assert res_create.status_code == 201, res_create.text
    lavoro_id = res_create.json()["id"]

    # 2. Carica foto Prima, foto Dopo e Video del Dopo con poster
    fake_jpg = b"\xff\xd8\xff\xe0" + b"0" * 128
    fake_webp = b"RIFF\x20\x00\x00\x00WEBP" + b"1" * 128
    fake_mp4 = b"\x00\x00\x00\x18ftypisom" + bytes(range(256)) * 4

    r_prima = client.post(
        f"/api/lavori/{lavoro_id}/media",
        data={"tipo": "prima", "didascalia": "Stato iniziale piastrelle", "ordine": "0"},
        files={"file": ("prima.jpg", fake_jpg, "image/jpeg")},
    )
    assert r_prima.status_code == 201, r_prima.text
    prima_id = r_prima.json()["id"]

    r_dopo = client.post(
        f"/api/lavori/{lavoro_id}/media",
        data={"tipo": "dopo", "didascalia": "Risultato finale continuo", "ordine": "0"},
        files={"file": ("dopo.webp", fake_webp, "image/webp")},
    )
    assert r_dopo.status_code == 201, r_dopo.text

    r_video = client.post(
        f"/api/lavori/{lavoro_id}/media",
        data={
            "tipo": "video",
            "titolo": "Panoramica finale terrazzo",
            "didascalia": "Ripresa completa a lavoro ultimato",
            "durata": "0:14",
            "ordine": "0",
        },
        files={
            "file": ("tour.mp4", fake_mp4, "video/mp4"),
            "poster": ("poster.jpg", fake_jpg, "image/jpeg"),
        },
    )
    assert r_video.status_code == 201, r_video.text
    video_id = r_video.json()["id"]
    assert r_video.json()["poster_url"] == f"/api/lavori/{lavoro_id}/media/{video_id}/poster"

    # 3. GET /api/lavori restituisce tutti i campi + media raggruppati
    res_list = client.get("/api/lavori")
    assert res_list.status_code == 200
    dati = res_list.json()["dati"]
    assert len(dati) == 1
    item = dati[0]
    assert item["superficie_mq"] == 250
    assert item["supporto"] == "Piastrelle in gres esistenti"
    assert item["ciclo_sistema"] == "Poliurea a freddo bicomponente"
    assert len(item["stratigrafia_fasi"]) == 2
    assert len(item["foto_prima"]) == 1
    assert len(item["foto_dopo"]) == 1
    assert len(item["video_dopo"]) == 1
    assert item["video_dopo"][0]["durata"] == "0:14"

    # 4. Streaming video con HTTP 206 Partial Content + poster 200
    res_range = client.get(
        f"/api/lavori/{lavoro_id}/media/{video_id}",
        headers={"Range": "bytes=0-15"},
    )
    assert res_range.status_code == 206
    assert res_range.headers["content-range"] == f"bytes 0-15/{len(fake_mp4)}"
    assert len(res_range.content) == 16
    assert res_range.content == fake_mp4[:16]

    res_poster = client.get(f"/api/lavori/{lavoro_id}/media/{video_id}/poster")
    assert res_poster.status_code == 200
    assert res_poster.content == fake_jpg

    # 5. PATCH aggiorna superficie e stratigrafia
    res_patch = client.patch(
        f"/api/lavori/{lavoro_id}",
        json={
            "superficie_mq": 280,
            "ciclo_sistema": "Poliurea a freddo + topcoat UV",
            "stratigrafia_fasi": [
                {"fase": "01", "titolo": "Primer", "dettaglio": "Epossidico"},
                {"fase": "02", "titolo": "Poliurea", "dettaglio": "2 mm"},
                {"fase": "03", "titolo": "Topcoat", "dettaglio": "Alifatico UV"},
            ],
        },
    )
    assert res_patch.status_code == 200
    updated = client.get("/api/lavori").json()["dati"][0]
    assert updated["superficie_mq"] == 280
    assert len(updated["stratigrafia_fasi"]) == 3

    # 6. Eliminazione singolo media + eliminazione lavoro pulisce tutto da R2
    assert len(env.UPLOADS.store) == 4  # prima + dopo + video + poster
    r_del_media = client.delete(f"/api/lavori/{lavoro_id}/media/{prima_id}")
    assert r_del_media.status_code == 204
    assert len(env.UPLOADS.store) == 3

    r_del_job = client.delete(f"/api/lavori/{lavoro_id}")
    assert r_del_job.status_code == 204
    assert len(env.UPLOADS.store) == 0
    assert client.get("/api/lavori").json()["dati"] == []
