import datetime
import os
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2", "pbkdf2_sha256"], deprecated="auto")
SECRET_KEY = os.getenv("AGENTAUTH_JWT_SECRET", "super-secret-default-key-for-jwt")
ALGORITHM = "HS256"

# Load or generate Fernet key for symmetric encryption
KEY_FILE = Path(".agentauth_master.key")
if "AGENTAUTH_MASTER_KEY" in os.environ:
    _fernet_key = os.environ["AGENTAUTH_MASTER_KEY"].encode()
elif KEY_FILE.exists():
    _fernet_key = KEY_FILE.read_bytes()
else:
    _fernet_key = Fernet.generate_key()
    KEY_FILE.write_bytes(_fernet_key)

_fernet = Fernet(_fernet_key)


def encrypt_secret(val: str) -> str:
    """Encrypt a plaintext secret."""
    if not val:
        return val
    return str(_fernet.encrypt(val.encode()).decode())


def decrypt_secret(val: str) -> str:
    """Decrypt an encrypted secret."""
    if not val:
        return val
    try:
        return str(_fernet.decrypt(val.encode()).decode())
    except Exception:
        # Fallback if somehow not encrypted (or wrong key during tests)
        return val


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its hashed counterpart."""
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Return a secure hash of the given plain-text password."""
    return str(pwd_context.hash(password))


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """Create a signed JWT access token with an optional expiry delta."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
            minutes=1440
        )
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))  # type: ignore


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, returning the payload."""
    return dict(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]))  # type: ignore
