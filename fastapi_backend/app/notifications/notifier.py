
from sqlalchemy.orm import Session
from app.storage.models import Notification

def notify(db: Session, message: str):
    n = Notification(message=message)
    db.add(n)
    db.commit()
