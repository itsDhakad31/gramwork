"""AES-256-GCM encrypted secret store."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from gramwork.exceptions import SecurityError

MAGIC = b"GRAMVAULT1"
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


class Vault:
    """Encrypted JSON key-value store.

    Binary format on disk: GRAMVAULT1 (10B) + salt (32B) + nonce (12B) + ciphertext.
    """

    def __init__(self, path: str | Path = ".gramwork_vault") -> None:
        self._path = Path(path)
        self._data: dict[str, str] | None = None
        self._key: bytes | None = None

    @property
    def is_unlocked(self) -> bool:
        return self._data is not None

    def init(self, password: str) -> None:
        if self._path.exists():
            raise SecurityError(f"Vault already exists at {self._path}")
        self._data = {}
        self._key = None
        self._save(password)

    def unlock(self, password: str) -> None:
        if not self._path.exists():
            raise SecurityError(f"Vault not found at {self._path}")

        raw = self._path.read_bytes()
        if not raw.startswith(MAGIC):
            raise SecurityError("Invalid vault file (bad magic)")

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
                "Failed to decrypt vault, wrong password?"
            ) from exc

        self._data = json.loads(plaintext.decode("utf-8"))
        self._key = key

    def lock(self) -> None:
        self._data = None
        self._key = None

    def get(self, key: str) -> str:
        self._check_unlocked()
        assert self._data is not None
        if key not in self._data:
            raise SecurityError(f"Key '{key}' not found in vault")
        return self._data[key]

    def set(self, key: str, value: str, password: str) -> None:
        self._check_unlocked()
        assert self._data is not None
        self._data[key] = value
        self._save(password)

    def list_keys(self) -> list[str]:
        self._check_unlocked()
        assert self._data is not None
        return list(self._data.keys())

    def _check_unlocked(self) -> None:
        if self._data is None:
            raise SecurityError("Vault is locked, call unlock() first")

    def _save(self, password: str) -> None:
        assert self._data is not None
        salt = os.urandom(SALT_LEN)
        nonce = os.urandom(NONCE_LEN)
        key = _derive_key(password, salt)
        aesgcm = AESGCM(key)
        plaintext = json.dumps(self._data).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        self._path.write_bytes(MAGIC + salt + nonce + ciphertext)
        self._key = key
