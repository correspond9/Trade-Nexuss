
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from pathlib import Path

# Database path - ABSOLUTE PATH to database/ folder for consistency
FASTAPI_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # fastapi_backend/
DB_DIR = FASTAPI_BACKEND_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "broker.db"

# Prefer DATABASE_URL from environment (production/docker). Fallback to SQLite file.
env_db = os.environ.get("DATABASE_URL")
if env_db:
	DATABASE_URL = env_db
else:
	DATABASE_URL = f"sqlite:///{str(DB_PATH).replace(chr(92), '/')}"

print(f"[DB] Using DATABASE_URL={DATABASE_URL}")
print(f"[DB] Local DB path: {DB_PATH} exists={DB_PATH.exists()}")

# For SQLite we need check_same_thread; for other DBs omit it
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
