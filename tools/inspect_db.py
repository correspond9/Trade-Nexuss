from app.storage.db import SessionLocal
from app.storage.models import DhanCredential


def main():
    db = SessionLocal()
    try:
        rows = db.query(DhanCredential).all()
        if not rows:
            print('NO_ROWS')
            return
        for r in rows:
            print('ID:', r.id)
            print('client_id:', r.client_id)
            print('api_key:', r.api_key)
            print('api_secret:', r.api_secret)
            print('auth_token:', r.auth_token)
            print('daily_token:', r.daily_token)
            print('auth_mode:', r.auth_mode)
            print('is_default:', r.is_default)
            print('last_updated:', r.last_updated)
            print('---')
    finally:
        db.close()

if __name__ == '__main__':
    main()
