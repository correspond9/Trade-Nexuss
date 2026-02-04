"""
Option Chain Router
Handles option chain endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_active_user

router = APIRouter()

@router.get("/{symbol}")
async def get_option_chain(
    symbol: str,
    expiry: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get option chain for symbol"""
    return {"message": "Option chain endpoint not yet implemented"}
