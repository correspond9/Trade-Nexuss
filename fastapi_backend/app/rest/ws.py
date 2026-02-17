import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.market.live_prices import get_prices, get_dashboard_symbols

router = APIRouter()


def _serialize_prices():
    """Build the REST/WS payload for the dashboard."""
    price_snapshot = get_prices()
    payload = {symbol: float(price_snapshot.get(symbol) or 0.0) for symbol in get_dashboard_symbols()}
    payload["timestamp"] = datetime.utcnow().isoformat()
    payload["status"] = "active" if any(payload[symbol] for symbol in get_dashboard_symbols()) else "waiting_for_data"
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
