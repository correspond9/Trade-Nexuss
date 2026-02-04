"""
Expiry Router
Handles expiry-related endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_active_user

router = APIRouter()

@router.get("/{symbol}")
async def get_expiry_dates(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get expiry dates for symbol"""
    return {"message": "Expiry dates endpoint not yet implemented"}
