
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load root .env
load_dotenv()

database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

# Ensure sync url
if 'aiosqlite' in database_url:
    database_url = database_url.replace('aiosqlite', 'sqlite')

print(f"Initializing Dhan tables in {database_url}...")

try:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        # 1. Insert default auth mode
        conn.execute(text("""
            INSERT INTO dhan_auth_mode (mode, data_authority, is_active, last_switched_at) 
            VALUES ('DAILY_TOKEN', 'DHAN', 1, :now)
        """), {"now": datetime.now()})

        # 2. Insert a dummy token
        conn.execute(text("""
            INSERT INTO dhan_daily_token_credentials (access_token, generated_at, expires_at, is_active) 
            VALUES ('dummy_token_configure_in_admin_panel', :now, '2099-12-31 00:00:00', 1)
        """), {"now": datetime.now()})

        conn.commit()
    print("✅ Dhan authentication initialized successfully.")
except Exception as e:
    print(f"❌ Error: {e}")
