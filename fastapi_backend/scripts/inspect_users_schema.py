import sqlite3, os
DB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'broker.db'))
print('DB', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        print('No users table')
    else:
        cur.execute("PRAGMA table_info(users)")
        cols = cur.fetchall()
        print('users columns:')
        for c in cols:
            print(c)
finally:
    conn.close()
