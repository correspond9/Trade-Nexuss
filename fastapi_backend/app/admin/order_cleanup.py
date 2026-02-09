from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.users.auth import get_current_user, get_db
from app.users.permissions import require_role
from app.storage.models import UserAccount, MockOrder, MockTrade, ExecutionEvent, MockPosition, LedgerEntry, PnlSnapshot
from typing import Dict, Any

router = APIRouter(prefix="/admin", tags=["admin"])

@router.delete("/clear-executed-orders")
def clear_admin_executed_orders(
    include_positions: bool = False,
    include_ledger: bool = False,
    include_pnl: bool = False,
    user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Remove all executed order entries from Admin account
    
    Query Parameters:
    - include_positions: Also remove mock positions (default: False)
    - include_ledger: Also remove ledger entries (default: False) 
    - include_pnl: Also remove PnL snapshots (default: False)
    """
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    
    try:
        # Find Admin user
        admin_user = db.query(UserAccount).filter(
            UserAccount.role.in_(["ADMIN", "SUPER_ADMIN"])
        ).first()
        
        if not admin_user:
            raise HTTPException(status_code=404, detail="No Admin user found")
        
        # Count records before deletion
        executed_orders = db.query(MockOrder).filter(
            MockOrder.user_id == admin_user.id,
            MockOrder.status == "EXECUTED"
        ).count()
        
        execution_events = db.query(ExecutionEvent).filter(
            ExecutionEvent.user_id == admin_user.id
        ).count()
        
        mock_trades = db.query(MockTrade).filter(
            MockTrade.user_id == admin_user.id
        ).count()
        
        positions = db.query(MockPosition).filter(
            MockPosition.user_id == admin_user.id
        ).count() if include_positions else 0
        
        ledger_entries = db.query(LedgerEntry).filter(
            LedgerEntry.user_id == admin_user.id
        ).count() if include_ledger else 0
        
        pnl_snapshots = db.query(PnlSnapshot).filter(
            PnlSnapshot.user_id == admin_user.id
        ).count() if include_pnl else 0
        
        # Remove records in order of foreign key dependencies
        
        # 1. Remove execution events
        db.query(ExecutionEvent).filter(ExecutionEvent.user_id == admin_user.id).delete()
        
        # 2. Remove mock trades
        db.query(MockTrade).filter(MockTrade.user_id == admin_user.id).delete()
        
        # 3. Remove executed orders
        db.query(MockOrder).filter(
            MockOrder.user_id == admin_user.id,
            MockOrder.status == "EXECUTED"
        ).delete()
        
        # 4. Optional additional cleanup
        if include_positions:
            db.query(MockPosition).filter(MockPosition.user_id == admin_user.id).delete()
        
        if include_ledger:
            db.query(LedgerEntry).filter(LedgerEntry.user_id == admin_user.id).delete()
        
        if include_pnl:
            db.query(PnlSnapshot).filter(PnlSnapshot.user_id == admin_user.id).delete()
        
        db.commit()
        
        return {
            "status": "success",
            "admin_user": admin_user.username,
            "removed_records": {
                "executed_orders": executed_orders,
                "execution_events": execution_events,
                "mock_trades": mock_trades,
                "positions": positions,
                "ledger_entries": ledger_entries,
                "pnl_snapshots": pnl_snapshots
            },
            "total_removed": executed_orders + execution_events + mock_trades + positions + ledger_entries + pnl_snapshots
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing executed orders: {str(e)}")

@router.get("/executed-orders-count")
def get_admin_executed_orders_count(
    user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get count of executed orders and related records for Admin account"""
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    
    try:
        # Find Admin user
        admin_user = db.query(UserAccount).filter(
            UserAccount.role.in_(["ADMIN", "SUPER_ADMIN"])
        ).first()
        
        if not admin_user:
            raise HTTPException(status_code=404, detail="No Admin user found")
        
        # Count all related records
        executed_orders = db.query(MockOrder).filter(
            MockOrder.user_id == admin_user.id,
            MockOrder.status == "EXECUTED"
        ).count()
        
        execution_events = db.query(ExecutionEvent).filter(
            ExecutionEvent.user_id == admin_user.id
        ).count()
        
        mock_trades = db.query(MockTrade).filter(
            MockTrade.user_id == admin_user.id
        ).count()
        
        positions = db.query(MockPosition).filter(
            MockPosition.user_id == admin_user.id
        ).count()
        
        ledger_entries = db.query(LedgerEntry).filter(
            LedgerEntry.user_id == admin_user.id
        ).count()
        
        pnl_snapshots = db.query(PnlSnapshot).filter(
            PnlSnapshot.user_id == admin_user.id
        ).count()
        
        return {
            "admin_user": admin_user.username,
            "record_counts": {
                "executed_orders": executed_orders,
                "execution_events": execution_events,
                "mock_trades": mock_trades,
                "positions": positions,
                "ledger_entries": ledger_entries,
                "pnl_snapshots": pnl_snapshots
            },
            "total_records": executed_orders + execution_events + mock_trades + positions + ledger_entries + pnl_snapshots
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting counts: {str(e)}")
