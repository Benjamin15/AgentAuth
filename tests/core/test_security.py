import importlib
import os
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet

from agentauth.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    get_password_hash,
    verify_password,
)


def test_encryption_logic():
    # Test empty values
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None

    # Test valid flow
    plain = "secret123"
    enc = encrypt_secret(plain)
    assert enc != plain
    assert decrypt_secret(enc) == plain

    # Test invalid decryption fallback
    assert decrypt_secret("invalid-base64-or-wrong-format") == "invalid-base64-or-wrong-format"


def test_password_hashing():
    pw = "mypassword"
    hashed = get_password_hash(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token():
    data = {"sub": "admin"}
    # Default expiry
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "admin"

    # Custom expiry
    token2 = create_access_token(data, expires_delta=timedelta(minutes=5))
    decoded2 = decode_access_token(token2)
    assert decoded2["sub"] == "admin"


def test_key_generation_logic():
    from pathlib import Path

    key_file = Path(".agentauth_master.key")
    backup = None
    if key_file.exists():
        backup = key_file.read_bytes()
        key_file.unlink()

    import agentauth.core.security

    try:
        importlib.reload(agentauth.core.security)
        assert key_file.exists()
    finally:
        if backup:
            key_file.write_bytes(backup)


def test_master_key_env_override():
    custom_key = Fernet.generate_key().decode()
    import agentauth.core.security

    with patch.dict(os.environ, {"AGENTAUTH_MASTER_KEY": custom_key}):
        importlib.reload(agentauth.core.security)
        from agentauth.core.security import decrypt_secret, encrypt_secret

        plain = "hello"
        enc = encrypt_secret(plain)
        assert decrypt_secret(enc) == "hello"

    # Restore
    importlib.reload(agentauth.core.security)
