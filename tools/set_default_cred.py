from app.storage.db import SessionLocal
from app.storage.models import DhanCredential

TARGET_ID = 3

def main():
    db = SessionLocal()
    try:
        # Clear existing defaults
        db.query(DhanCredential).update({DhanCredential.is_default: False})
        db.commit()
        # Set target as default
        row = db.query(DhanCredential).filter(DhanCredential.id == TARGET_ID).first()
        if not row:
            print('ROW_NOT_FOUND')
            return
        row.is_default = True
        db.add(row)
        db.commit()
        print('OK')
    finally:
        db.close()

if __name__ == '__main__':
    main()
