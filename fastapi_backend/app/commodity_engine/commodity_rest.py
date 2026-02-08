"""REST + WebSocket endpoints for MCX commodity market cache."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.commodity_engine import commodity_engine
from app.commodity_engine.commodity_expiry_service import commodity_expiry_service
from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
from app.commodity_engine.commodity_futures_service import commodity_futures_service
from app.market_cache.options import get_option_chain
from app.market_cache.futures import list_futures

router = APIRouter()


@router.get("/api/v2/commodities/expiries")
async def get_commodity_expiries(underlying: str):
    expiries = commodity_expiry_service.registry.get_expiries(underlying)
    if not expiries:
        expiries = await commodity_expiry_service.fetch_expiry_list(underlying)
    selected = commodity_expiry_service.select_current_next(expiries)
    return {"status": "ok", "data": selected}


@router.get("/api/v2/commodities/options")
def get_commodity_options(underlying: str, expiry: str):
    chain = get_option_chain("MCX", underlying, expiry)
    return {"status": "ok", "data": chain}


@router.get("/api/v2/commodities/futures")
def get_commodity_futures(expiry: str | None = None, tab: str | None = None):
    if tab in ("current", "next"):
        rows = []
        index = 0 if tab == "current" else 1
        symbols = list(commodity_futures_service.futures_cache.keys())
        for symbol in symbols:
            expiries = commodity_expiry_service.registry.get_expiries(symbol)
            selected = commodity_expiry_service.select_current_next(expiries)
            if len(selected) <= index:
                continue
            exp = selected[index]
            entries = list_futures(exchange="MCX", symbol=symbol, expiry=exp)
            if entries:
                rows.extend(entries)
        return {"status": "ok", "data": rows}

    rows = list_futures(exchange="MCX", expiry=expiry)
    return {"status": "ok", "data": rows}


@router.post("/api/v2/commodities/refresh")
async def refresh_commodities():
    await commodity_engine.refresh_all("manual_refresh")
    return {"status": "ok"}

@router.post("/api/v2/commodities/refresh-closing")
async def refresh_commodities_closing():
    ok = await commodity_engine.populate_closing_snapshot_from_rest()
    return {"status": "ok" if ok else "failed"}

@router.websocket("/ws/commodities")
async def commodities_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Send snapshot every second (REST fallback still available)
            options = commodity_option_chain_service.option_chain_cache
            futures = commodity_futures_service.futures_cache
            await ws.send_json({"options": options, "futures": futures})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
    except Exception:
        return
