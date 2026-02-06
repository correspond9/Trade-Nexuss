
from sqlalchemy.orm import Session
from app.storage.models import Notification

def notify(db: Session, message: str, level: str = "WARN"):
    n = Notification(message=message, level=level)
    db.add(n)
    db.commit()
