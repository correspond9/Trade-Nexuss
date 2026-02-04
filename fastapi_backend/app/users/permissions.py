
from fastapi import HTTPException

def require_role(user, roles):
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
