"""
REST API endpoints for two-tier subscription system.
Watchlist, option chains, and subscription status.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, Dict, List
from pydantic import BaseModel
import re
from app.market.watchlist_manager import get_watchlist_manager
from app.market.atm_engine import get_atm_engine
from app.market.subscription_manager import get_subscription_manager
from app.market.ws_manager import get_ws_manager
from app.market.instrument_master.registry import REGISTRY
from app.schedulers.expiry_refresh_scheduler import get_expiry_scheduler
from app.routers.authoritative_option_chain import router as option_chain_router
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/v2", tags=["market"])

# Request/Response models
class AddWatchlistRequest(BaseModel):
    user_id: int
    symbol: str
    expiry: str
    instrument_type: str = "STOCK_OPTION"
    underlying_ltp: Optional[float] = None

class RemoveWatchlistRequest(BaseModel):
    user_id: int
    symbol: str
    expiry: str

class OptionChainRequest(BaseModel):
    symbol: str
    expiry: str
    underlying_ltp: float

class AdminSubscribeIndicesRequest(BaseModel):
    symbols: Optional[List[str]] = None
    tier: str = "TIER_B"

# ============================================================================
# WATCHLIST ENDPOINTS
# ============================================================================

@router.post("/watchlist/add")
async def add_to_watchlist(req: AddWatchlistRequest):
    """Add instrument to user watchlist and subscribe to option chain"""
    watchlist_mgr = get_watchlist_manager()
    result = watchlist_mgr.add_to_watchlist(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry,
        instrument_type=req.instrument_type,
        underlying_ltp=req.underlying_ltp
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    
    return result

@router.post("/watchlist/remove")
async def remove_from_watchlist(req: RemoveWatchlistRequest):
    """Remove from watchlist and unsubscribe option chain"""
    watchlist_mgr = get_watchlist_manager()
    result = watchlist_mgr.remove_from_watchlist(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/watchlist/{user_id}")
async def get_user_watchlist(user_id: int):
    """Get user's watchlist"""
    watchlist_mgr = get_watchlist_manager()
    watchlist = watchlist_mgr.get_user_watchlist(user_id)
    return {
        "user_id": user_id,
        "count": len(watchlist),
        "watchlist": watchlist
    }

# ============================================================================
# OPTION CHAIN ENDPOINTS
# ============================================================================

@router.get("/option-chain/{symbol}")
async def get_option_chain(
    symbol: str,
    expiry: str = Query(...),
    underlying_ltp: float = Query(...)
):
    """
    Get option chain for a symbol+expiry.
    Generates strikes based on ATM calculation.
    Does NOT subscribe - that happens via watchlist.
    """
    atm_engine = get_atm_engine()
    
    try:
        chain = atm_engine.generate_chain(
            symbol=symbol,
            expiry=expiry,
            underlying_ltp=underlying_ltp
        )
        return chain
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/option-chain/subscribe")
async def subscribe_option_chain(req: OptionChainRequest):
    """
    Explicitly subscribe to option chain strikes.
    Used for programmatic subscriptions or admin overrides.
    """
    atm_engine = get_atm_engine()
    sub_mgr = get_subscription_manager()
    
    try:
        # Generate chain
        chain = atm_engine.generate_chain(
            symbol=req.symbol,
            expiry=req.expiry,
            underlying_ltp=req.underlying_ltp,
            force_recalc=True
        )
        
        strikes = chain["strikes"]
        subscribed = []
        failed = []
        
        # Subscribe all strikes
        for strike in strikes:
            # CE
            token_ce = f"{req.symbol}_{req.expiry}_{strike:.0f}CE"
            success, msg, ws_id = sub_mgr.subscribe(
                token=token_ce,
                symbol=req.symbol,
                expiry=req.expiry,
                strike=strike,
                option_type="CE",
                tier="TIER_A"
            )
            if success:
                subscribed.append(token_ce)
            else:
                failed.append(token_ce)
            
            # PE
            token_pe = f"{req.symbol}_{req.expiry}_{strike:.0f}PE"
            success, msg, ws_id = sub_mgr.subscribe(
                token=token_pe,
                symbol=req.symbol,
                expiry=req.expiry,
                strike=strike,
                option_type="PE",
                tier="TIER_A"
            )
            if success:
                subscribed.append(token_pe)
            else:
                failed.append(token_pe)
        
        return {
            "symbol": req.symbol,
            "expiry": req.expiry,
            "option_chain": chain,
            "subscribed": subscribed,
            "failed": failed,
            "total_subscribed": len(subscribed)
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# SUBSCRIPTION STATUS ENDPOINTS
# ============================================================================

@router.get("/subscriptions/status")
async def get_subscription_status():
    """Get overall subscription status"""
    sub_mgr = get_subscription_manager()
    ws_mgr = get_ws_manager()
    
    return {
        "subscriptions": sub_mgr.get_ws_stats(),
        "websocket": ws_mgr.get_status()
    }


@router.get("/market/stream-status")
async def get_stream_status():
    """Return consolidated market stream status for admin monitoring."""
    from app.market_orchestrator import get_orchestrator
    from app.commodity_engine.commodity_ws_manager import commodity_ws_manager
    from app.dhan.live_feed import get_live_feed_status
    from app.market.ws_manager import get_ws_manager

    orchestrator_status = get_orchestrator().get_status()
    equity_ws_status = get_ws_manager().get_status()
    mcx_ws_status = commodity_ws_manager.get_status()
    live_feed_status = get_live_feed_status()

    return {
        "status": "ok",
        "orchestrator": orchestrator_status,
        "equity_ws": equity_ws_status,
        "mcx_ws": mcx_ws_status,
        "live_feed": live_feed_status,
    }


@router.post("/market/stream-reconnect")
async def reconnect_streams():
    """Clear cooldowns and trigger a single stream restart attempt."""
    from app.market_orchestrator import get_orchestrator
    from app.dhan import live_feed
    from app.commodity_engine.commodity_ws_manager import commodity_ws_manager

    live_feed.reset_cooldown()
    commodity_ws_manager.reset_block()
    get_orchestrator().start_streams_sync()

    return {"status": "ok", "message": "reconnect_triggered"}


# ================== ADMIN: MARKET HOURS & FORCE OVERRIDE ==================
@router.get("/admin/market-config")
async def get_market_config():
    from app.ems.market_config import market_config
    return {"status": "ok", "data": market_config.get()}


class MarketConfigUpdate(BaseModel):
    config: Dict[str, Dict]


@router.post("/admin/market-config")
async def update_market_config(payload: MarketConfigUpdate):
    from app.ems.market_config import market_config
    market_config.update(payload.config or {})
    return {"status": "ok", "data": market_config.get()}


class MarketForcePayload(BaseModel):
    exchange: str
    state: str  # "open" | "close" | "none"


@router.post("/admin/market-force")
async def set_market_force(payload: MarketForcePayload):
    from app.ems.market_config import market_config
    market_config.set_force(payload.exchange.strip().upper(), payload.state.strip().lower())
    return {"status": "ok", "data": market_config.get()}

@router.get("/subscriptions/active")
async def list_active_subscriptions(tier: Optional[str] = None):
    """List active subscriptions, optionally filtered by tier"""
    sub_mgr = get_subscription_manager()
    subs = sub_mgr.list_active_subscriptions(tier=tier)
    
    return {
        "tier": tier,
        "count": len(subs),
        "subscriptions": subs
    }

@router.get("/subscriptions/search")
async def search_active_subscriptions(
    q: str = Query(..., min_length=1),
    tier: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Search active subscriptions by token/symbol for autocomplete"""
    sub_mgr = get_subscription_manager()
    query = q.upper().strip()
    subs = sub_mgr.list_active_subscriptions(tier=tier)
    results = []

    for sub in subs:
        haystack = " ".join(
            str(part) for part in [
                sub.get("token"),
                sub.get("symbol"),
                sub.get("expiry"),
                sub.get("strike"),
                sub.get("option_type"),
                sub.get("symbol_canonical")
            ] if part
        ).upper()

        if query in haystack:
            results.append(sub)
            if len(results) >= limit:
                break

    return {
        "query": q,
        "tier": tier,
        "count": len(results),
        "results": results
    }

@router.get("/subscriptions/{token}")
async def get_subscription_details(token: str):
    """Get details for a specific subscription"""
    sub_mgr = get_subscription_manager()
    sub = sub_mgr.get_subscription(token)
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {
        "token": token,
        "details": sub
    }

@router.post("/admin/migrate-tier-a-to-b")
async def migrate_tier_a_to_b():
    """
    Move all currently active Tier A subscriptions to Tier B.
    Persists the change to the database and returns counts.
    """
    sub_mgr = get_subscription_manager()
    changed = 0
    for token, data in list(sub_mgr.subscriptions.items()):
        if (data.get("tier") or "").upper() == "TIER_A":
            data["tier"] = "TIER_B"
            changed += 1
    # Persist to DB
    try:
        sub_mgr.sync_to_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist: {e}")
    stats = sub_mgr.get_ws_stats()
    return {
        "action": "MIGRATE_TIER_A_TO_TIER_B",
        "changed_count": changed,
        "tier_a_count": stats.get("tier_a_count"),
        "tier_b_count": stats.get("tier_b_count"),
    }

# ============================================================================
# FUTURES QUOTE/LIST ENDPOINTS (served from backend cache)
# ============================================================================
@router.get("/futures/quote")
async def get_future_quote(
    exchange: str = Query(..., min_length=2),
    symbol: str = Query(..., min_length=1),
    expiry: str = Query(..., min_length=1),
):
    """
    Return futures quote from backend cache (no direct frontend WS).
    """
    try:
        from app.market_cache.futures import get_future
        entry = get_future(exchange.upper(), symbol.upper(), expiry)
        if not entry:
            raise HTTPException(status_code=404, detail="Future not found in cache")
        return {"status": "success", "data": entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/futures/list")
async def list_futures_cached(
    exchange: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    expiry: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List futures entries from backend cache with optional filters.
    """
    try:
        from app.market_cache.futures import list_futures
        rows = list_futures(exchange=exchange.upper() if exchange else None,
                            symbol=symbol.upper() if symbol else None,
                            expiry=expiry)
        return {"status": "success", "count": min(len(rows), limit), "data": rows[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# INSTRUMENT SEARCH ENDPOINTS (UNIVERSE, NOT JUST SUBSCRIPTIONS)
# ============================================================================

@router.get("/instruments/search")
async def search_instruments(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Return a list of underlying symbols matching query.
    Includes F&O eligibility flag to guide UI.
    """
    query = q.upper().strip()
    # Ensure registry loaded (startup does it; this is safe)
    if not REGISTRY.loaded:
        REGISTRY.load()

    # Search over underlying symbol keys
    underlyings = list(REGISTRY.by_underlying.keys())
    matched = []
    for sym in underlyings:
        if query in sym.upper():
            matched.append({
                "symbol": sym,
                "f_o_eligible": REGISTRY.is_f_o_eligible(sym),
                "count": len(REGISTRY.by_underlying.get(sym, []))
            })
            if len(matched) >= limit:
                break
    return {
        "query": q,
        "count": len(matched),
        "results": matched
    }

@router.get("/instruments/{symbol}/expiries")
async def get_instrument_expiries(symbol: str):
    """
    Return available expiries for an underlying symbol (stock/index).
    """
    if not REGISTRY.loaded:
        REGISTRY.load()
    expiries = REGISTRY.get_expiries_for_underlying(symbol.upper())
    return {
        "symbol": symbol.upper(),
        "count": len(expiries),
        "expiries": expiries
    }

def _normalize_expiry(expiry: str) -> datetime.date | None:
    text = (expiry or "").strip().upper()
    for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%b%y", "%d%B%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None

@router.get("/instruments/futures/search")
async def search_stock_futures_current_next(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search NSE stock and index futures (current + next monthly) by query.
    Returns token-like entries for UI suggestions.
    """
    query = q.upper().strip()
    if not REGISTRY.loaded:
        REGISTRY.load()

    today = datetime.now().date()

    results = []
    # Candidate symbols = F&O stocks + known indices
    index_symbols = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX"}
    candidates = sorted(set(REGISTRY.f_o_stocks) | index_symbols)

    # Tokenize query and drop generic words
    tokens = [t for t in re.split(r"\s+", query) if t]
    tokens = [t for t in tokens if t not in {"FUT", "FUTURE", "FUTURES"}]

    for sym in candidates:
        hay = sym.upper()
        if tokens and not any(t in hay for t in tokens):
            continue
        # Collect expiries that have FUTSTK/FUTIDX instruments only
        expiries = set()
        records = REGISTRY.by_underlying.get(sym.upper(), [])
        for row in records:
            instr = (row.get("INSTRUMENT_TYPE") or "").strip().upper()
            if instr not in {"FUTSTK", "FUTIDX"}:
                continue
            exp = (row.get("SM_EXPIRY_DATE") or "").strip()
            dt = _normalize_expiry(exp)
            if dt and dt >= today:
                expiries.add(exp)
        parsed = sorted([(exp, _normalize_expiry(exp)) for exp in expiries if _normalize_expiry(exp)], key=lambda x: x[1])
        # Pick current and next month
        selected = [exp for exp, _ in parsed[:2]]
        for exp in selected:
            # Construct suggestion payload
            token = f"{sym}_{exp}_FUT"
            results.append({
                "token": token,
                "symbol": sym,
                "expiry": exp,
                "option_type": None,
                "exchange": "NSE",
                "lot_size": 1,
                "tier": "TIER_A",  # Futures fall under on-demand tier for user
                "active": False
            })
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@router.get("/options/strikes/search")
async def search_option_strikes_near_atm(
    q: str = Query(..., min_length=1),
    underlying: Optional[str] = Query(None),
    tab: Optional[str] = Query("current"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search option strikes near a target value or ATM for index/stocks.
    - If 'underlying' provided, restrict to that symbol, else search common indices.
    - 'tab' chooses current or next expiry.
    Returns CE/PE suggestion entries suitable for watchlist.
    """
    if not REGISTRY.loaded:
        REGISTRY.load()
    # Detect underlying from query if not provided
    if underlying:
        symbols = [underlying.upper()]
    else:
        q_tokens = [t for t in re.split(r"\s+", q.upper().strip()) if t]
        known = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX"}
        symbols = [t for t in q_tokens if t in known] or list(known)
    # Parse target strike if numeric
    target = None
    num = re.search(r"(\d+(?:\.\d+)?)", q)
    if num:
        try:
            target = float(num.group(1))
        except Exception:
            target = None

    today = datetime.now().date()
    suggestions = []
    for sym in symbols:
        expiries = REGISTRY.get_expiries_for_underlying(sym)
        parsed = [(exp, _normalize_expiry(exp)) for exp in expiries]
        parsed = [(exp, dt) for exp, dt in parsed if dt and dt >= today]
        parsed.sort(key=lambda x: x[1])
        if not parsed:
            continue
        selected_list: List[str] = []
        exp_to_dt: Dict[str, datetime.date] = {}
        if sym in {"NIFTY", "SENSEX"}:
            parsed_sorted = sorted(parsed, key=lambda x: x[1])
            for exp, dt in parsed_sorted[:3]:
                selected_list.append(exp)
                exp_to_dt[exp] = dt
        elif sym == "BANKNIFTY":
            groups = {}
            for exp, dt in parsed:
                key = (dt.year, dt.month)
                groups.setdefault(key, []).append((exp, dt))
            keys_sorted = sorted(groups.keys(), key=lambda k: (k[0], k[1]))
            cur_idx = 0
            for i, k in enumerate(keys_sorted):
                if datetime(k[0], k[1], 1).date() >= datetime(today.year, today.month, 1).date():
                    cur_idx = i
                    break
            if keys_sorted:
                cur_key = keys_sorted[cur_idx]
                cur_month_last_exp, cur_month_last_dt = sorted(groups[cur_key], key=lambda x: x[1])[-1]
                selected_list.append(cur_month_last_exp)
                exp_to_dt[cur_month_last_exp] = cur_month_last_dt
                if cur_idx + 1 < len(keys_sorted):
                    next_key = keys_sorted[cur_idx + 1]
                    next_month_last_exp, next_month_last_dt = sorted(groups[next_key], key=lambda x: x[1])[-1]
                    selected_list.append(next_month_last_exp)
                    exp_to_dt[next_month_last_exp] = next_month_last_dt
        else:
            parsed_sorted = sorted(parsed, key=lambda x: x[1])
            for exp, dt in parsed_sorted[:2]:
                selected_list.append(exp)
                exp_to_dt[exp] = dt
        # Estimate ATM using cached/REST LTP if target not provided
        if target is None:
            try:
                # Best-effort LTP fetch
                ltp_resp = await get_underlying_ltp(sym)  # reuse internal function
                ltp_val = float(ltp_resp.get("ltp") or 0.0)
            except Exception:
                ltp_val = 0.0
        else:
            ltp_val = target
        step = REGISTRY.get_strike_step(sym)
        atm = round(ltp_val / step) * step if step > 0 else ltp_val
        offsets_order = [0, 1, -1, 2, -2, 3, -3]
        window = []
        for off in offsets_order:
            strike = atm + (off * step)
            if strike > 0:
                window.append(strike)
        built = []
        for selected_exp in selected_list:
            dt = exp_to_dt.get(selected_exp)
            days_left = (dt - today).days if dt else 9999
            for strike in window:
                dist = abs((ltp_val or 0.0) - strike)
                token_ce = f"{sym}_{selected_exp}_{int(strike)}CE"
                token_pe = f"{sym}_{selected_exp}_{int(strike)}PE"
                built.append((
                    dist, days_left, {
                        "token": token_ce,
                        "symbol": sym,
                        "expiry": selected_exp,
                        "strike": strike,
                        "option_type": "CE",
                        "exchange": "NSE",
                        "tier": "TIER_A",
                        "active": False
                    }
                ))
                built.append((
                    dist, days_left, {
                        "token": token_pe,
                        "symbol": sym,
                        "expiry": selected_exp,
                        "strike": strike,
                        "option_type": "PE",
                        "exchange": "NSE",
                        "tier": "TIER_A",
                        "active": False
                    }
                ))
        built.sort(key=lambda x: (x[0], x[1]))
        suggestions.extend([item for _, _, item in built][:limit])
    return {
        "query": q,
        "count": len(suggestions),
        "results": suggestions[:limit]
    }

@router.get("/market/underlying-ltp/{symbol}")
async def get_underlying_ltp(symbol: str):
    """Return latest underlying LTP from live price cache"""
    from app.market.live_prices import get_price
    from app.market.live_prices import update_price
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    symbol_upper = symbol.upper()
    ltp = get_price(symbol_upper)
    if ltp is None:
        # Fallback to REST quote to recover missing index LTP (e.g., BANKNIFTY)
        market_data = await authoritative_option_chain_service._fetch_market_data_from_api(symbol_upper)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No LTP available for {symbol_upper}")

        ltp = market_data.get("current_price")
        if ltp is None:
            raise HTTPException(status_code=404, detail=f"No LTP available for {symbol_upper}")

        update_price(symbol_upper, float(ltp))

    # Update ATM in cache for indices on every request (keeps strike window current)
    try:
        authoritative_option_chain_service.update_option_price_from_websocket(
            symbol=symbol_upper,
            ltp=float(ltp)
        )
    except Exception:
        pass
    return {
        "status": "success",
        "symbol": symbol_upper,
        "ltp": ltp
    }

@router.post("/options/refresh-closing")
async def refresh_closing_cache():
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    ok = await authoritative_option_chain_service.populate_cache_with_market_aware_data()
    if not ok:
        raise HTTPException(status_code=500, detail="refresh_failed")
    stats = authoritative_option_chain_service.get_cache_statistics()
    return {"status": "success", "stats": stats}

@router.post("/options/refresh-closing-rest")
async def refresh_closing_cache_from_rest():
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    ok = await authoritative_option_chain_service.populate_closing_snapshot_from_rest()
    if not ok:
        raise HTTPException(status_code=500, detail="refresh_failed")
    stats = authoritative_option_chain_service.get_cache_statistics()
    return {"status": "success", "stats": stats}
@router.get("/market/option-depth")
async def get_option_depth(
    underlying: str = Query(...),
    expiry: str = Query(...),
    strike: float = Query(...),
    option_type: str = Query(..., min_length=2, max_length=2),
):
    """Return top-5 bid/ask depth for a specific option leg if available."""
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service

    option_type_upper = option_type.upper()
    if option_type_upper not in {"CE", "PE"}:
        raise HTTPException(status_code=400, detail="Invalid option_type")

    chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying.upper(), expiry)
    if not chain:
        raise HTTPException(status_code=404, detail="Option chain not found")

    strikes = chain.get("strikes") or {}
    strike_key = str(float(strike))
    strike_data = strikes.get(strike_key)
    if not strike_data:
        raise HTTPException(status_code=404, detail="Strike not found")

    leg = strike_data.get(option_type_upper) or {}
    depth = leg.get("depth") or {}
    bids = depth.get("bids") or []
    asks = depth.get("asks") or []

    return {
        "status": "success",
        "data": {
            "underlying": underlying.upper(),
            "expiry": expiry,
            "strike": float(strike),
            "option_type": option_type_upper,
            "bids": bids[:5],
            "asks": asks[:5],
            "bid": leg.get("bid"),
            "ask": leg.get("ask"),
            "ltp": leg.get("ltp"),
        }
    }

# ============================================================================
# INSTRUMENT SEARCH ENDPOINTS
# ============================================================================

@router.get("/instruments/search")
async def search_instruments(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Search for instruments by symbol (for watchlist UI)"""
    if len(q) < 1:
        return {"results": []}
    
    q_upper = q.upper()
    results = []
    
    # Search in registry
    for symbol, records in REGISTRY.by_symbol.items():
        if q_upper in symbol:
            results.append({
                "symbol": symbol,
                "count": len(records),
                "f_o_eligible": REGISTRY.is_f_o_eligible(symbol)
            })
        
        if len(results) >= limit:
            break
    
    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@router.get("/instruments/{symbol}/expiries")
async def get_expiries(symbol: str):
    """Get available expiries for a symbol"""
    expiries = REGISTRY.get_expiries_for_symbol(symbol)
    
    return {
        "symbol": symbol,
        "expiries": expiries,
        "count": len(expiries)
    }

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.post("/admin/unsubscribe-all-tier-a")
async def admin_unsubscribe_all_tier_a():
    """Admin: Unsubscribe all Tier A subscriptions (simulates EOD)"""
    sub_mgr = get_subscription_manager()
    count = sub_mgr.unsubscribe_all_tier_a()
    
    return {
        "action": "UNSUBSCRIBE_ALL_TIER_A",
        "count": count,
        "message": f"Unsubscribed {count} Tier A instruments"
    }

@router.post("/admin/clear-watchlists")
async def admin_clear_watchlists(user_id: Optional[int] = None):
    """Admin: Clear watchlists (all users or specific user)"""
    watchlist_mgr = get_watchlist_manager()
    
    if user_id:
        result = watchlist_mgr.clear_all_user_watchlist(user_id)
        return {
            "action": "CLEAR_WATCHLIST",
            "user_id": user_id,
            **result
        }
    else:
        return {
            "action": "CLEAR_ALL_WATCHLISTS",
            "message": "Not implemented - specify user_id"
        }

@router.get("/admin/ws-status")
async def admin_ws_status():
    """Admin: Get detailed WebSocket status"""
    ws_mgr = get_ws_manager()
    return ws_mgr.get_status()

@router.post("/admin/rebalance-ws")
async def admin_rebalance_ws():
    """Admin: Rebalance subscriptions across WS connections"""
    ws_mgr = get_ws_manager()
    result = ws_mgr.rebalance()
    
    return {
        "action": "REBALANCE_WS",
        **result
    }

@router.post("/admin/refresh-lot-sizes")
async def admin_refresh_lot_sizes():
    """Admin: Force-run lot size refresh from Dhan CSV and update caches."""
    from app.schedulers.lot_size_refresh_scheduler import get_lot_size_scheduler
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
    from app.commodity_engine.commodity_futures_service import commodity_futures_service
    from datetime import datetime

    ok = await get_lot_size_scheduler().refresh_all_lot_sizes()

    opt_updated = 0
    for underlying, exp_map in authoritative_option_chain_service.option_chain_cache.items():
        for expiry, skeleton in exp_map.items():
            try:
                if int(skeleton.lot_size) > 0:
                    opt_updated += 1
            except Exception:
                continue

    mcx_opt_updated = 0
    for symbol, exp_map in commodity_option_chain_service.option_chain_cache.items():
        for expiry, skeleton in exp_map.items():
            try:
                if int(skeleton.get("lot_size") or 0) > 0:
                    mcx_opt_updated += 1
            except Exception:
                continue

    mcx_fut_updated = 0
    for symbol, exp_map in commodity_futures_service.futures_cache.items():
        for expiry, entry in exp_map.items():
            try:
                if int(entry.get("lot_size") or 0) > 0:
                    mcx_fut_updated += 1
            except Exception:
                continue

    return {
        "status": "ok" if ok else "failed",
        "updated": {
            "index_option_chains": opt_updated,
            "mcx_option_chains": mcx_opt_updated,
            "mcx_futures": mcx_fut_updated,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.get("/admin/lot-sizes/status")
async def admin_lot_sizes_status():
    """Admin: Report last lot size refresh time and coverage across caches."""
    from app.schedulers.lot_size_refresh_scheduler import get_lot_size_scheduler
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
    from app.commodity_engine.commodity_futures_service import commodity_futures_service

    scheduler = get_lot_size_scheduler()
    last = scheduler.last_refresh.get("LOT_SIZE")
    last_txt = last.isoformat() if last else None

    opt_total = sum(1 for _, exp_map in authoritative_option_chain_service.option_chain_cache.items() for _ in exp_map.items())
    opt_with_lot = sum(1 for _, exp_map in authoritative_option_chain_service.option_chain_cache.items() for _, s in exp_map.items() if getattr(s, "lot_size", 0))

    mcx_opt_total = sum(1 for _, exp_map in commodity_option_chain_service.option_chain_cache.items() for _ in exp_map.items())
    mcx_opt_with_lot = sum(1 for _, exp_map in commodity_option_chain_service.option_chain_cache.items() for _, s in exp_map.items() if int((s.get("lot_size") or 0)) > 0)

    mcx_fut_total = sum(1 for _, exp_map in commodity_futures_service.futures_cache.items() for _ in exp_map.items())
    mcx_fut_with_lot = sum(1 for _, exp_map in commodity_futures_service.futures_cache.items() for _, s in exp_map.items() if int((s.get("lot_size") or 0)) > 0)

    return {
        "last_refresh": last_txt,
        "coverage": {
            "index_option_chains": {"total": opt_total, "with_lot_size": opt_with_lot},
            "mcx_option_chains": {"total": mcx_opt_total, "with_lot_size": mcx_opt_with_lot},
            "mcx_futures": {"total": mcx_fut_total, "with_lot_size": mcx_fut_with_lot},
        }
    }

@router.post("/admin/subscribe-indices")
async def admin_subscribe_indices(req: AdminSubscribeIndicesRequest):
    """Admin: Subscribe a minimal set of index symbols for dashboard live prices"""
    sub_mgr = get_subscription_manager()

    allowed = {"NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"}
    symbols = [s.upper() for s in (req.symbols or ["NIFTY", "BANKNIFTY", "SENSEX"])]
    symbols = [s for s in symbols if s in allowed]

    results = []
    for symbol in symbols:
        token = f"INDEX_{symbol}"
        success, msg, ws_id = sub_mgr.subscribe(
            token=token,
            symbol=symbol,
            expiry=None,
            strike=None,
            option_type=None,
            tier=req.tier
        )
        results.append({
            "symbol": symbol,
            "token": token,
            "success": success,
            "message": msg,
            "ws_id": ws_id
        })

    return {
        "action": "SUBSCRIBE_INDICES",
        "count": len(results),
        "results": results
    }

@router.get("/options/expiry-cache")
async def get_expiry_cache():
    """Inspect cached expiries fetched by the daily scheduler"""
    scheduler = get_expiry_scheduler()
    last_refresh = {
        symbol: ts.isoformat() if ts else None
        for symbol, ts in scheduler.last_refresh.items()
    }
    return {
        "status": "ok",
        "expiries": scheduler.cached_expiries,
        "last_refresh": last_refresh
    }

# ============================================================================
# INCLUDE AUTHORITATIVE OPTION CHAIN ROUTES
# ============================================================================
# Register nested router with dedicated prefix to avoid conflicts
# Routes will be at /api/v2/options/live, /api/v2/options/available/*, etc.
router.include_router(option_chain_router, prefix="/options", tags=["option-chain"])

print("[OK] Market API v2 endpoints loaded")
print("[OK] Authoritative option chain routes registered at /api/v2/options/*")
