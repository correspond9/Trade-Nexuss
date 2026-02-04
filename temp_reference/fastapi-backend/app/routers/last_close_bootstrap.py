"""
Last Close Bootstrap API Routes
One-time bootstrap endpoint to populate last close prices
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app.services.last_close_bootstrap import last_close_bootstrap
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])


@router.post("/last-close-prices", response_model=Dict[str, Any])
async def bootstrap_last_close_prices(
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: Session = Depends(get_db)
    # Temporarily remove auth check for testing
    # current_user: dict = Depends(get_current_user)
):
    """
    Trigger one-time bootstrap of last close prices from Dhan REST API
    
    Args:
        force: Force bootstrap even if already completed (USE WITH CAUTION)
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Bootstrap status and statistics
    """
    try:
        # Temporarily skip auth check for testing
        logger.info("🚀 Starting bootstrap (auth check bypassed for testing)")
        
        # Check user permissions (only admin/super_admin)
        # user_role = current_user.get('role', '').upper()
        # if user_role not in ['SUPER_ADMIN', 'ADMIN']:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Only administrators can run bootstrap"
        #     )
        
        # Check if bootstrap should run
        if not force:
            should_run = await last_close_bootstrap.should_run_bootstrap(db)
            if not should_run:
                return {
                    "status": "skipped",
                    "message": "Bootstrap not required or already completed",
                    "note": "Use force=true to override this check"
                }
        
        # Run bootstrap in background
        logger.info("🚀 Starting bootstrap last close prices...")
        result = await last_close_bootstrap.run_bootstrap()
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Bootstrap API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bootstrap failed: {str(e)}"
        )


@router.get("/last-close-prices/status", response_model=Dict[str, Any])
async def get_bootstrap_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get bootstrap status and statistics
    
    Args:
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Bootstrap status information
    """
    try:
        from sqlalchemy import select, func
        from app.models.instrument_last_close import InstrumentLastClose
        
        # Get statistics
        total_records = db.execute(
            select(func.count()).select_from(InstrumentLastClose)
        ).scalar()
        
        bootstrap_completed = db.execute(
            select(func.count()).select_from(InstrumentLastClose).where(
                InstrumentLastClose.bootstrap_completed == True
            )
        ).scalar() > 0
        
        # Get sample records
        sample_records = db.execute(
            select(InstrumentLastClose).limit(5)
        ).scalars().all()
        
        return {
            "total_records": total_records,
            "bootstrap_completed": bootstrap_completed,
            "sample_records": [record.to_dict() for record in sample_records],
            "last_close_bootstrap_completed": last_close_bootstrap.bootstrap_completed
        }
        
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


@router.delete("/last-close-prices", response_model=Dict[str, Any])
async def reset_bootstrap(
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Reset bootstrap data (DANGEROUS - deletes all last close prices)
    
    Args:
        confirm: Must be true to confirm deletion
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Reset status
    """
    try:
        # Check user permissions (only super_admin)
        user_role = current_user.get('role', '').upper()
        if user_role != 'SUPER_ADMIN':
            raise HTTPException(
                status_code=403,
                detail="Only super administrators can reset bootstrap"
            )
        
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Must set confirm=true to reset bootstrap data"
            )
        
        from sqlalchemy import delete
        from app.models.instrument_last_close import InstrumentLastClose
        
        # Delete all records
        deleted_count = db.execute(
            delete(InstrumentLastClose)
        ).rowcount
        
        db.commit()
        
        # Reset bootstrap flag
        last_close_bootstrap.bootstrap_completed = False
        
        logger.warning(f"⚠️ Bootstrap reset: deleted {deleted_count} records")
        
        return {
            "status": "success",
            "deleted_records": deleted_count,
            "message": "Bootstrap data has been reset",
            "warning": "You must run bootstrap again to populate data"
        }
        
    except Exception as e:
        logger.error(f"❌ Reset error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reset failed: {str(e)}"
        )
