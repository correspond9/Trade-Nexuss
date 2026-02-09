
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.users.auth import get_current_user, get_db
from app.users.permissions import require_role
from app.storage.models import UserAccount, Notification, MockOrder, MockTrade, ExecutionEvent, MockPosition, LedgerEntry, PnlSnapshot
from app.notifications.notifier import notify
import os
import zipfile

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

@router.post("/nse-refresh")
async def nse_refresh(user=Depends(get_current_user)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    try:
        from app.services.nse_reports_service import nse_reports_service
        from app.services.span_parameters_service import span_parameters_service
        await nse_reports_service.refresh_daily_reports()
        span_parameters_service.refresh_from_extracted()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload/equity-exposure")
async def upload_equity_exposure(file: UploadFile = File(...), user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    try:
        from app.services.nse_reports_service import nse_reports_service
        import csv, io
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cache_dir = os.path.join(base_dir, "cache", "nse")
        os.makedirs(cache_dir, exist_ok=True)
        dest = os.path.join(cache_dir, f"exposure_manual.csv")
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)
        # Parse uploaded CSV directly (no network call). Prefer "Total applicable ELM%" column.
        text = content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        exposures = {}
        if reader.fieldnames:
            # Normalize headers
            headers = [h.strip().upper() for h in reader.fieldnames]
            sym_key = None
            elm_key = None
            inst_key = None
            for h in headers:
                if h in {"SYMBOL", "UNDERLYING"}:
                    sym_key = h
                if h in {"TOTAL APPLICABLE ELM%", "TOTAL ELM%", "ELM%", "EXPOSURE%", "TOTAL APPLICABLE ELM%"}:
                    elm_key = h
                if h in {"INSTRUMENT TYPE", "INSTRUMENT", "TYPE"}:
                    inst_key = h
            for row in reader:
                if not row:
                    continue
                # Access by normalized keys
                row_norm = {k.strip().upper(): (v or "").strip() for k, v in row.items()}
                sym = (row_norm.get(sym_key or "SYMBOL") or "").upper()
                raw_val = (row_norm.get(elm_key or "TOTAL APPLICABLE ELM%") or "").replace("%", "")
                inst = (row_norm.get(inst_key or "INSTRUMENT TYPE") or "").upper()
                if inst and inst != "OTH":
                    # Only keep OTH rows for futures exposure margin
                    continue
                if not sym or not raw_val:
                    continue
                try:
                    val = float(raw_val)
                    if val > 1:
                        val = val / 100.0
                except ValueError:
                    continue
                if 0 <= val <= 1:
                    exposures[sym] = val
        else:
            # Fallback: simple CSV without headers, assume first col symbol, last col percent
            for line in text.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2:
                    continue
                sym = parts[0].upper()
                val_raw = parts[-1].replace("%", "")
                try:
                    val = float(val_raw)
                    if val > 1:
                        val = val / 100.0
                except ValueError:
                    continue
                if sym and 0 <= val <= 1:
                    exposures[sym] = val
        if exposures:
            nse_reports_service.state.exposures_fno = exposures
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload/equity-span")
async def upload_equity_span(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    try:
        from app.services.span_parameters_service import span_parameters_service
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cache_dir = os.path.join(base_dir, "cache", "nse")
        os.makedirs(cache_dir, exist_ok=True)
        zip_path = os.path.join(cache_dir, "equity_span_manual.zip")
        extract_dir = os.path.join(cache_dir, "equity_span_manual")
        content = await file.read()
        with open(zip_path, "wb") as f:
            f.write(content)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        span_parameters_service.refresh_from_extracted()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload/commodity-span")
async def upload_commodity_span(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    try:
        from app.services.span_parameters_service import span_parameters_service
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cache_dir = os.path.join(base_dir, "cache", "nse")
        os.makedirs(cache_dir, exist_ok=True)
        zip_path = os.path.join(cache_dir, "commodity_span_manual.zip")
        extract_dir = os.path.join(cache_dir, "commodity_span_manual")
        content = await file.read()
        with open(zip_path, "wb") as f:
            f.write(content)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        span_parameters_service.refresh_from_extracted()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
