import argparse
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BACKEND_DIR / "preventivi.db"
UPLOADS_DIR = BACKEND_DIR / "uploads"

TABLE_COLUMNS = {
    "preventivi": (
        "id",
        "nome",
        "email",
        "telefono",
        "servizio",
        "messaggio",
        "stato",
        "note_cliente",
        "data_richiesta",
    ),
    "clienti": (
        "id",
        "nome",
        "email",
        "password_hash",
        "attivo",
        "data_creazione",
    ),
    "lavori": (
        "id",
        "titolo",
        "descrizione",
        "localita",
        "nome_file",
        "nome_originale",
        "tipo_mime",
        "data_creazione",
    ),
    "allegati": (
        "id",
        "preventivo_id",
        "nome_file",
        "nome_originale",
        "tipo_mime",
    ),
}


def valore_sql(valore: Any) -> str:
    if valore is None:
        return "NULL"
    if isinstance(valore, (int, float)):
        return str(valore)
    if isinstance(valore, bytes):
        return "X'" + valore.hex() + "'"
    return "'" + str(valore).replace("'", "''") + "'"


def righe_tabella(
    connection: sqlite3.Connection, table: str, columns: tuple[str, ...]
) -> list[dict[str, Any]]:
    disponibili = {
        riga["name"] for riga in connection.execute(f"PRAGMA table_info({table})")
    }
    selezione = []
    for column in columns:
        if column in disponibili:
            selezione.append(column)
        elif column == "stato":
            selezione.append("'ricevuto' AS stato")
        elif column == "note_cliente":
            selezione.append("'' AS note_cliente")
        elif column == "attivo":
            selezione.append("1 AS attivo")
        else:
            raise RuntimeError(f"La colonna {column} manca dalla tabella locale {table}.")
    query = f"SELECT {', '.join(selezione)} FROM {table} ORDER BY id"
    return [dict(riga) for riga in connection.execute(query).fetchall()]


def crea_sql(connection: sqlite3.Connection) -> tuple[str, list[tuple[Path, str]]]:
    statements = []
    uploads = []
    for table, columns in TABLE_COLUMNS.items():
        for riga in righe_tabella(connection, table, columns):
            valori = ", ".join(valore_sql(riga[column]) for column in columns)
            statements.append(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({valori});"
            )

            if table == "allegati":
                source = UPLOADS_DIR / riga["nome_file"]
                key = f"allegati/{riga['nome_file']}"
                uploads.append((source, key))
            elif table == "lavori":
                source = UPLOADS_DIR / "lavori" / riga["nome_file"]
                key = f"lavori/{riga['nome_file']}"
                uploads.append((source, key))

    return "\n".join(statements) + ("\n" if statements else ""), uploads


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trasferisce i record SQLite e gli upload locali in D1 e R2."
    )
    parser.add_argument("--database", required=True, help="Nome del database D1")
    parser.add_argument(
        "--bucket",
        default="preventivi-uploads",
        help="Nome del bucket R2 (default: preventivi-uploads)",
    )
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"Database SQLite da importare (default: {DEFAULT_DATABASE})",
    )
    args = parser.parse_args()

    if not args.sqlite.is_file():
        raise FileNotFoundError(f"Database SQLite non trovato: {args.sqlite}")

    with sqlite3.connect(args.sqlite) as connection:
        connection.row_factory = sqlite3.Row
        sql, uploads = crea_sql(connection)

    files_missing = [source for source, _ in uploads if not source.is_file()]
    if files_missing:
        raise FileNotFoundError(
            "Mancano file locali necessari alla migrazione: "
            + ", ".join(str(path) for path in files_missing)
        )

    for source, key in uploads:
        subprocess.run(
            [
                "uv",
                "run",
                "pywrangler",
                "r2",
                "object",
                "put",
                f"{args.bucket}/{key}",
                "--file",
                str(source),
                "--remote",
            ],
            cwd=BACKEND_DIR,
            check=True,
        )

    if sql:
        with tempfile.TemporaryDirectory(prefix="elastomeri-d1-") as directory:
            sql_file = Path(directory) / "local-data.sql"
            sql_file.write_text(sql, encoding="utf-8")
            subprocess.run(
                [
                    "uv",
                    "run",
                    "pywrangler",
                    "d1",
                    "execute",
                    args.database,
                    "--remote",
                    "--file",
                    str(sql_file),
                    "--yes",
                ],
                cwd=BACKEND_DIR,
                check=True,
            )

    print(
        f"Migrazione completata: {len(uploads)} file trasferiti e "
        f"{sum(sql.count(f'INSERT INTO {table} ') for table in TABLE_COLUMNS)} record esportati."
    )


if __name__ == "__main__":
    main()
