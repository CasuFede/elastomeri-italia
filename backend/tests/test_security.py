"""Test unitari per il modulo core.security e gestione token HMAC."""
import time
from core.config import get_session_secret, maschera_email
from core.security import (
    crea_hash_password,
    crea_token_sessione,
    pbkdf2_sha256_bytes,
    valida_complessita_password,
    valida_token_sessione,
    verifica_hash_password,
)


def test_password_hashing():
    pwd = "SicuraPassword123!"
    h = crea_hash_password(pwd)
    assert h.startswith("pbkdf2_sha256$")
    assert verifica_hash_password(pwd, h) is True
    assert verifica_hash_password("PasswordErrata!", h) is False


def test_pbkdf2_iterations_protection():
    pwd = "TestPassword"
    salt = b"1234567890123456"

    # Hash con 300.000 iterazioni (valido e supportato senza clamping alterato)
    h_300k = f"pbkdf2_sha256$300000${salt.hex()}${pbkdf2_sha256_bytes(pwd.encode(), salt, 300000).hex()}"
    assert verifica_hash_password(pwd, h_300k) is True

    # Hash anomalo > 600.000 iterazioni (rifiutato per prevenzione DoS)
    h_700k = f"pbkdf2_sha256$700000${salt.hex()}${pbkdf2_sha256_bytes(pwd.encode(), salt, 10000).hex()}"
    assert verifica_hash_password(pwd, h_700k) is False

    # Hash anomalo < 10.000 iterazioni (rifiutato per debolezza)
    h_low = f"pbkdf2_sha256$5000${salt.hex()}${pbkdf2_sha256_bytes(pwd.encode(), salt, 5000).hex()}"
    assert verifica_hash_password(pwd, h_low) is False


def test_session_token_lifecycle():
    secret = "chiave-segreta-test-12345"
    token = crea_token_sessione("cliente", "42", secret)

    # Validazione token corretto
    cliente_id = valida_token_sessione(token, secret, "cliente")
    assert cliente_id == "42"

    # Rifiuto se il tipo atteso non coincide
    assert valida_token_sessione(token, secret, "admin") is None

    # Rifiuto se il secret è errato
    assert valida_token_sessione(token, "segreto-sbagliato", "cliente") is None

    # Rifiuto se la firma è manomessa
    parti = token.split(":")
    parti[-1] = "f" * len(parti[-1])
    token_falsificato = ":".join(parti)
    assert valida_token_sessione(token_falsificato, secret, "cliente") is None


def test_session_secret_fallback():
    class DummyEnv:
        ADMIN_PASSWORD = "admin_master_pwd"

    env_solo_admin = DummyEnv()
    assert get_session_secret(env_solo_admin) == "admin_master_pwd"

    class DummyEnvDedicated:
        ADMIN_PASSWORD = "admin_master_pwd"
        SESSION_SECRET = "dedicated_jwt_secret"

    env_dedicated = DummyEnvDedicated()
    assert get_session_secret(env_dedicated) == "dedicated_jwt_secret"


def test_password_complexity_and_email_masking():
    assert valida_complessita_password("weak", 8) is not None
    assert valida_complessita_password("nouppercase123", 8) is not None
    assert valida_complessita_password("NOLOWERCASE123", 8) is not None
    assert valida_complessita_password("NoDigitsHere", 8) is not None
    assert valida_complessita_password("Sicura123", 8) is None
    assert valida_complessita_password("Sicura123456", 12) is None
    assert maschera_email("mario.rossi@example.it") == "m***@example.it"
    assert maschera_email("invalid") == "***"
