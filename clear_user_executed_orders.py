#!/usr/bin/env python3
"""
Script to remove all executed order entries from user with mobile number 9967595222
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

from sqlalchemy.orm import Session
from app.storage.db import engine, SessionLocal
from app.storage.models import UserAccount, MockOrder, MockTrade, ExecutionEvent, MockPosition, LedgerEntry, PnlSnapshot

def clear_user_executed_orders_by_mobile():
    """Remove all executed order entries from user with mobile number 9967595222"""
    
    db = SessionLocal()
    try:
        # Find user by mobile number
        target_user = db.query(UserAccount).filter(
            UserAccount.mobile == "9967595222"
        ).first()
        
        if not target_user:
            print(f"❌ No user found with mobile number 9967595222")
            return False
        
        print(f"🔍 Found user: {target_user.username} (ID: {target_user.id}, Mobile: {target_user.mobile})")
        
        # Count executed orders before deletion
        executed_orders = db.query(MockOrder).filter(
            MockOrder.user_id == target_user.id,
            MockOrder.status == "EXECUTED"
        ).all()
        
        print(f"📊 Found {len(executed_orders)} executed orders")
        
        if not executed_orders:
            print("✅ No executed orders found for this user")
            return True
        
        # Remove related records first (foreign key dependencies)
        
        # 1. Remove execution events
        execution_events = db.query(ExecutionEvent).filter(
            ExecutionEvent.user_id == target_user.id
        ).all()
        print(f"🗑️  Removing {len(execution_events)} execution events")
        db.query(ExecutionEvent).filter(ExecutionEvent.user_id == target_user.id).delete()
        
        # 2. Remove mock trades
        mock_trades = db.query(MockTrade).filter(
            MockTrade.user_id == target_user.id
        ).all()
        print(f"🗑️  Removing {len(mock_trades)} mock trades")
        db.query(MockTrade).filter(MockTrade.user_id == target_user.id).delete()
        
        # 3. Remove executed orders
        print(f"🗑️  Removing {len(executed_orders)} executed orders")
        db.query(MockOrder).filter(
            MockOrder.user_id == target_user.id,
            MockOrder.status == "EXECUTED"
        ).delete()
        
        # 4. Optionally clean up positions, ledger entries, and PnL snapshots
        # Uncomment if you want to remove these as well
        
        # positions = db.query(MockPosition).filter(MockPosition.user_id == target_user.id).all()
        # print(f"🗑️  Removing {len(positions)} positions")
        # db.query(MockPosition).filter(MockPosition.user_id == target_user.id).delete()
        
        # ledger_entries = db.query(LedgerEntry).filter(LedgerEntry.user_id == target_user.id).all()
        # print(f"🗑️  Removing {len(ledger_entries)} ledger entries")
        # db.query(LedgerEntry).filter(LedgerEntry.user_id == target_user.id).delete()
        
        # pnl_snapshots = db.query(PnlSnapshot).filter(PnlSnapshot.user_id == target_user.id).all()
        # print(f"🗑️  Removing {len(pnl_snapshots)} PnL snapshots")
        # db.query(PnlSnapshot).filter(PnlSnapshot.user_id == target_user.id).delete()
        
        # Commit changes
        db.commit()
        print(f"✅ Successfully removed all executed order entries from user {target_user.username}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting cleanup of executed orders for mobile 9967595222...")
    success = clear_user_executed_orders_by_mobile()
    if success:
        print("🎉 Cleanup completed successfully!")
    else:
        print("💥 Cleanup failed!")
        sys.exit(1)
