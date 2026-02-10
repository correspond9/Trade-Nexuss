import sqlite3
import sys
import os

DB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'broker.db'))
EMAIL = 'admin@example.com'

try:
    print('DB_PATH', DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT id, email, role FROM users WHERE email=?', (EMAIL,))
    rows = cur.fetchall()
    if rows:
        print('FOUND', rows)
    else:
        print('NOT_FOUND')
    conn.close()
except Exception as e:
    print('ERROR', e)
    sys.exit(2)
