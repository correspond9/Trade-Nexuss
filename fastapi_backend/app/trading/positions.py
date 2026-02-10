from fastapi import APIRouter

from app.trading.position_store import get as get_position
from app.trading.position_store import save as save_position
from app.trading.position_engine import update as update_position

router = APIRouter(prefix="/positions", tags=["Positions"])


# ------------------------------
# Get all positions for a user
# ------------------------------
@router.get("/{user}")
def get_positions(user: str):
    # For now: simple in-memory scan
    # Later we connect DB
    results = []

    # position_store currently holds dict:
    # positions[(user, symbol)]
    from app.trading.position_store import positions

    for (u, symbol), pos in positions.items():
        if u == user:
            results.append({
                "symbol": symbol,
                "qty": pos["qty"],
                "avg_price": pos["avg_price"]
            })

    return results


# ------------------------------
# Get position for one symbol
# ------------------------------
@router.get("/{user}/{symbol}")
def get_single_position(user: str, symbol: str):
    pos = get_position(user, symbol)
    return pos


# ------------------------------
# Simulate trade update
# ------------------------------
@router.post("/update")
def update_trade(user: str, symbol: str, qty: int):
    trade = {"qty": qty}

    position = get_position(user, symbol)
    updated = update_position(position, trade)

    save_position(user, symbol, updated)

    return {
        "message": "Position updated",
        "position": updated
    }
