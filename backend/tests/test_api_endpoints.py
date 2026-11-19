"""Test di integrazione API tramite Starlette / FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import CloudflareServices, get_environment, get_services
from core.security import crea_token_sessione

client = TestClient(app)


class MockD1Statement:
    def __init__(self, query: str):
        self.query = query
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def all(self):
        class Res:
            pass
        res = Res()
        if "RETURNING id" in self.query:
            res.results = [{"id": 123}]
        elif "SELECT c.id" in self.query:
            res.results = [
                {
                    "id": 1,
                    "nome": "Cliente Test",
                    "email": "test@example.com",
                    "attivo": 1,
                    "data_creazione": "2026-01-01",
                    "totale_preventivi": 2,
                }
            ]
        elif "SELECT id, nome, email, password_hash" in self.query:
            res.results = [
                {
                    "id": 1,
                    "nome": "Cliente Test",
                    "email": "test@example.com",
                    "password_hash": "pbkdf2_sha256$100000$abcd$ef01",
                    "attivo": 1,
                    "data_creazione": "2026-01-01",
                    "primo_accesso": 0,
                }
            ]
        else:
            res.results = []
        return res

    async def run(self):
        return None


class MockD1:
    def prepare(self, query: str):
        return MockD1Statement(query)


class MockEnv:
    def __init__(self):
        self.DB = MockD1()
        self.UPLOADS = None
        self.ADMIN_USERNAME = "admin"
        self.ADMIN_PASSWORD = "testpassword123"
        self.SESSION_SECRET = "testsecret123"


@pytest.fixture(autouse=True)
def override_deps():
    env = MockEnv()
    app.state.env = env
    app.dependency_overrides[get_environment] = lambda: env
    app.dependency_overrides[get_services] = lambda: CloudflareServices(database=env.DB, uploads=env.UPLOADS)
    yield
    app.dependency_overrides.clear()
    app.state.env = None


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "poliurea-api"


def test_cors_and_security_headers():
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


def test_recupero_password_no_enumeration():
    # Test per prevenzione User Enumeration: email non esistente restituisce 200 con messaggio neutro
    response = client.post(
        "/api/auth/cliente/lost-password",
        json={"email": "non-esisto-sul-database@example.org"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Se l'indirizzo" in data["message"]


def test_preventivo_submission():
    # Test invio preventivo valido con form multipart
    form_data = {
        "nome": "Mario Rossi",
        "email": "mario.rossi@example.com",
        "telefono": "+39 333 1234567",
        "comune": "Genova",
        "tipo_immobile": "Condominio",
        "area_intervento": "Terrazzi / Balconi",
        "situazione": "Infiltrazione attiva (emergenza)",
        "metratura": "50–150 mq",
        "messaggio": "Infiltrazione dal terrazzo superiore.",
        "consenso": "true",
    }
    response = client.post("/api/preventivo", data=form_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id_pratica"] == 123


def test_clienti_list_authenticated():
    # Test rotta /clienti protetta con cookie admin
    token = crea_token_sessione("admin", "admin", "testsecret123")
    client.cookies.set("poliurea_admin_session", token)

    response = client.get("/api/clienti")
    assert response.status_code == 200
    data = response.json()
    assert "dati" in data
    assert len(data["dati"]) == 1
    assert data["dati"][0]["preventivi"] == 2
