from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.storage.db import SessionLocal
from app.storage import models
from app.market.live_prices import get_prices
from app.rms.kill_switch import blocked as kill_switch_blocked
from app.execution_simulator import get_execution_engine

router = APIRouter(tags=["mock-exchange"])
EXEC_ENGINE = get_execution_engine()


# ---------- DB Dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    key = (symbol or "").upper().split()[0]
    ltp = prices.get(key)
    if ltp and isinstance(ltp, (int, float)):
        return float(ltp)
    return float(fallback_price or 0.0)


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
    if product_type == "MIS":
        return notional * 0.2
    return notional * 1.0


def _segment_allowed(user: models.UserAccount, exchange_segment: str) -> bool:
    allowed = {s.strip().upper() for s in (user.allowed_segments or "").split(",") if s.strip()}
    if not allowed:
        return True
    seg = (exchange_segment or "").split("_")[0].upper()
    return seg in allowed or exchange_segment.upper() in allowed


def _update_ledger(db: Session, user: models.UserAccount, credit: float, debit: float, entry_type: str, remarks: str):
    balance = (user.wallet_balance or 0.0) + credit - debit
    user.wallet_balance = balance
    user.updated_at = datetime.utcnow()
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
    position.updated_at = datetime.utcnow()


def _execute_order(db: Session, order: models.MockOrder, execution_price: float):
    remaining = order.quantity - order.filled_qty
    if remaining <= 0:
        return
    order.filled_qty += remaining
    order.status = "EXECUTED"
    order.updated_at = datetime.utcnow()

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


class UserRequest(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "USER"
    status: str = "ACTIVE"
    allowed_segments: Optional[str] = "NSE,NFO,BSE,MCX"
    wallet_balance: float = 0.0
    brokerage_plan_id: Optional[int] = None


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    allowed_segments: Optional[str] = None
    wallet_balance: Optional[float] = None
    brokerage_plan_id: Optional[int] = None


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


class SquareOffRequest(BaseModel):
    quantity: Optional[int] = None


class MarginRequest(BaseModel):
    user_id: Optional[int] = 1
    symbol: Optional[str] = None
    quantity: int = 1
    price: float = 0.0
    product_type: str = "MIS"


# ---------- Public Endpoints ----------

@router.get("/trading/orders")
def list_orders(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    query = db.query(models.MockOrder)
    if user_id:
        query = query.filter(models.MockOrder.user_id == user_id)
    orders = query.order_by(models.MockOrder.created_at.desc()).all()
    return {"data": [_serialize(o) for o in orders]}


@router.get("/orders")
def list_orders_legacy(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return list_orders(user_id=user_id, db=db)


@router.post("/trading/orders")
def place_order(req: OrderRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)

    if user.status != "ACTIVE" or kill_switch_blocked(user):
        raise HTTPException(status_code=403, detail="User blocked")

    if not _segment_allowed(user, req.exchange_segment):
        raise HTTPException(status_code=403, detail="Segment restricted")

    snapshot = EXEC_ENGINE._snapshot_for_order(req.symbol, req.exchange_segment)
    decision_price = snapshot.get("best_ask") if req.transaction_type == "BUY" else snapshot.get("best_bid")
    exec_price = decision_price or (req.price or 0.0)
    required = _margin_required(exec_price, req.quantity, req.product_type)
    margin = _get_or_create_margin(db, user.id)
    if margin.available_margin < required:
        raise HTTPException(status_code=400, detail="Insufficient margin")

    order = models.MockOrder(
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
    return {"data": _serialize(order)}


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
            "quantity": pos.quantity,
            "avg_price": pos.avg_price,
            "mtm": mtm,
            "realizedPnl": pos.realized_pnl,
            "status": pos.status,
        })
    return {"data": results}


@router.get("/positions")
def list_positions_legacy(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return list_positions(user_id=user_id, db=db)


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

    order = models.MockOrder(
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
        results.append(place_order(order_req, db))
    basket.status = "EXECUTED"
    basket.updated_at = datetime.utcnow()
    db.commit()
    return {"data": results}


@router.post("/api/calculate-margin")
def calculate_margin(req: MarginRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == (req.user_id or 1)).first()
    if not user:
        user = _get_or_create_admin(db)
    margin = _get_or_create_margin(db, user.id)
    required = _margin_required(req.price or 0.0, req.quantity, req.product_type)
    return {
        "margin": required,
        "availableMargin": margin.available_margin,
    }


@router.post("/margin/calculate")
def calculate_margin_v2(req: MarginRequest, db: Session = Depends(get_db)):
    return calculate_margin(req=req, db=db)


@router.post("/wallet/payin")
def wallet_payin(req: LedgerAdjustRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _update_ledger(db, user, credit=req.credit, debit=0.0, entry_type="PAYIN", remarks=req.remarks or "Payin")
    margin = _get_or_create_margin(db, user.id)
    margin.available_margin += req.credit
    db.commit()
    return {"status": "ok"}


@router.post("/wallet/payout")
def wallet_payout(req: LedgerAdjustRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _update_ledger(db, user, credit=0.0, debit=req.debit, entry_type="PAYOUT", remarks=req.remarks or "Payout")
    margin = _get_or_create_margin(db, user.id)
    margin.available_margin = max(0.0, margin.available_margin - req.debit)
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
def list_users(db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    users = db.query(models.UserAccount).all()
    return {"data": [_serialize(u) for u in users]}


@router.post("/admin/users")
def create_user(req: UserRequest, db: Session = Depends(get_db)):
    _get_or_create_admin(db)
    plan_id = req.brokerage_plan_id
    if plan_id is None:
        plan = _get_or_create_default_plan(db)
        plan_id = plan.id
    user = models.UserAccount(
        username=req.username,
        email=req.email,
        role=req.role,
        status=req.status,
        allowed_segments=req.allowed_segments,
        wallet_balance=req.wallet_balance,
        brokerage_plan_id=plan_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    margin = models.MarginAccount(user_id=user.id, available_margin=user.wallet_balance, used_margin=0.0)
    db.add(margin)
    db.commit()
    return {"data": _serialize(user)}


@router.put("/admin/users/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.username is not None:
        user.username = req.username
    if req.email is not None:
        user.email = req.email
    if req.role is not None:
        user.role = req.role
    if req.status is not None:
        user.status = req.status
    if req.allowed_segments is not None:
        user.allowed_segments = req.allowed_segments
    if req.wallet_balance is not None:
        user.wallet_balance = req.wallet_balance
    if req.brokerage_plan_id is not None:
        user.brokerage_plan_id = req.brokerage_plan_id
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"data": _serialize(user)}


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "BLOCKED"
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "blocked"}


@router.get("/admin/users/{user_id}/positions")
def admin_user_positions(user_id: int, db: Session = Depends(get_db)):
    return list_positions(user_id=user_id, db=db)


@router.post("/admin/users/{user_id}/positions/{position_id}/squareoff")
def admin_squareoff(user_id: int, position_id: int, req: SquareOffRequest, db: Session = Depends(get_db)):
    pos = db.query(models.MockPosition).filter(models.MockPosition.id == position_id, models.MockPosition.user_id == user_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return close_position(position_id=position_id, req=req, db=db)


@router.post("/admin/users/{user_id}/restrict")
def admin_restrict_user(user_id: int, req: RestrictRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.allowed_segments = req.allowed_segments
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"data": _serialize(user)}


@router.post("/admin/users/{user_id}/brokerage-plan")
def admin_set_brokerage_plan(user_id: int, req: BrokeragePlanRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.brokerage_plan_id = req.brokerage_plan_id
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"data": _serialize(user)}


@router.post("/admin/ledger/adjust")
def adjust_ledger(req: LedgerAdjustRequest, db: Session = Depends(get_db)):
    user = db.query(models.UserAccount).filter(models.UserAccount.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _update_ledger(db, user, credit=req.credit, debit=req.debit, entry_type="ADJUST", remarks=req.remarks or "Manual adjustment")
    db.commit()
    return {"status": "ok"}


@router.get("/admin/ledger")
def list_ledger(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.LedgerEntry)
    if user_id:
        query = query.filter(models.LedgerEntry.user_id == user_id)
    entries = query.order_by(models.LedgerEntry.created_at.desc()).all()
    return {"data": [_serialize(e) for e in entries]}


@router.get("/admin/ledger/summary")
def ledger_summary(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.LedgerEntry)
    if user_id:
        query = query.filter(models.LedgerEntry.user_id == user_id)
    entries = query.all()
    total_credit = sum(e.credit or 0.0 for e in entries)
    total_debit = sum(e.debit or 0.0 for e in entries)
    return {"data": {"total_credit": total_credit, "total_debit": total_debit}}


@router.get("/admin/payouts")
def list_payouts(db: Session = Depends(get_db)):
    entries = db.query(models.LedgerEntry).filter(models.LedgerEntry.entry_type == "PAYOUT").all()
    return {"data": [_serialize(e) for e in entries]}


@router.get("/admin/payins")
def list_payins(db: Session = Depends(get_db)):
    entries = db.query(models.LedgerEntry).filter(models.LedgerEntry.entry_type == "PAYIN").all()
    return {"data": [_serialize(e) for e in entries]}


@router.post("/admin/margins/adjust")
def adjust_margin(req: MarginAdjustRequest, db: Session = Depends(get_db)):
    margin = _get_or_create_margin(db, req.user_id)
    if req.available_margin is not None:
        margin.available_margin = req.available_margin
    if req.used_margin is not None:
        margin.used_margin = req.used_margin
    margin.updated_at = datetime.utcnow()
    db.commit()
    return {"data": _serialize(margin)}
