from __future__ import annotations

import hashlib
import secrets
from typing import Tuple


def hash_password(password: str) -> Tuple[str, str]:
    """Return (salt, hash) for a password."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, digest


def verify_password(password: str, salt: str, digest: str) -> bool:
    """Verify a password against a salt+hash pair."""
    if not salt or not digest:
        return False
    check = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(check, digest)
