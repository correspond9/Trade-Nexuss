
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from pathlib import Path

# Database path - ABSOLUTE PATH to database/ folder for consistency
# This ensures credentials are ALWAYS found regardless of where app starts from
FASTAPI_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # fastapi_backend/
DB_DIR = FASTAPI_BACKEND_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "broker.db"

# Use absolute path with proper forward slashes for SQLite
DATABASE_URL = f"sqlite:///{str(DB_PATH).replace(chr(92), '/')}"

print(f"[DB] Database path: {DB_PATH}")
print(f"[DB] Database exists: {DB_PATH.exists()}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
