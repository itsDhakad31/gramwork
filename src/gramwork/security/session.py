"""Encrypted Telethon session storage."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from telethon.sessions import StringSession

from gramwork.exceptions import SecurityError

MAGIC = b"GRAMSESS1\x00"
SALT_LEN = 32
NONCE_LEN = 12
KDF_ITERATIONS = 600_000


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def save_encrypted_session(
    session: StringSession, path: str | Path, password: str
) -> None:
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    plaintext = session.save().encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    Path(path).write_bytes(MAGIC + salt + nonce + ciphertext)


def load_encrypted_session(path: str | Path, password: str) -> StringSession:
    p = Path(path)
    if not p.exists():
        raise SecurityError(f"Encrypted session not found at {p}")

    raw = p.read_bytes()
    if not raw.startswith(MAGIC):
        raise SecurityError("Invalid session file (bad magic)")

    offset = len(MAGIC)
    salt = raw[offset : offset + SALT_LEN]
    offset += SALT_LEN
    nonce = raw[offset : offset + NONCE_LEN]
    offset += NONCE_LEN
    ciphertext = raw[offset:]

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise SecurityError(
            "Failed to decrypt session, wrong password?"
        ) from exc

    return StringSession(plaintext.decode("utf-8"))
