from datetime import datetime, timedelta
import asyncio
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.storage.db import SessionLocal
from app.users.auth import get_current_user
from app.users.permissions import require_role
from app.storage import models
from app.users.passwords import hash_password
from app.market.live_prices import get_prices, update_price
from app.rms.kill_switch import blocked as kill_switch_blocked
from app.execution_simulator import get_execution_engine
from app.rms.span_margin_calculator import (
    fetch_user_positions as fetch_fno_positions,
    position_from_order as span_position_from_order,
)
from app.rms.mcx_margin_calculator import (
    fetch_mcx_positions,
    position_from_order as mcx_position_from_order,
)
from app.services.dhan_margin_service import dhan_margin_service
from app.market.watchlist_manager import get_watchlist_manager
from app.ems.market_config import market_config
from app.market.market_state import state as market_state
from app.oms.order_ids import generate as generate_order_id


# IST timezone offset (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)


router = APIRouter(tags=["mock-exchange"])
EXEC_ENGINE = get_execution_engine()


# ---------- DB Dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Optional current user resolver: returns active UserAccount or None when no X-USER header
def optional_current_user(x_user: str = Header(None), db: Session = Depends(get_db)):
    if not x_user:
        return None
    user = db.query(models.UserAccount).filter(models.UserAccount.username == x_user).first()
    if not user or user.status != "ACTIVE":
        return None
    return user


def _serialize(model_obj):
    data = {k: v for k, v in model_obj.__dict__.items() if not k.startswith("_")}
    return data


# ---------- Helpers ----------

def _get_or_create_default_plan(db: Session) -> models.BrokeragePlan:
    plan = db.query(models.BrokeragePlan).filter(models.BrokeragePlan.name == "DEFAULT").first()
    if plan:
        return plan
    plan = models.BrokeragePlan(name="DEFAULT", flat_fee=20.0, percent_fee=0.0, max_fee=20.0)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _get_or_create_admin(db: Session) -> models.UserAccount:
    admin = db.query(models.UserAccount).filter(models.UserAccount.username == "admin").first()
    if admin:
        return admin
    admin = db.query(models.UserAccount).filter(models.UserAccount.email == "admin@example.com").first()
    if admin:
        return admin
    admin = db.query(models.UserAccount).filter(models.UserAccount.role == "SUPER_ADMIN").first()
    if admin:
        return admin
    plan = _get_or_create_default_plan(db)
    admin = models.UserAccount(
        username="admin",
        email="admin@example.com",
        role="SUPER_ADMIN",
        status="ACTIVE",
        allowed_segments="NSE,NFO,BSE,MCX",
        wallet_balance=1_000_000.0,
        brokerage_plan_id=plan.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    margin = models.MarginAccount(user_id=admin.id, available_margin=admin.wallet_balance, used_margin=0.0)
    db.add(margin)
    db.commit()
    return admin


def _get_or_create_margin(db: Session, user_id: int) -> models.MarginAccount:
    margin = db.query(models.MarginAccount).filter(models.MarginAccount.user_id == user_id).first()
    if margin:
        return margin
    margin = models.MarginAccount(user_id=user_id, available_margin=0.0, used_margin=0.0)
    db.add(margin)
    db.commit()
    db.refresh(margin)
    return margin


def _get_ltp(symbol: str, fallback_price: float) -> float:
    prices = get_prices()
    key = (symbol or "").upper().strip()
    parts = key.split()
    if len(parts) >= 3 and parts[-1] in {"CE", "PE"}:
        try:
            strike_val = float(parts[-2])
            expiry_hint = None
            if len(parts) >= 4 and any(ch.isalpha() for ch in parts[-3]) and any(ch.isdigit() for ch in parts[-3]):
                expiry_hint = parts[-3]
                underlying = " ".join(parts[:-3]).strip()
            else:
                underlying = " ".join(parts[:-2]).strip()
            if underlying:
                from app.services.authoritative_option_chain_service import authoritative_option_chain_service
                chains = authoritative_option_chain_service.option_chain_cache.get(underlying, {})
                for expiry, skeleton in chains.items():
                    if expiry_hint and expiry != expiry_hint:
                        continue
                    leg = skeleton.strikes.get(strike_val)
                    if not leg:
                        continue
                    data = leg.CE if parts[-1] == "CE" else leg.PE
                    if data and data.ltp:
                        return float(data.ltp)
        except Exception:
            pass

    key_base = key.split()[0]
    ltp = prices.get(key_base)
    if ltp and isinstance(ltp, (int, float)):
        return float(ltp)
    return float(fallback_price or 0.0)


def _normalize_margin_symbol(symbol: str) -> str:
    text = (symbol or "").strip().upper()
    if text in {"NIFTY 50", "NIFTY50"}:
        return "NIFTY"
    if text in {"BANK NIFTY", "NIFTY BANK", "BANKNIFTY"}:
        return "BANKNIFTY"
    if text in {"BSE SENSEX", "S&P BSE SENSEX", "SENSEX 50"}:
        return "SENSEX"
    return text


def _extract_option_underlying(symbol: str) -> str:
    parts = (symbol or "").strip().split()
    if len(parts) >= 3 and parts[-1].upper() in {"CE", "PE"}:
        return _normalize_margin_symbol(" ".join(parts[:-2]))
    return _normalize_margin_symbol(symbol)


def _normalize_expiry_iso(expiry: Optional[str]) -> Optional[str]:
    if not expiry:
        return None
    text = str(expiry).strip().upper()
    for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%B%Y", "%d%b%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return str(expiry).strip() or None


def _is_mcx_segment(exchange_segment: Optional[str]) -> bool:
    return "MCX" in (exchange_segment or "").upper()


def _is_fno_segment(exchange_segment: Optional[str]) -> bool:
    text = (exchange_segment or "").upper()
    if "MCX" in text:
        return False
    return "FNO" in text or "NFO" in text


def _resolve_lot_size(underlying: Optional[str], expiry: Optional[str]) -> int:
    if not underlying:
        return 1
    try:
        from app.market.instrument_master.registry import REGISTRY

        if not REGISTRY.loaded:
            REGISTRY.load()

        target_expiry = REGISTRY._normalize_expiry(expiry) if expiry else None
        for row in REGISTRY.by_underlying.get(underlying.upper(), []):
            row_expiry = REGISTRY._normalize_expiry(row.get("SM_EXPIRY_DATE", ""))
            if target_expiry and row_expiry and row_expiry != target_expiry:
                continue
            lot = row.get("LOT_SIZE") or row.get("MARKET_LOT")
            try:
                lot_val = int(float(lot)) if lot is not None else None
            except (TypeError, ValueError):
                lot_val = None
            if lot_val and lot_val > 0:
                return lot_val
    except Exception:
        pass
    return 1


def _build_market_data_for_positions(positions: List[dict]) -> dict:
    market_data = {}
    for pos in positions:
        symbol = (pos.get("symbol") or "").strip()
        underlying = (pos.get("underlying") or "").strip()
        expiry = pos.get("expiry")
        lot_size = _resolve_lot_size(underlying or symbol, expiry)

        if symbol:
            if symbol not in market_data:
                market_data[symbol] = {}
            market_data[symbol].setdefault("ltp", _get_ltp(symbol, pos.get("price") or 0.0))
            market_data[symbol].setdefault("lot_size", lot_size)

        if underlying:
            if underlying not in market_data:
                market_data[underlying] = {}
            market_data[underlying].setdefault("ltp", _get_ltp(underlying, 0.0))
            market_data[underlying].setdefault("lot_size", lot_size)

    return market_data


def _local_margin_for_order(
    user_id: int,
    exchange_segment: Optional[str],
    symbol: str,
    transaction_type: str,
    quantity: int,
    price: float,
) -> Optional[dict]:
    """Fetch margin from Dhan API - NO LOCAL CALCULATION"""
    return None


def _local_margin_for_scripts(user_id: int, scripts: List["MarginScript"]) -> Optional[dict]:
    """Fetch margin from Dhan API - NO LOCAL CALCULATION"""
    return None


async def _dhan_margin_for_order(
    user_id: int,
    exchange_segment: Optional[str],
    symbol: str,
    transaction_type: str,
    quantity: int,
    price: float,
    product_type: str,
    security_id: Optional[str] = None,
) -> Optional[dict]:
    """Fetch margin from Dhan API with proper rate limiting"""
    try:
        # Use the provided security_id or let Dhan API resolve it
        margin_result = await dhan_margin_service.calculate_margin_single(
            exchange_segment=exchange_segment or "NSE_EQ",
            transaction_type=transaction_type or "BUY",
            quantity=quantity,
            product_type=product_type or "MIS",
            security_id=security_id or symbol,
            price=price
        )
        
        if margin_result and "margin" in margin_result:
            return {
                "margin": float(margin_result["margin"]),
                "source": "DHAN_API",
                "raw": margin_result
            }
        return None
    except Exception as e:
        print(f"[MARGIN] Dhan API error: {e}")
        return None


async def _dhan_margin_for_scripts(user_id: int, scripts: List["MarginScript"]) -> Optional[dict]:
    """Fetch multi-script margin from Dhan API with proper rate limiting"""
    try:
        # Convert scripts to Dhan API format
        dhan_scripts = []
        for script in scripts:
            dhan_script = {
                "exchangeSegment": script.exchange_segment or "NSE_EQ",
                "transactionType": script.transaction_type or "BUY",
                "quantity": int(script.quantity or 0),
                "productType": script.product_type or "MIS",
                "securityId": script.security_id or script.symbol,
                "price": float(script.price or 0.0),
            }
            if script.trigger_price is not None:
                dhan_script["triggerPrice"] = float(script.trigger_price)
            dhan_scripts.append(dhan_script)
        
        if not dhan_scripts:
            return {
                "margin": 0.0,
                "source": "DHAN_API_EMPTY",
                "raw": {}
            }
        
        margin_result = await dhan_margin_service.calculate_margin_multi(
            scripts=dhan_scripts,
            include_positions=True,
            include_orders=True
        )
        
        if margin_result and "margin" in margin_result:
            return {
                "margin": float(margin_result["margin"]),
                "source": "DHAN_API_MULTI",
                "raw": margin_result
            }
        return None
    except Exception as e:
        print(f"[MARGIN] Dhan API multi-script error: {e}")
        return None


def _brokerage_for(db: Session, user: models.UserAccount, turnover: float) -> float:
    plan = None
    if user.brokerage_plan_id:
        plan = db.query(models.BrokeragePlan).filter(models.BrokeragePlan.id == user.brokerage_plan_id).first()
    if not plan:
        plan = _get_or_create_default_plan(db)
    fee = plan.flat_fee + (turnover * (plan.percent_fee or 0.0))
    return min(fee, plan.max_fee or fee)


def _margin_required(price: float, qty: int, product_type: str) -> float:
    notional = abs(price * qty)
    return notional * 1.0


def _normalize_margin_multiplier(value: Optional[float]) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return 5.0
    return coerced if coerced > 0 else 5.0


def _apply_margin_multiplier(required: float, user: models.UserAccount, product_type: Optional[str] = None) -> float:
    if product_type and str(product_type).upper() != "MIS":
        return required
    multiplier = _normalize_margin_multiplier(getattr(user, "margin_multiplier", 5.0))
    return required / multiplier


def _segment_allowed(user: models.UserAccount, exchange_segment: str) -> bool:
    allowed = {s.strip().upper() for s in (user.allowed_segments or "").split(",") if s.strip()}
    if not allowed:
        return True
    seg = (exchange_segment or "").split("_")[0].upper()
    return seg in allowed or exchange_segment.upper() in allowed


def _update_ledger(db: Session, user: models.UserAccount, credit: float, debit: float, entry_type: str, remarks: str):
    balance = (user.wallet_balance or 0.0) + credit - debit
    user.wallet_balance = balance
    user.updated_at = ist_now()
    entry = models.LedgerEntry(
        user_id=user.id,
        entry_type=entry_type,
        credit=credit,
        debit=debit,
        balance=balance,
        remarks=remarks,
    )
    db.add(entry)


def _apply_position(db: Session, user_id: int, symbol: str, exchange_segment: str, product_type: str, qty: int, price: float):
    position = (
        db.query(models.MockPosition)
        .filter(
            models.MockPosition.user_id == user_id,
            models.MockPosition.symbol == symbol,
            models.MockPosition.product_type == product_type,
        )
        .first()
    )
    if not position:
        position = models.MockPosition(
            user_id=user_id,
            symbol=symbol,
            exchange_segment=exchange_segment,
            product_type=product_type,
            quantity=0,
            avg_price=0.0,
            realized_pnl=0.0,
            status="OPEN",
        )
        db.add(position)
        db.flush()

    new_qty = position.quantity + qty
    if position.quantity == 0 or (position.quantity > 0 and qty > 0) or (position.quantity < 0 and qty < 0):
        # same direction
        total_qty = position.quantity + qty
        if total_qty != 0:
            position.avg_price = ((position.avg_price * position.quantity) + (price * qty)) / total_qty
        position.quantity = total_qty
    else:
        # closing or flipping
        closing_qty = min(abs(position.quantity), abs(qty))
        pnl = (price - position.avg_price) * closing_qty
        if position.quantity < 0:
            pnl = -pnl
        position.realized_pnl += pnl
        position.quantity = new_qty
        if position.quantity == 0:
            position.status = "CLOSED"
        else:
            position.avg_price = price
    position.updated_at = ist_now()


def _execute_order(db: Session, order: models.MockOrder, execution_price: float):
    remaining = order.quantity - order.filled_qty
    if remaining <= 0:
        return
    order.filled_qty += remaining
    order.status = "EXECUTED"
    order.updated_at = ist_now()

    trade = models.MockTrade(
        order_id=order.id,
        user_id=order.user_id,
        price=execution_price,
        qty=remaining,
    )
    db.add(trade)

    user = db.query(models.UserAccount).filter(models.UserAccount.id == order.user_id).first()
    if not user:
        return

    turnover = execution_price * remaining
    brokerage = _brokerage_for(db, user, turnover)

    if order.transaction_type == "BUY":
        _update_ledger(db, user, credit=0.0, debit=turnover + brokerage, entry_type="TRADE_PNL", remarks="Order filled BUY")
    else:
        _update_ledger(db, user, credit=turnover - brokerage, debit=0.0, entry_type="TRADE_PNL", remarks="Order filled SELL")

    _apply_position(
        db,
        user_id=order.user_id,
        symbol=order.symbol,
        exchange_segment=order.exchange_segment,
        product_type=order.product_type,
        qty=remaining if order.transaction_type == "BUY" else -remaining,
        price=execution_price,
    )


def process_pending_orders():
    db = SessionLocal()
    try:
        EXEC_ENGINE.process_pending_orders(db)
        db.commit()
    finally:
        db.close()


# ---------- Request Models ----------

class OrderRequest(BaseModel):
    user_id: Optional[int] = 1
    symbol: str
    security_id: Optional[str] = None
    exchange_segment: str = "NSE_EQ"
    transaction_type: str = Field("BUY", pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    order_type: str = Field("MARKET", pattern="^(MARKET|LIMIT|SL-M|SL-L|GTT|TRIGGER)$")
    product_type: str = Field("MIS", pattern="^(MIS|NORMAL)$")
    price: Optional[float] = 0.0
    trigger_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    trailing_jump: Optional[float] = None
    is_super: Optional[bool] = False


class BasketLegRequest(BaseModel):
    symbol: str
    security_id: Optional[str] = None
    exchange_segment: str = "NSE_EQ"
    transaction_type: str = Field("BUY", pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    order_type: str = "MARKET"
    product_type: str = "MIS"
    price: Optional[float] = 0.0


class BasketRequest(BaseModel):
    user_id: Optional[int] = 1
    name: str
    legs: List[BasketLegRequest]


class BasketAppendRequest(BaseModel):
    legs: List[BasketLegRequest]


class UserRequest(BaseModel):
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    initial_password: Optional[str] = None
    role: str = "USER"
    status: str = "ACTIVE"
    allowed_segments: Optional[str] = "NSE,NFO,BSE,MCX"
    wallet_balance: float = 0.0
    margin_multiplier: Optional[float] = 5.0
    brokerage_plan_id: Optional[int] = None
def _place_order_core(req: OrderRequest, db: Session, user: models.UserAccount):
    def _reject_order(reason: str):
        order = models.MockOrder(
            order_ref=generate_order_id(),
            user_id=user.id,
            symbol=req.symbol,
            security_id=req.security_id,
            exchange_segment=req.exchange_segment,
            transaction_type=req.transaction_type,
            quantity=req.quantity,
            order_type=req.order_type,
            product_type=req.product_type,
            price=req.price or 0.0,
            trigger_price=req.trigger_price,
            is_super=bool(req.is_super),
            target_price=req.target_price,
            stop_loss_price=req.stop_loss_price,
            trailing_jump=req.trailing_jump,
            status="REJECTED",
            remarks=reason,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return {"data": _serialize(order)}

    if user.status != "ACTIVE" or kill_switch_blocked(user):
        return _reject_order("USER_BLOCKED")

    if not _segment_allowed(user, req.exchange_segment):
        return _reject_order("SEGMENT_RESTRICTED")

    snapshot = EXEC_ENGINE._snapshot_for_order(req.symbol, req.exchange_segment)
    decision_price = snapshot.get("best_ask") if req.transaction_type == "BUY" else snapshot.get("best_bid")
    exec_price = decision_price or (req.price or 0.0)
    required = _margin_required(exec_price, req.quantity, req.product_type)
    local_margin = _local_margin_for_order(
        user_id=user.id,
        exchange_segment=req.exchange_segment,
        symbol=req.symbol,
        transaction_type=req.transaction_type,
        quantity=req.quantity,
        price=exec_price,
    )
    if local_margin and local_margin.get("margin") is not None:
        required = float(local_margin["margin"])
    required = _apply_margin_multiplier(required, user, req.product_type)
    margin = _get_or_create_margin(db, user.id)
    margin_exceeded = margin.available_margin < required

    order = models.MockOrder(
        order_ref=generate_order_id(),
        user_id=user.id,
        symbol=req.symbol,
        security_id=req.security_id,
        exchange_segment=req.exchange_segment,
        transaction_type=req.transaction_type,
        quantity=req.quantity,
        order_type=req.order_type,
        product_type=req.product_type,
        price=req.price or 0.0,
        trigger_price=req.trigger_price,
        is_super=bool(req.is_super),
        target_price=req.target_price,
        stop_loss_price=req.stop_loss_price,
        trailing_jump=req.trailing_jump,
        status="PENDING",
    )
    db.add(order)
    db.flush()

    EXEC_ENGINE.process_new_order(db, order)

    db.commit()
    db.refresh(order)
    response = {"data": _serialize(order)}
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    initial_password: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    allowed_segments: Optional[str] = None
    wallet_balance: Optional[float] = None
    margin_multiplier: Optional[float] = None
    brokerage_plan_id: Optional[int] = None


class BackdatePositionRequest(BaseModel):
    # Identify target account
    mobile: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None

    # Position details
    symbol: str
    quantity: int
    avg_price: float = Field(..., alias="avg_price")
    exchange_segment: Optional[str] = "NSE_EQ"
    product_type: Optional[str] = "MIS"

    # When provided, set position created_at to this datetime (ISO format accepted)
    created_at: Optional[datetime] = None

    # If an existing position for (user,symbol,product_type) exists, merge by default
    merge: bool = True


class LedgerAdjustRequest(BaseModel):
    user_id: int
    credit: float = 0.0
    debit: float = 0.0
    remarks: Optional[str] = None


class MarginAdjustRequest(BaseModel):
    user_id: int
    available_margin: Optional[float] = None
    used_margin: Optional[float] = None


class RestrictRequest(BaseModel):
    allowed_segments: str


class BrokeragePlanRequest(BaseModel):
    brokerage_plan_id: int


class BasketExecuteRequest(BaseModel):
    basket_id: int


class PnlSnapshotRequest(BaseModel):
    user_id: Optional[int] = None


class SquareOffRequest(BaseModel):
    quantity: Optional[int] = None


class MarginRequest(BaseModel):
    user_id: Optional[int] = 1
    symbol: Optional[str] = None
    exchange_segment: Optional[str] = None
    transaction_type: Optional[str] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None
    quantity: int = 1
    price: float = 0.0
    product_type: str = "MIS"
    security_id: Optional[str] = None
    trigger_price: Optional[float] = None


class MarginScript(BaseModel):
    exchange_segment: str
    transaction_type: str
    quantity: int
    product_type: str
    security_id: str
    price: float = 0.0
    trigger_price: Optional[float] = None
    symbol: Optional[str] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None


class MultiMarginRequest(BaseModel):
    user_id: Optional[int] = 1
    scripts: List[MarginScript]
    include_positions: bool = True
    include_orders: bool = True


class PortfolioMarginRequest(BaseModel):
    user_id: Optional[int] = 1


# ---------- Public Endpoints ----------

@router.get("/trading/orders")
def list_orders(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    query = db.query(models.MockOrder)
    if user_id:
        query = query.filter(models.MockOrder.user_id == user_id)
    orders = query.order_by(models.MockOrder.created_at.desc()).all()
    return {"data": [_serialize(o) for o in orders]}


# ---------- Watchlist Endpoints (Tier A) ----------
@router.post("/watchlist/add")
def api_watchlist_add(payload: dict, db: Session = Depends(get_db)):
    mgr = get_watchlist_manager()
    user_id = int(payload.get("user_id", 1))
    symbol = payload.get("symbol")
    expiry = payload.get("expiry")
    instrument_type = payload.get("instrument_type", "STOCK_OPTION")
    underlying_ltp = payload.get("underlying_ltp")
    return mgr.add_to_watchlist(user_id=user_id, symbol=symbol, expiry=expiry, instrument_type=instrument_type, underlying_ltp=underlying_ltp)


@router.post("/watchlist/remove")
def api_watchlist_remove(payload: dict, db: Session = Depends(get_db)):
    mgr = get_watchlist_manager()
    user_id = int(payload.get("user_id", 1))
    symbol = payload.get("symbol")
    expiry = payload.get("expiry")
    return mgr.remove_from_watchlist(user_id=user_id, symbol=symbol, expiry=expiry)


@router.get("/watchlist/{user_id}")
def api_get_watchlist(user_id: int, db: Session = Depends(get_db)):
    mgr = get_watchlist_manager()
    return {"data": mgr.get_user_watchlist(user_id=user_id)}


@router.get("/orders")
def list_orders_legacy(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return list_orders(user_id=user_id, db=db)


@router.post("/trading/orders")
async def place_order(
    req: OrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.UserAccount] = Depends(optional_current_user),
):
    # Inspect raw JSON to detect forbidden credential-like fields
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    SENSITIVE_KEYS = {
        'api_key','apiKey','api_secret','apiSecret','secret_api','secret',
        'client_id','clientId','access_token','accessToken','auth_token','authToken',
        'daily_token','dailyToken'
    }

    # shallow check of top-level keys to avoid accidental leakage
    if any(k in SENSITIVE_KEYS for k in (payload.keys() if isinstance(payload, dict) else [])):
        raise HTTPException(status_code=400, detail="Credential-like fields are forbidden in order payload")

    # If a current user is present, enforce user_id matches
    if current_user is not None:
        if req.user_id and int(req.user_id) != int(current_user.id):
            raise HTTPException(status_code=403, detail="user_id does not match authenticated user")
        user = current_user
    else:
        user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)

    def _reject_order(reason: str):
        order = models.MockOrder(
            order_ref=generate_order_id(),
            user_id=user.id,
            symbol=req.symbol,
            security_id=req.security_id,
            exchange_segment=req.exchange_segment,
            transaction_type=req.transaction_type,
            quantity=req.quantity,
            order_type=req.order_type,
            product_type=req.product_type,
            price=req.price or 0.0,
            trigger_price=req.trigger_price,
            is_super=bool(req.is_super),
            target_price=req.target_price,
            stop_loss_price=req.stop_loss_price,
            trailing_jump=req.trailing_jump,
            status="REJECTED",
            remarks=reason,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return {"data": _serialize(order)}

    if user.status != "ACTIVE" or kill_switch_blocked(user):
        return _reject_order("USER_BLOCKED")

    if not _segment_allowed(user, req.exchange_segment):
        return _reject_order("SEGMENT_RESTRICTED")

    snapshot = EXEC_ENGINE._snapshot_for_order(req.symbol, req.exchange_segment)
    decision_price = snapshot.get("best_ask") if req.transaction_type == "BUY" else snapshot.get("best_bid")
    exec_price = decision_price or (req.price or 0.0)
    required = _margin_required(exec_price, req.quantity, req.product_type)
    local_margin = _local_margin_for_order(
        user_id=user.id,
        exchange_segment=req.exchange_segment,
        symbol=req.symbol,
        transaction_type=req.transaction_type,
        quantity=req.quantity,
        price=exec_price,
    )
    if local_margin and local_margin.get("margin") is not None:
        required = float(local_margin["margin"])
    required = _apply_margin_multiplier(required, user, req.product_type)
    margin = _get_or_create_margin(db, user.id)
    margin_exceeded = margin.available_margin < required

    order = models.MockOrder(
        order_ref=generate_order_id(),
        user_id=user.id,
        symbol=req.symbol,
        security_id=req.security_id,
        exchange_segment=req.exchange_segment,
        transaction_type=req.transaction_type,
        quantity=req.quantity,
        order_type=req.order_type,
        product_type=req.product_type,
        price=req.price or 0.0,
        trigger_price=req.trigger_price,
        is_super=bool(req.is_super),
        target_price=req.target_price,
        stop_loss_price=req.stop_loss_price,
        trailing_jump=req.trailing_jump,
        status="PENDING",
    )
    db.add(order)
    db.flush()

    EXEC_ENGINE.process_new_order(db, order)

    db.commit()
    db.refresh(order)
    response = {"data": _serialize(order)}
    if margin_exceeded:
        response["warning"] = "MARGIN_EXCEEDED"
    return response


@router.post("/orders")
def place_order_legacy(req: OrderRequest, db: Session = Depends(get_db)):
    return place_order(req=req, db=db)


@router.get("/portfolio/positions")
def list_positions(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    query = db.query(models.MockPosition)
    if user_id:
        query = query.filter(models.MockPosition.user_id == user_id)
    positions = query.all()
    results = []
    for pos in positions:
        ltp = _get_ltp(pos.symbol, pos.avg_price)
        mtm = (ltp - pos.avg_price) * pos.quantity
        results.append({
            "id": pos.id,
            "user_id": pos.user_id,
            "symbol": pos.symbol,
            "exchange_segment": pos.exchange_segment,
            "product_type": pos.product_type,
            "qty": pos.quantity,  # Frontend expects 'qty'
            "avgEntry": pos.avg_price,  # Frontend expects 'avgEntry'
            "mtm": mtm,
            "realizedPnl": pos.realized_pnl,  # Frontend expects 'realizedPnl'
            "status": pos.status,
        })
    return {"data": results}


@router.get("/positions")
def list_positions_legacy(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return list_positions(user_id=user_id, db=db)


@router.post("/closeposition")
def close_position_by_data(req: SquareOffRequest, db: Session = Depends(get_db)):
    """Close position by position data (for frontend compatibility)"""
    # Try to find position by ID first
    position = None
    
    # If request has position_id, use it
    if hasattr(req, 'position_id') and req.position_id:
        position = db.query(models.MockPosition).filter(
            models.MockPosition.id == req.position_id,
            models.MockPosition.user_id == 1,  # SUPER_ADMIN user
            models.MockPosition.status == "OPEN"
        ).first()
    else:
        # Otherwise, find the first open position for SUPER_ADMIN
        position = db.query(models.MockPosition).filter(
            models.MockPosition.user_id == 1,  # SUPER_ADMIN user
            models.MockPosition.status == "OPEN"
        ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return close_position(position_id=position.id, req=req, db=db)


@router.post("/positions/{position_id}/close")
def close_position(position_id: int, req: SquareOffRequest, db: Session = Depends(get_db)):
    pos = db.query(models.MockPosition).filter(models.MockPosition.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    if pos.status != "OPEN":
        return {"data": _serialize(pos)}

    qty = req.quantity or abs(pos.quantity)
    qty = min(abs(pos.quantity), qty)
    ltp = _get_ltp(pos.symbol, pos.avg_price)

    # ✨ ENHANCE: Add fallback for square-off when depth is unavailable
    snapshot = EXEC_ENGINE._snapshot_for_order(pos.symbol, pos.exchange_segment)
    if not snapshot.get("best_bid") or not snapshot.get("best_ask"):
        # Use LTP as fallback when depth data is not available
        print(f"[SQUAREOFF] Using LTP fallback for {pos.symbol}: {ltp}")
        snapshot["best_bid"] = ltp * 0.999  # Small spread
        snapshot["best_ask"] = ltp * 1.001

    order = models.MockOrder(
        order_ref=generate_order_id(),
        user_id=pos.user_id,
        symbol=pos.symbol,
        exchange_segment=pos.exchange_segment,
        transaction_type="SELL" if pos.quantity > 0 else "BUY",
        quantity=qty,
        order_type="MARKET",
        product_type=pos.product_type,
        price=ltp,
        status="PENDING",
    )
    db.add(order)
    db.flush()
    EXEC_ENGINE.process_new_order(db, order)
    db.commit()
    return {"data": _serialize(order)}


@router.post("/portfolio/positions/{position_id}/squareoff")
def squareoff_position(position_id: int, req: SquareOffRequest, db: Session = Depends(get_db)):
    return close_position(position_id=position_id, req=req, db=db)


@router.get("/trading/basket-orders")
def list_baskets(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    query = db.query(models.MockBasket)
    if user_id:
        query = query.filter(models.MockBasket.user_id == user_id)
    baskets = query.all()
    result = []
    for b in baskets:
        legs = db.query(models.MockBasketLeg).filter(models.MockBasketLeg.basket_id == b.id).all()
        result.append({
            "id": b.id,
            "name": b.name,
            "status": b.status,
            "legs": [_serialize(l) for l in legs],
        })
    return {"data": result}


@router.post("/trading/basket-orders")
def create_basket(req: BasketRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)

    existing_count = db.query(models.MockBasket).filter(models.MockBasket.user_id == user.id).count()
    if existing_count >= 5:
        raise HTTPException(status_code=400, detail="Basket limit reached (max 5)")

    basket = models.MockBasket(user_id=user.id, name=req.name, status="ACTIVE")
    db.add(basket)
    db.flush()
    for leg in req.legs:
        db.add(models.MockBasketLeg(
            basket_id=basket.id,
            symbol=leg.symbol,
            security_id=leg.security_id,
            exchange_segment=leg.exchange_segment,
            transaction_type=leg.transaction_type,
            quantity=leg.quantity,
            order_type=leg.order_type,
            product_type=leg.product_type,
            price=leg.price or 0.0,
        ))
    db.commit()
    return {"data": {"basket_id": basket.id}}


@router.post("/trading/basket-orders/{basket_id}/legs")
def append_basket_legs(basket_id: int, req: BasketAppendRequest, db: Session = Depends(get_db)):
    basket = db.query(models.MockBasket).filter(models.MockBasket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    if not req.legs:
        raise HTTPException(status_code=400, detail="No legs provided")

    for leg in req.legs:
        db.add(models.MockBasketLeg(
            basket_id=basket.id,
            symbol=leg.symbol,
            security_id=leg.security_id,
            exchange_segment=leg.exchange_segment,
            transaction_type=leg.transaction_type,
            quantity=leg.quantity,
            order_type=leg.order_type,
            product_type=leg.product_type,
            price=leg.price or 0.0,
        ))

    basket.updated_at = ist_now()
    db.commit()
    return {"data": {"basket_id": basket.id, "legs_added": len(req.legs)}}


@router.post("/trading/basket-orders/execute")
def execute_basket(req: BasketExecuteRequest, db: Session = Depends(get_db)):
    basket_id = req.basket_id
    basket = db.query(models.MockBasket).filter(models.MockBasket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    legs = db.query(models.MockBasketLeg).filter(models.MockBasketLeg.basket_id == basket_id).all()
    results = []
    for leg in legs:
        order_req = OrderRequest(
            user_id=basket.user_id,
            symbol=leg.symbol,
            security_id=leg.security_id,
            exchange_segment=leg.exchange_segment,
            transaction_type=leg.transaction_type,
            quantity=leg.quantity,
            order_type=leg.order_type,
            product_type=leg.product_type,
            price=leg.price,
        )
        # Resolve user for basket and call core placement synchronously
        basket_user = db.query(models.UserAccount).filter(models.UserAccount.id == basket.user_id).first()
        if not basket_user:
            basket_user = _get_or_create_admin(db)
        results.append(_place_order_core(order_req, db, basket_user))
    basket.status = "EXECUTED"
    basket.updated_at = ist_now()
    db.commit()
    return {"data": results}


@router.post("/api/calculate-margin")
async def calculate_margin(req: MarginRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)
    margin = _get_or_create_margin(db, user.id)

    price = req.price or 0.0
    if price <= 0 and req.symbol:
        price = _get_ltp(req.symbol, price)

    security_id = req.security_id
    exchange_segment = req.exchange_segment
    if security_id:
        try:
            int(str(security_id))
        except (TypeError, ValueError):
            security_id = None

    if not security_id and req.expiry and req.strike is not None and req.option_type:
        try:
            from app.services.dhan_security_id_mapper import dhan_security_mapper
            if not dhan_security_mapper.security_id_cache:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
                if loop is None:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                if not loop.is_running():
                    loop.run_until_complete(dhan_security_mapper.load_security_ids())

            opt_type = str(req.option_type).upper()
            underlying = _extract_option_underlying(req.symbol or "")
            expiry_norm = _normalize_expiry_iso(req.expiry)
            token_key = f"{opt_type}_{underlying}_{float(req.strike)}_{expiry_norm or req.expiry}"
            mapped_id = dhan_security_mapper.get_security_id(token_key)
            if not mapped_id and expiry_norm:
                mapped_id = dhan_security_mapper.get_security_id(
                    f"{opt_type}_{underlying}_{float(req.strike)}_{req.expiry}"
                )
            if mapped_id:
                security_id = str(mapped_id)
                option_data = dhan_security_mapper.get_option_data(token_key) or dhan_security_mapper.get_option_data(
                    f"{opt_type}_{underlying}_{float(req.strike)}_{req.expiry}"
                )
                if option_data and not exchange_segment:
                    exchange_segment = option_data.get("segment") or exchange_segment
        except Exception:
            pass

    if not security_id and req.expiry and req.strike is not None and req.option_type:
        try:
            from app.market.instrument_master.registry import REGISTRY
            if not REGISTRY.loaded:
                REGISTRY.load()
            underlying = _extract_option_underlying(req.symbol or "")
            expiry_norm = _normalize_expiry_iso(req.expiry)
            for row in REGISTRY.get_by_symbol(underlying):
                row_expiry = _normalize_expiry_iso(row.get("SM_EXPIRY_DATE") or row.get("EXPIRY_DATE"))
                if expiry_norm and row_expiry != expiry_norm:
                    continue
                row_option = (row.get("OPTION_TYPE") or "").upper()
                if row_option != str(req.option_type).upper():
                    continue
                try:
                    row_strike = float(row.get("STRIKE_PRICE"))
                except (TypeError, ValueError):
                    continue
                if abs(row_strike - float(req.strike)) > 1e-6:
                    continue
                row_sec_id = row.get("SECURITY_ID")
                if row_sec_id:
                    security_id = str(row_sec_id).strip()
                    if not exchange_segment:
                        row_exch = (row.get("EXCH_ID") or "").strip().upper()
                        if row_exch == "BSE":
                            exchange_segment = "BSE_FNO"
                        elif row_exch == "NSE":
                            exchange_segment = "NSE_FNO"
                    break
        except Exception:
            pass

    symbol_for_margin = req.symbol or ""
    if req.expiry and req.strike is not None and req.option_type:
        parts = (symbol_for_margin or "").split()
        if not parts or parts[-1].upper() not in {"CE", "PE"} or len(parts) < 3:
            try:
                opt_type = str(req.option_type).upper()
                underlying = _extract_option_underlying(req.symbol or "")
                expiry_norm = _normalize_expiry_iso(req.expiry)
                strike_val = float(req.strike)
                symbol_for_margin = f"{underlying} {expiry_norm or req.expiry} {strike_val} {opt_type}"
            except Exception:
                pass
    # Fetch margin from Dhan API - NO LOCAL CALCULATION
    dhan_margin = None
    try:
        dhan_margin = await _dhan_margin_for_order(
            user_id=user.id,
            exchange_segment=exchange_segment or req.exchange_segment,
            symbol=symbol_for_margin,
            transaction_type=req.transaction_type or "BUY",
            quantity=req.quantity,
            price=price,
            product_type=req.product_type or "MIS",
            security_id=security_id
        )
    except Exception as e:
        print(f"[MARGIN] Critical error in margin calculation: {e}")
        dhan_margin = None
    
    if dhan_margin:
        required = _apply_margin_multiplier(float(dhan_margin.get("margin") or 0.0), user, req.product_type)
        return {
            "margin": required,
            "availableMargin": margin.available_margin,
            "source": dhan_margin.get("source") or "DHAN_API",
            "raw": dhan_margin.get("raw"),
        }

    # Dhan API failed - no fallback to local calculation
    return {
        "margin": None,
        "availableMargin": margin.available_margin,
        "source": "DHAN_API_FAILED",
    }


@router.post("/margin/calculate")
async def calculate_margin_v2(req: MarginRequest, db: Session = Depends(get_db)):
    return await calculate_margin(req=req, db=db)


@router.post("/margin/calculate-multi")
async def calculate_margin_multi(req: MultiMarginRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)
    margin = _get_or_create_margin(db, user.id)

    # Fetch margin from Dhan API - NO LOCAL CALCULATION
    dhan_margin = await _dhan_margin_for_scripts(user.id, req.scripts)
    
    if dhan_margin:
        product_types = {str(s.product_type or "MIS").upper() for s in req.scripts}
        product_type = "MIS" if product_types == {"MIS"} else None
        required = _apply_margin_multiplier(float(dhan_margin.get("margin") or 0.0), user, product_type)
        return {
            "margin": required,
            "availableMargin": margin.available_margin,
            "source": dhan_margin.get("source") or "DHAN_API",
            "raw": dhan_margin.get("raw"),
        }

    # Dhan API failed - no fallback to local calculation
    return {
        "margin": None,
        "availableMargin": margin.available_margin,
        "source": "DHAN_API_FAILED",
    }


@router.get("/margin/account")
def margin_account(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)
    margin = _get_or_create_margin(db, user.id)
    return {"data": _serialize(margin)}


@router.post("/margin/portfolio")
async def portfolio_margin(req: PortfolioMarginRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)
    margin = _get_or_create_margin(db, user.id)

    # Convert portfolio positions to Dhan API format
    fno_positions = fetch_fno_positions(user.id)
    mcx_positions = fetch_mcx_positions(user.id)
    
    # Build scripts list for Dhan API
    portfolio_scripts = []
    
    # Add FNO positions
    for pos in fno_positions:
        script = {
            "exchangeSegment": pos["exchange_segment"] or "NSE_FNO",
            "transactionType": "BUY" if pos["quantity"] > 0 else "SELL",
            "quantity": abs(pos["quantity"]),
            "productType": "MARGIN",  # Portfolio positions are typically NRML
            "securityId": pos["symbol"],
            "price": pos["price"],
        }
        portfolio_scripts.append(script)
    
    # Add MCX positions
    for pos in mcx_positions:
        script = {
            "exchangeSegment": pos["exchange_segment"] or "MCX_COMM",
            "transactionType": "BUY" if pos["quantity"] > 0 else "SELL",
            "quantity": abs(pos["quantity"]),
            "productType": "MARGIN",  # Portfolio positions are typically NRML
            "securityId": pos["symbol"],
            "price": pos["price"],
        }
        portfolio_scripts.append(script)
    
    if not portfolio_scripts:
        return {
            "margin": 0.0,
            "availableMargin": margin.available_margin,
            "source": "DHAN_API_EMPTY_PORTFOLIO",
            "span": {"total_margin": 0.0},
            "mcx": {"total_margin": 0.0},
        }
    
    # Fetch portfolio margin from Dhan API
    try:
        margin_result = await dhan_margin_service.calculate_margin_multi(
            scripts=portfolio_scripts,
            include_positions=True,
            include_orders=True
        )
        
        if margin_result and "margin" in margin_result:
            return {
                "margin": float(margin_result["margin"]),
                "availableMargin": margin.available_margin,
                "source": "DHAN_API_PORTFOLIO",
                "span": {"total_margin": float(margin_result.get("margin", 0.0))},
                "mcx": {"total_margin": 0.0},  # Dhan API returns combined margin
                "raw": margin_result,
            }
    except Exception as e:
        print(f"[MARGIN] Portfolio Dhan API error: {e}")
    
    # Dhan API failed - no fallback to local calculation
    return {
        "margin": None,
        "availableMargin": margin.available_margin,
        "source": "DHAN_API_PORTFOLIO_FAILED",
        "span": {"total_margin": 0.0},
        "mcx": {"total_margin": 0.0},
    }


@router.post("/wallet/payin")
def wallet_payin(req: LedgerAdjustRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _update_ledger(db, user, credit=req.credit, debit=0.0, entry_type="PAYIN", remarks=req.remarks or "Payin")
    margin = _get_or_create_margin(db, user.id)
    margin.available_margin += req.credit * _normalize_margin_multiplier(user.margin_multiplier)
    margin.updated_at = ist_now()
    db.commit()
    return {"status": "ok"}


@router.post("/wallet/payout")
def wallet_payout(req: LedgerAdjustRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _update_ledger(db, user, credit=0.0, debit=req.debit, entry_type="PAYOUT", remarks=req.remarks or "Payout")
    margin = _get_or_create_margin(db, user.id)
    margin.available_margin = max(0.0, margin.available_margin - (req.debit * _normalize_margin_multiplier(user.margin_multiplier)))
    margin.updated_at = ist_now()
    db.commit()
    return {"status": "ok"}


@router.delete("/trading/basket-orders/{basket_id}")
def delete_basket(basket_id: int, db: Session = Depends(get_db)):
    basket = db.query(models.MockBasket).filter(models.MockBasket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    db.query(models.MockBasketLeg).filter(models.MockBasketLeg.basket_id == basket_id).delete()
    db.delete(basket)
    db.commit()
    return {"status": "deleted"}


# ---------- Admin Endpoints ----------

@router.get("/admin/users")
def list_users(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    _get_or_create_admin(db)
    if user.role == "SUPER_ADMIN":
        users = db.query(models.UserAccount).all()
    else:
        # ADMIN: hide SUPER_ADMIN accounts
        users = db.query(models.UserAccount).filter(models.UserAccount.role != "SUPER_ADMIN").all()
    return {"data": [_serialize(u) for u in users]}


@router.post("/admin/users")
def create_user(req: UserRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    _get_or_create_admin(db)
    # ADMIN cannot create SUPER_ADMIN
    if user.role == "ADMIN" and (req.role or "USER") == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions to create SUPER_ADMIN user")
    if not req.mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")
    plan_id = req.brokerage_plan_id
    if plan_id is None:
        plan = _get_or_create_default_plan(db)
        plan_id = plan.id
    user = models.UserAccount(
        username=req.username,
        email=req.email,
        mobile=req.mobile,
        user_id=req.mobile,
        role=req.role,
        status=req.status,
        allowed_segments=req.allowed_segments,
        wallet_balance=req.wallet_balance,
        margin_multiplier=_normalize_margin_multiplier(req.margin_multiplier),
        brokerage_plan_id=plan_id,
    )
    if req.initial_password:
        salt, digest = hash_password(req.initial_password)
        user.password_salt = salt
        user.password_hash = digest
        user.require_password_reset = True
    db.add(user)
    db.commit()
    db.refresh(user)
    margin = models.MarginAccount(
        user_id=user.id,
        available_margin=(user.wallet_balance or 0.0) * _normalize_margin_multiplier(user.margin_multiplier),
        used_margin=0.0
    )
    db.add(margin)
    db.commit()
    return {"data": _serialize(user)}


@router.put("/admin/users/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # ADMIN restrictions: cannot modify SUPER_ADMIN or other ADMIN accounts
    if user.role == "ADMIN":
        if target.role == "SUPER_ADMIN":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if target.role == "ADMIN" and target.id != user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to modify other ADMIN accounts")
    margin = _get_or_create_margin(db, target.id)
    previous_wallet = user.wallet_balance or 0.0
    previous_multiplier = _normalize_margin_multiplier(user.margin_multiplier)
    if req.username is not None:
        user.username = req.username
    if req.email is not None:
        user.email = req.email
    if req.mobile is not None:
        user.mobile = req.mobile
        user.user_id = req.mobile
    if req.role is not None:
        user.role = req.role
    if req.status is not None:
        user.status = req.status
    if req.allowed_segments is not None:
        user.allowed_segments = req.allowed_segments
    if req.wallet_balance is not None:
        user.wallet_balance = req.wallet_balance
    if req.margin_multiplier is not None:
        user.margin_multiplier = _normalize_margin_multiplier(req.margin_multiplier)
    if req.brokerage_plan_id is not None:
        user.brokerage_plan_id = req.brokerage_plan_id
    if req.initial_password:
        salt, digest = hash_password(req.initial_password)
        user.password_salt = salt
        user.password_hash = digest
        user.require_password_reset = True
    if req.wallet_balance is not None or req.margin_multiplier is not None:
        updated_multiplier = _normalize_margin_multiplier(user.margin_multiplier)
        if req.margin_multiplier is not None:
            margin.available_margin = max(
                0.0,
                (user.wallet_balance or 0.0) * updated_multiplier - (margin.used_margin or 0.0)
            )
        elif req.wallet_balance is not None:
            delta_wallet = (user.wallet_balance or 0.0) - previous_wallet
            margin.available_margin = max(
                0.0,
                margin.available_margin + (delta_wallet * previous_multiplier)
            )
        margin.updated_at = ist_now()
    target.updated_at = ist_now()
    db.commit()
    return {"data": _serialize(target)}

# List all brokerage plans
@router.get("/admin/brokerage-plans")
def list_brokerage_plans(db: Session = Depends(get_db)):
    _get_or_create_default_plan(db)
    plans = db.query(models.BrokeragePlan).all()
    return {"data": [_serialize(p) for p in plans]}


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # ADMIN cannot block ADMIN or SUPER_ADMIN (except themselves)
    if user.role == "ADMIN":
        if target.role == "SUPER_ADMIN":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if target.role == "ADMIN" and target.id != user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to block other ADMIN accounts")
    target.status = "BLOCKED"
    target.updated_at = ist_now()
    db.commit()
    return {"status": "blocked"}


@router.get("/admin/users/{user_id}/positions")
def admin_user_positions(user_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN" and target.role == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return list_positions(user_id=user_id, db=db)


@router.post("/admin/positions/backdate")
def admin_backdate_position(req: BackdatePositionRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Only SUPER_ADMIN can create back-dated positions
    require_role(user, ["SUPER_ADMIN"])

    # Resolve target user
    target = None
    if req.user_id is not None:
        target = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    elif req.mobile:
        target = db.query(models.UserAccount).filter(models.UserAccount.mobile == req.mobile).first()
    elif req.username:
        target = db.query(models.UserAccount).filter(models.UserAccount.username == req.username).first()
    else:
        raise HTTPException(status_code=400, detail="Provide mobile or user_id or username")

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent ADMIN-level restrictions here — only SUPER_ADMIN allowed by require_role

    # Check for existing position
    existing = db.query(models.MockPosition).filter(
        models.MockPosition.user_id == target.id,
        models.MockPosition.symbol == req.symbol,
        models.MockPosition.product_type == req.product_type,
    ).first()

    created_at = req.created_at or models.ist_now()

    if existing:
        if not req.merge:
            raise HTTPException(status_code=409, detail="Position already exists; set merge=true to combine")
        # Merge quantities and recompute average price
        total_qty = (existing.quantity or 0) + req.quantity
        if total_qty == 0:
            new_avg = req.avg_price
        else:
            new_avg = ((existing.avg_price or 0.0) * (existing.quantity or 0) + req.avg_price * req.quantity) / total_qty
        existing.quantity = total_qty
        existing.avg_price = new_avg
        existing.updated_at = created_at
        # Optionally backdate created_at if requested
        existing.created_at = created_at
        db.commit()
        db.refresh(existing)
        return {"data": _serialize(existing)}

    pos = models.MockPosition(
        user_id=target.id,
        symbol=req.symbol,
        exchange_segment=req.exchange_segment,
        product_type=req.product_type,
        quantity=req.quantity,
        avg_price=req.avg_price,
        status="OPEN",
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(pos)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    db.refresh(pos)
    return {"data": _serialize(pos)}


@router.post("/admin/users/{user_id}/positions/{position_id}/squareoff")
def admin_squareoff(user_id: int, position_id: int, req: SquareOffRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN" and target.role == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    pos = db.query(models.MockPosition).filter(models.MockPosition.id == position_id, models.MockPosition.user_id == user_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return close_position(position_id=position_id, req=req, db=db)


@router.post("/admin/users/{user_id}/restrict")
def admin_restrict_user(user_id: int, req: RestrictRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN" and target.role in ["ADMIN", "SUPER_ADMIN"] and target.id != user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions to modify this account")
    target.allowed_segments = req.allowed_segments
    target.updated_at = ist_now()
    db.commit()
    return {"data": _serialize(target)}


@router.post("/admin/users/{user_id}/brokerage-plan")
def admin_set_brokerage_plan(user_id: int, req: BrokeragePlanRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN" and target.role in ["ADMIN", "SUPER_ADMIN"] and target.id != user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions to modify this account")
    target.brokerage_plan_id = req.brokerage_plan_id
    target.updated_at = ist_now()
    db.commit()
    return {"data": _serialize(target)}


@router.post("/admin/margins/recalculate")
def admin_recalculate_margins(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, ["ADMIN", "SUPER_ADMIN"])
    users = db.query(models.UserAccount).all()
    updated = 0
    for user in users:
        margin = _get_or_create_margin(db, user.id)
        multiplier = _normalize_margin_multiplier(user.margin_multiplier)
        wallet = user.wallet_balance or 0.0
        used = margin.used_margin or 0.0
        margin.available_margin = max(0.0, (wallet * multiplier) - used)
        margin.updated_at = ist_now()
        updated += 1
    db.commit()
    return {"updated": updated}


@router.post("/admin/ledger/adjust")
def adjust_ledger(req: LedgerAdjustRequest, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # ADMIN restrictions: cannot adjust ledger for ADMIN/SUPER_ADMIN except themselves
    if caller.role == "ADMIN" and user.role in ["ADMIN", "SUPER_ADMIN"] and user.id != caller.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions to adjust this account")
    _update_ledger(db, user, credit=req.credit, debit=req.debit, entry_type="ADJUST", remarks=req.remarks or "Manual adjustment")
    db.commit()
    return {"status": "ok"}


@router.get("/admin/ledger")
def list_ledger(caller=Depends(get_current_user), user_id: Optional[int] = None, db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    query = db.query(models.LedgerEntry)
    if user_id:
        # If ADMIN requests a specific user's ledger, enforce visibility rules
        target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if caller.role == "ADMIN" and target.role in ["ADMIN", "SUPER_ADMIN"] and target.id != caller.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view this ledger")
        query = query.filter(models.LedgerEntry.user_id == user_id)
    else:
        if caller.role == "ADMIN":
            # ADMIN should not see SUPER_ADMIN ledger entries
            sub = db.query(models.UserAccount.id).filter(models.UserAccount.role == "SUPER_ADMIN").subquery()
            query = query.filter(~models.LedgerEntry.user_id.in_(sub))
    entries = query.order_by(models.LedgerEntry.created_at.desc()).all()
    return {"data": [_serialize(e) for e in entries]}


@router.get("/admin/ledger/summary")
def ledger_summary(caller=Depends(get_current_user), user_id: Optional[int] = None, db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    query = db.query(models.LedgerEntry)
    if user_id:
        target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if caller.role == "ADMIN" and target.role in ["ADMIN", "SUPER_ADMIN"] and target.id != caller.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view this summary")
        query = query.filter(models.LedgerEntry.user_id == user_id)
    else:
        if caller.role == "ADMIN":
            sub = db.query(models.UserAccount.id).filter(models.UserAccount.role == "SUPER_ADMIN").subquery()
            query = query.filter(~models.LedgerEntry.user_id.in_(sub))
    entries = query.all()
    total_credit = sum(e.credit or 0.0 for e in entries)
    total_debit = sum(e.debit or 0.0 for e in entries)
    return {"data": {"total_credit": total_credit, "total_debit": total_debit}}


@router.get("/admin/pnl/snapshots")
def list_pnl_snapshots(caller=Depends(get_current_user), user_id: Optional[int] = None, db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    query = db.query(models.PnlSnapshot)
    if user_id:
        target = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if caller.role == "ADMIN" and target.role in ["ADMIN", "SUPER_ADMIN"] and target.id != caller.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view this user's PnL")
        query = query.filter(models.PnlSnapshot.user_id == user_id)
    else:
        if caller.role == "ADMIN":
            # ADMIN should only see USER snapshots (exclude ADMIN/SUPER_ADMIN)
            user_ids = [u.id for u in db.query(models.UserAccount).filter(models.UserAccount.role == "USER").all()]
            query = query.filter(models.PnlSnapshot.user_id.in_(user_ids))
    snapshots = query.order_by(models.PnlSnapshot.created_at.desc()).all()
    return {"data": [_serialize(s) for s in snapshots]}


@router.post("/admin/pnl/snapshots")
def record_pnl_snapshot(req: PnlSnapshotRequest, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    _get_or_create_admin(db)
    users = db.query(models.UserAccount).all()
    if caller.role == "SUPER_ADMIN":
        target_ids = [req.user_id] if req.user_id else [u.id for u in users]
    else:
        # ADMIN: only allow snapshots for USER accounts; if specific user_id provided, enforce it's allowed
        if req.user_id:
            target_user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
            if not target_user:
                raise HTTPException(status_code=404, detail="User not found")
            if target_user.role != "USER" and target_user.id != caller.id:
                raise HTTPException(status_code=403, detail="Insufficient permissions to snapshot this account")
            target_ids = [req.user_id]
        else:
            target_ids = [u.id for u in users if u.role == "USER"]
    results = []
    for uid in target_ids:
        positions = db.query(models.MockPosition).filter(models.MockPosition.user_id == uid).all()
        realized = sum((p.realized_pnl or 0.0) for p in positions)
        mtm = 0.0
        for p in positions:
            ltp = _get_ltp(p.symbol, p.avg_price)
            mtm += (ltp - (p.avg_price or 0.0)) * (p.quantity or 0)
        total = realized + mtm
        snapshot = models.PnlSnapshot(
            user_id=uid,
            realized_pnl=realized,
            mtm=mtm,
            total_pnl=total
        )
        db.add(snapshot)
        results.append(snapshot)
    db.commit()
    return {"data": [_serialize(s) for s in results]}


@router.get("/admin/payouts")
def list_payouts(caller=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    query = db.query(models.LedgerEntry).filter(models.LedgerEntry.entry_type == "PAYOUT")
    if caller.role == "ADMIN":
        sub = db.query(models.UserAccount.id).filter(models.UserAccount.role == "SUPER_ADMIN").subquery()
        query = query.filter(~models.LedgerEntry.user_id.in_(sub))
    entries = query.all()
    return {"data": [_serialize(e) for e in entries]}


@router.get("/admin/payins")
def list_payins(caller=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    query = db.query(models.LedgerEntry).filter(models.LedgerEntry.entry_type == "PAYIN")
    if caller.role == "ADMIN":
        sub = db.query(models.UserAccount.id).filter(models.UserAccount.role == "SUPER_ADMIN").subquery()
        query = query.filter(~models.LedgerEntry.user_id.in_(sub))
    entries = query.all()
    return {"data": [_serialize(e) for e in entries]}


@router.post("/admin/margins/adjust")
def adjust_margin(req: MarginAdjustRequest, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    margin = _get_or_create_margin(db, req.user_id)
    target_user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if caller.role == "ADMIN" and target_user.role in ["ADMIN", "SUPER_ADMIN"] and target_user.id != caller.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions to modify this account's margin")
    if req.available_margin is not None:
        margin.available_margin = req.available_margin
    if req.used_margin is not None:
        margin.used_margin = req.used_margin
    margin.updated_at = ist_now()
    db.commit()
    return {"data": _serialize(margin)}


@router.post("/admin/market/force")
def admin_force_market(payload: dict, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    """Force market open/close for an exchange. payload: {exchange: 'NSE', state: 'open'|'close'|'none'}"""
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    ex = payload.get("exchange")
    state = payload.get("state")
    if not ex or state not in {"open", "close", "none"}:
        raise HTTPException(status_code=400, detail="exchange and valid state required")
    market_config.set_force(ex, state)
    return {"status": "ok", "exchange": ex, "state": state}


@router.post("/admin/price/update")
def admin_update_price(payload: dict, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    """Update dashboard price for a symbol. payload: {symbol: 'NIFTY', price: 18000.5}"""
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    sym = payload.get("symbol")
    price = payload.get("price")
    try:
        price_f = float(price)
    except Exception:
        raise HTTPException(status_code=400, detail="valid price required")
    if not sym:
        raise HTTPException(status_code=400, detail="symbol required")
    update_price(sym, price_f)
    return {"status": "ok", "symbol": sym, "price": price_f}


@router.post("/admin/market/depth")
def admin_set_depth(payload: dict, caller=Depends(get_current_user), db: Session = Depends(get_db)):
    """Set market depth for a symbol (admin test helper).
    payload: {symbol: 'RELIANCE', depth: {'bids':[{'price':..,'qty':..}], 'asks':[{'price':..,'qty':..}]}}
    """
    require_role(caller, ["ADMIN", "SUPER_ADMIN"])
    sym = payload.get("symbol")
    depth = payload.get("depth")
    if not sym or not isinstance(depth, dict):
        raise HTTPException(status_code=400, detail="symbol and depth required")
    key = (sym or "").upper().strip()
    market_state.setdefault("depth", {})[key] = depth
    return {"status": "ok", "symbol": key, "depth": depth}
