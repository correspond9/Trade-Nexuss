import sqlite3
import json
import os

# Resolve DB relative to scripts folder
DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'database', 'broker.db'))
conn = sqlite3.connect(DB)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
output = {'tables': tables, 'db_path': DB}

# Dump recent rows for mock tables commonly used by the backend
for t in ('mock_orders', 'mock_positions', 'mock_trades', 'users'):
    if t in tables:
        cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 100")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        output[t] = [dict(zip(cols, row)) for row in rows]

print(json.dumps(output, indent=2, default=str))
conn.close()