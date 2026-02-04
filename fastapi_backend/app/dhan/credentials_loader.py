import re
from pathlib import Path

from app.storage.db import SessionLocal
from app.storage.models import DhanCredential

DEFAULT_CRED_PATH = Path(__file__).resolve().parents[2] / "API_cred.txt"


def _parse_credentials(text: str) -> dict:
    def find(pattern: str) -> str | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    return {
        "client_id": find(r"client\s*id\s*[-: ]\s*(\d+)")
        or find(r"client\s*id\s*[-: ]\s*([\w-]+)"),
        "api_key": find(r"api\s*key\s*[-: ]\s*([\w-]+)"),
        "api_secret": find(r"secret\s*api\s*[-: ]\s*([\w-]+)"),
        "auth_token": find(r"daily\s*token\s*[-: ]\s*([\w\-.]+)"),
    }


def ensure_db_credentials_from_file(path: Path | None = None) -> bool:
    cred_path = path or DEFAULT_CRED_PATH
    if not cred_path.exists():
        return False

    text = cred_path.read_text(encoding="utf-8", errors="ignore")
    parsed = _parse_credentials(text)
    if not parsed.get("client_id") or not parsed.get("auth_token"):
        return False

    db = SessionLocal()
    try:
        existing = db.query(DhanCredential).first()
        if existing and existing.client_id and existing.auth_token:
            return False

        db.query(DhanCredential).delete()
        row = DhanCredential(
            client_id=parsed.get("client_id") or "",
            api_key=parsed.get("api_key") or "",
            api_secret=parsed.get("api_secret") or "",
            auth_token=parsed.get("auth_token") or "",
        )
        db.add(row)
        db.commit()
        return True
    finally:
        db.close()