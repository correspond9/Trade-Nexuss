"""
Instruments Router
Handles instrument-related endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_active_user

router = APIRouter()

@router.get("/")
async def get_instruments(
    exchange: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get instruments"""
    return {"message": "Instruments endpoint not yet implemented"}

@router.get("/{instrument_id}")
async def get_instrument_details(
    instrument_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get instrument details"""
    return {"message": "Instrument details endpoint not yet implemented"}
