
"""Thin wrapper around execution simulator for OMS flow."""
from app.ems.exchange_clock import is_market_open
from app.execution_simulator import get_execution_engine


def execute(order):
    if not is_market_open(order["exchange"]):
        return {"status": "PENDING_AMO"}

    engine = get_execution_engine()
    snapshot = engine._snapshot_for_order(order.get("symbol"), order.get("segment"))
    bid = snapshot.get("best_bid")
    ask = snapshot.get("best_ask")
    if bid is None or ask is None:
        return {"status": "REJECTED", "reason": "NO_LIQUIDITY"}

    side = order.get("side") or order.get("transaction_type") or "BUY"
    top_price = ask if side == "BUY" else bid
    top_qty = snapshot.get("ask_qty") if side == "BUY" else snapshot.get("bid_qty")
    top_qty = top_qty or engine.config.default_ask_qty
    spread = ask - bid
    fills = engine.fill_engine.compute_fills(order.get("exchange", "NSE"), side, int(order.get("quantity", 0)), top_price, int(top_qty), spread)
    if not fills:
        return {"status": "PENDING"}
    fill = fills[0]
    return {"status": "FILLED", "price": fill.fill_price, "qty": fill.fill_quantity}
