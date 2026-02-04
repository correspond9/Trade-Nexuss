
from sqlalchemy.orm import Session
from app.storage.models import DhanCredential

def save_credentials(db: Session, data: dict):
    db.query(DhanCredential).delete()
    cred = DhanCredential(**data)
    db.add(cred)
    db.commit()
