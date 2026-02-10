import sqlite3
import sys

DB = 'fastapi_backend/database/broker.db'
EMAIL = 'admin@example.com'

try:
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
