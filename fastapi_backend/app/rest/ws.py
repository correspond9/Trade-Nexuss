import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.market.live_prices import get_prices, get_dashboard_symbols
from app.ems.exchange_clock import is_market_open

router = APIRouter()


def _serialize_prices():
    """Build the REST/WS payload for the dashboard."""
    price_snapshot = get_prices()
    payload = {}
    for symbol, raw_value in price_snapshot.items():
        try:
            payload[str(symbol).upper()] = float(raw_value or 0.0)
        except (TypeError, ValueError):
            payload[str(symbol).upper()] = 0.0

    for symbol in get_dashboard_symbols():
        payload.setdefault(symbol, 0.0)

    market_open_any = False
    try:
        market_open_any = is_market_open("NSE") or is_market_open("BSE") or is_market_open("MCX")
    except Exception:
        market_open_any = False

    has_live_data = any(float(value or 0.0) > 0 for value in payload.values())

    payload["timestamp"] = datetime.utcnow().isoformat()
    payload["status"] = "active" if (market_open_any or has_live_data) else "waiting_for_data"
    return payload

@router.get("/prices")
def get_live_prices():
    """REST endpoint for live price polling - returns all tracked instrument prices"""
    return _serialize_prices()

@router.websocket("/ws/prices")
async def prices_ws(ws: WebSocket):
    """WebSocket endpoint for real-time price streaming"""
    await ws.accept()
    print(f"[WS] Client connected from {ws.client}")
    try:
        msg_count = 0
        while True:
            payload = _serialize_prices()
            msg_count += 1
            if msg_count % 10 == 0:  # Log every 10th message to avoid spam
                print(f"[WS] Sending prices to client: {msg_count} messages, payload: {payload}")
            await ws.send_json(payload)
            sleep_seconds = 1 if payload.get("status") == "active" else 30
            await asyncio.sleep(sleep_seconds)
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        print(f"[WS] Client disconnected, sent {msg_count} messages total")
