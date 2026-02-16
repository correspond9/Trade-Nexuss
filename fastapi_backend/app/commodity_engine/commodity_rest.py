"""REST + WebSocket endpoints for MCX commodity market cache."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.commodity_engine import commodity_engine
from app.commodity_engine.commodity_expiry_service import commodity_expiry_service
from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
from app.commodity_engine.commodity_futures_service import commodity_futures_service
from app.commodity_engine.commodity_utils import fetch_dhan_credentials
from app.ems.exchange_clock import is_market_open
from app.market.market_state import state as market_state
from app.market_cache.options import get_option_chain
from app.market_cache.futures import list_futures

router = APIRouter(prefix="/commodities")

_QUOTE_LOCK = asyncio.Lock()
_QUOTE_LAST_CALL = 0.0
_QUOTE_MIN_INTERVAL_SECONDS = 0.75
_QUOTE_CACHE_TTL_SECONDS = 3.0
_QUOTE_CACHE: Dict[str, Dict[str, object]] = {}


@router.get("/expiries")
async def get_commodity_expiries(underlying: str):
    selected = await commodity_option_chain_service.get_available_expiries(underlying)
    return {"status": "ok", "data": selected}


def _format_expiry_code(expiry: str | None) -> str:
    if not expiry:
        return "—"
    try:
        dt = datetime.strptime(str(expiry), "%Y-%m-%d")
        return dt.strftime("%d%b").upper()
    except Exception:
        return str(expiry)


def _enrich_future_row(row: dict, market_open: bool) -> dict:
    ltp = row.get("ltp")
    prev_close = row.get("prev_close")
    base = prev_close
    change_pct = None
    if isinstance(ltp, (int, float)) and isinstance(base, (int, float)) and base:
        change_pct = ((float(ltp) - float(base)) / float(base)) * 100.0

    display_price = ltp if market_open else (prev_close if prev_close is not None else ltp)
    instrument = f"{row.get('symbol', '')} FUT {_format_expiry_code(row.get('expiry'))}".strip()

    payload = dict(row)
    payload.update(
        {
            "instrument": instrument,
            "change_pct": change_pct,
            "display_price": display_price,
        }
    )
    return payload


def _as_token(value: object) -> Optional[str]:
    try:
        return str(int(float(value)))
    except Exception:
        return None


def _extract_number(payload: object, keys: List[str]) -> Optional[float]:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload and payload[key] is not None:
            try:
                return float(payload[key])
            except Exception:
                continue
    nested = payload.get("data")
    if isinstance(nested, (dict, list)):
        return _extract_number(nested, keys)
    return None


def _extract_depth(payload: object) -> Dict[str, List[Dict[str, float]]]:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return {"bids": [], "asks": []}

    container = payload.get("depth") or payload.get("market_depth") or payload.get("depth_data") or payload
    if not isinstance(container, dict):
        return {"bids": [], "asks": []}

    bids_raw = container.get("bids") or container.get("bid") or container.get("buy") or []
    asks_raw = container.get("asks") or container.get("ask") or container.get("sell") or []
    bids = _normalize_depth_side(bids_raw, limit=5)
    asks = _normalize_depth_side(asks_raw, limit=5)
    if bids or asks:
        return {"bids": bids, "asks": asks}

    nested = payload.get("data")
    if isinstance(nested, (dict, list)):
        return _extract_depth(nested)
    return {"bids": [], "asks": []}


async def _rate_limit_quote_api() -> None:
    global _QUOTE_LAST_CALL
    async with _QUOTE_LOCK:
        now = time.monotonic()
        wait = _QUOTE_MIN_INTERVAL_SECONDS - (now - _QUOTE_LAST_CALL)
        if wait > 0:
            await asyncio.sleep(wait)
        _QUOTE_LAST_CALL = time.monotonic()


async def _fetch_mcx_quotes(tokens: List[str]) -> Dict[str, Dict[str, object]]:
    normalized_tokens = [token for token in {_as_token(token) for token in tokens} if token]
    if not normalized_tokens:
        return {}

    now = time.monotonic()
    response_map: Dict[str, Dict[str, object]] = {}
    missing: List[str] = []
    for token in normalized_tokens:
        cached = _QUOTE_CACHE.get(token)
        if cached and (now - float(cached.get("ts") or 0.0)) <= _QUOTE_CACHE_TTL_SECONDS:
            payload = cached.get("payload")
            if isinstance(payload, dict):
                response_map[token] = payload
                continue
        missing.append(token)

    if not missing:
        return response_map

    creds = await fetch_dhan_credentials()
    if not creds:
        return response_map

    headers = {
        "access-token": creds["access_token"],
        "client-id": creds["client_id"],
        "Content-Type": "application/json",
    }

    await _rate_limit_quote_api()
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"MCX_COMM": [int(token) for token in missing]}
            async with session.post("https://api.dhan.co/v2/marketfeed/quote", json=payload, headers=headers, timeout=8) as response:
                if response.status != 200:
                    return response_map
                body = await response.json()
                segment = (body.get("data") or {}).get("MCX_COMM") or {}
                ts = time.monotonic()
                for token_key, quote_payload in segment.items():
                    token = _as_token(token_key)
                    if not token:
                        continue
                    if isinstance(quote_payload, list) and quote_payload:
                        quote_payload = quote_payload[0]
                    if isinstance(quote_payload, dict):
                        response_map[token] = quote_payload
                        _QUOTE_CACHE[token] = {"payload": quote_payload, "ts": ts}
    except Exception:
        return response_map

    return response_map


async def _apply_quote_fallback_to_futures(rows: List[dict]) -> None:
    to_resolve = []
    for row in rows:
        token = _as_token(row.get("token"))
        if not token:
            continue
        bid = row.get("bid")
        ask = row.get("ask")
        try:
            has_bid = bid is not None and float(bid) > 0
        except Exception:
            has_bid = False
        try:
            has_ask = ask is not None and float(ask) > 0
        except Exception:
            has_ask = False
        if not (has_bid and has_ask):
            to_resolve.append(token)

    if not to_resolve:
        return

    quotes = await _fetch_mcx_quotes(to_resolve)
    for row in rows:
        token = _as_token(row.get("token"))
        if not token:
            continue
        quote = quotes.get(token)
        if not quote:
            continue

        bid = _extract_number(quote, ["BID", "bid", "best_bid", "best_bid_price", "bid_price", "buy_price", "bp1"])
        ask = _extract_number(quote, ["ASK", "ask", "best_ask", "best_ask_price", "ask_price", "sell_price", "ap1"])
        ltp = _extract_number(quote, ["LTP", "ltp", "last", "last_price", "lastPrice"])
        depth = _extract_depth(quote)
        if (bid is None or bid <= 0) and depth.get("bids"):
            try:
                bid = float(depth["bids"][0].get("price"))
            except Exception:
                bid = bid
        if (ask is None or ask <= 0) and depth.get("asks"):
            try:
                ask = float(depth["asks"][0].get("price"))
            except Exception:
                ask = ask
        updates = {}
        if bid is not None and bid > 0:
            row["bid"] = bid
            updates["bid"] = bid
        if ask is not None and ask > 0:
            row["ask"] = ask
            updates["ask"] = ask
        if ltp is not None and ltp > 0:
            row["ltp"] = ltp
            updates["ltp"] = ltp

        symbol = str(row.get("symbol") or "").upper()
        if symbol and (depth.get("bids") or depth.get("asks")):
            market_state.setdefault("depth", {})[symbol] = depth

        if updates:
            commodity_futures_service.update_future_tick(
                symbol=str(row.get("symbol")),
                expiry=str(row.get("expiry")),
                ltp=updates.get("ltp"),
                bid=updates.get("bid"),
                ask=updates.get("ask"),
            )


@router.get("/options")
async def get_commodity_options(underlying: str, expiry: str):
    chain = get_option_chain("MCX", underlying, expiry)
    if not chain:
        chain = await commodity_engine.ensure_option_chain(underlying, expiry)
    return {"status": "ok", "data": chain}


@router.get("/futures")
async def get_commodity_futures(expiry: str | None = None, tab: str | None = None):
    market_open = bool(is_market_open("MCX"))
    if tab in ("current", "next"):
        rows = []
        index = 0 if tab == "current" else 1
        symbols = list(commodity_futures_service.futures_cache.keys())
        for symbol in symbols:
            available = sorted(list((commodity_futures_service.futures_cache.get(symbol) or {}).keys()))
            if len(available) <= index:
                continue
            exp = available[index]
            entries = list_futures(exchange="MCX", symbol=symbol, expiry=exp)
            if entries:
                rows.extend(entries)
        await _apply_quote_fallback_to_futures(rows)
        return {"status": "ok", "data": [_enrich_future_row(entry, market_open) for entry in rows], "market_open": market_open}

    rows = list_futures(exchange="MCX", expiry=expiry)
    await _apply_quote_fallback_to_futures(rows)
    return {"status": "ok", "data": [_enrich_future_row(entry, market_open) for entry in rows], "market_open": market_open}


def _normalize_depth_side(entries, limit: int = 5):
    normalized = []
    if not isinstance(entries, list):
        return normalized
    for item in entries:
        if isinstance(item, dict):
            price = item.get("price")
            qty = item.get("qty", item.get("quantity", item.get("volume")))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            price, qty = item[0], item[1]
        else:
            continue
        try:
            price_f = float(price)
            qty_f = float(qty)
            if price_f <= 0 or qty_f < 0:
                continue
            normalized.append({"price": price_f, "qty": qty_f})
        except Exception:
            continue
        if len(normalized) >= limit:
            break
    return normalized


@router.get("/depth")
async def get_commodity_depth(symbol: str):
    symbol_key = (symbol or "").strip().upper()
    if not symbol_key:
        return {"status": "ok", "data": {"bids": [], "asks": []}}

    depth = (market_state.get("depth") or {}).get(symbol_key) or {}
    bids = _normalize_depth_side(depth.get("bids"), limit=5)
    asks = _normalize_depth_side(depth.get("asks"), limit=5)

    if not bids and not asks:
        futures_rows = list_futures(exchange="MCX", symbol=symbol_key)
        if futures_rows:
            first = futures_rows[0]
            token = _as_token(first.get("token"))
            if token:
                quotes = await _fetch_mcx_quotes([token])
                quote = quotes.get(token)
                if quote:
                    depth_from_quote = _extract_depth(quote)
                    if depth_from_quote.get("bids") or depth_from_quote.get("asks"):
                        market_state.setdefault("depth", {})[symbol_key] = depth_from_quote
                        bids = _normalize_depth_side(depth_from_quote.get("bids"), limit=5)
                        asks = _normalize_depth_side(depth_from_quote.get("asks"), limit=5)
                    bid_q = _extract_number(quote, ["BID", "bid", "best_bid", "best_bid_price", "bid_price", "buy_price", "bp1"])
                    ask_q = _extract_number(quote, ["ASK", "ask", "best_ask", "best_ask_price", "ask_price", "sell_price", "ap1"])
                    commodity_futures_service.update_future_tick(
                        symbol=symbol_key,
                        expiry=str(first.get("expiry")),
                        bid=bid_q if bid_q and bid_q > 0 else None,
                        ask=ask_q if ask_q and ask_q > 0 else None,
                    )
            bid = first.get("bid")
            ask = first.get("ask")
            try:
                if bid is not None and float(bid) > 0:
                    bids = [{"price": float(bid), "qty": 0.0}]
            except Exception:
                pass
            try:
                if ask is not None and float(ask) > 0:
                    asks = [{"price": float(ask), "qty": 0.0}]
            except Exception:
                pass

    return {"status": "ok", "data": {"bids": bids[:5], "asks": asks[:5]}}


@router.post("/refresh")
async def refresh_commodities():
    await commodity_engine.refresh_all("manual_refresh")
    return {"status": "ok"}

@router.post("/refresh-closing")
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
