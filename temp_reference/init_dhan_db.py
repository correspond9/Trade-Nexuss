
import sqlite3
import os
from datetime import datetime

db_path = 'fastapi-backend/trading_terminal.db'
if not os.path.exists(db_path):
    db_path = 'trading_terminal.db'

print(f"Initializing Dhan tables in {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Insert default auth mode
cursor.execute("INSERT OR REPLACE INTO dhan_auth_mode (id, mode, is_active, last_switched_at) VALUES (1, 'DAILY_TOKEN', 1, ?)", (datetime.now().isoformat(),))

# 2. Insert a dummy token (user can update it in UI)
cursor.execute("INSERT OR REPLACE INTO dhan_daily_token_credentials (id, access_token, generated_at, expires_at, is_active) VALUES (1, 'dummy_token_configure_in_admin_panel', ?, ?, 1)", 
               (datetime.now().isoformat(), '2099-12-31T00:00:00'))

conn.commit()
conn.close()

print("✅ Dhan authentication initialized with DAILY_TOKEN mode.")
