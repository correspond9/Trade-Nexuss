
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.users.auth import get_current_user, get_db
from app.users.permissions import require_role
from app.storage.models import UserAccount, Notification
from app.notifications.notifier import notify

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/suspend/{username}")
def suspend_user(username: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(UserAccount).filter(UserAccount.username == username).first()
    target.status = "BLOCKED"
    db.commit()
    notify(db, f"User {username} suspended by {user.username}")
    return {"status": "suspended"}


@router.get("/notifications")
def list_notifications(limit: int = 50, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    rows = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(rows),
        "notifications": [
            {
                "id": row.id,
                "message": row.message,
                "level": row.level,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }
