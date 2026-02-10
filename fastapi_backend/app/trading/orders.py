# ============================================================
# PAPER TRADING ORDERS ROUTER
# Safe, simulator-only order execution
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

# ============================================================
# MODELS
# ============================================================

class OrderRequest(BaseModel):
    symbol: str
    side: str        # BUY / SELL
    quantity: int
    order_type: str  # MARKET / LIMIT
    price: float | None = None


class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: float | None
    status: str
    timestamp: str


# ============================================================
# IN-MEMORY STORE (temporary for simulator)
# Later -> DB
# ============================================================

ORDERS_DB: List[OrderResponse] = []


# ============================================================
# PLACE ORDER
# ============================================================

@router.post("/", response_model=OrderResponse)
def place_order(order: OrderRequest):

    if order.side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Invalid order side")

    if order.order_type not in ["MARKET", "LIMIT"]:
        raise HTTPException(status_code=400, detail="Invalid order type")

    order_id = str(uuid4())

    new_order = OrderResponse(
        order_id=order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        order_type=order.order_type,
        price=order.price,
        status="FILLED",   # simulator instant fill
        timestamp=datetime.utcnow().isoformat()
    )

    ORDERS_DB.append(new_order)

    return new_order


# ============================================================
# GET ALL ORDERS
# ============================================================

@router.get("/", response_model=List[OrderResponse])
def get_orders():
    return ORDERS_DB


# ============================================================
# GET ORDER BY ID
# ============================================================

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):

    for order in ORDERS_DB:
        if order.order_id == order_id:
            return order

    raise HTTPException(status_code=404, detail="Order not found")
