"""
Authoritative Option Chain API Router
Serves frontend from central cache only - no direct Dhan API calls
"""

import logging
import asyncio
import time
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.authoritative_option_chain_service import authoritative_option_chain_service

logger = logging.getLogger(__name__)

router = APIRouter()
_warmup_lock = asyncio.Lock()
_last_warmup_by_underlying: Dict[str, float] = {}
_warmup_cooldown_seconds = 20.0


def _is_underlying_market_open(underlying: str) -> bool:
    try:
        from app.ems.exchange_clock import is_market_open

        symbol = str(underlying or "").strip().upper()
        if symbol in {"SENSEX", "BANKEX"}:
            return bool(is_market_open("BSE"))
        if symbol in {"CRUDEOIL", "GOLD", "SILVER", "NATURALGAS", "MCX"}:
            return bool(is_market_open("MCX"))
        return bool(is_market_open("NSE"))
    except Exception:
        return False


def _parse_iso_date(value: str):
    try:
        return datetime.fromisoformat(str(value).strip()[:10]).date()
    except Exception:
        return None


def _today_ist_date():
    try:
        from datetime import timedelta
        return (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()
    except Exception:
        return datetime.utcnow().date()

# STEP 10: SERVE FRONTEND FROM CACHE
@router.get("/live")
async def get_option_chain_live(
    underlying: str = Query(..., description="Underlying symbol (e.g., NIFTY, BANKNIFTY)"),
    expiry: str = Query(..., description="Expiry date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Get option chain from central cache - frontend reads ONLY from here
    
    Response must come ONLY from option_chain_cache
    """
    try:
        underlying = str(underlying or "").strip().upper()
        expiry = str(expiry or "").strip()
        logger.info(f"📊 Serving option chain from cache: {underlying} {expiry}")

        try:
            from app.market.live_prices import get_price
            latest_ltp = get_price(underlying)
            if latest_ltp is not None and float(latest_ltp) > 0:
                authoritative_option_chain_service.update_option_price_from_websocket(underlying, float(latest_ltp))
        except Exception:
            pass
        
        # Get from central cache
        option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
        served_expiry = expiry
        fallback_used = False
        
        if option_chain is None:
            # Guarded on-demand warm-up for cold cache / missing expiry.
            now = time.time()
            last_attempt = _last_warmup_by_underlying.get(underlying, 0.0)
            if now - last_attempt >= _warmup_cooldown_seconds:
                async with _warmup_lock:
                    now_locked = time.time()
                    last_attempt_locked = _last_warmup_by_underlying.get(underlying, 0.0)
                    if now_locked - last_attempt_locked >= _warmup_cooldown_seconds:
                        _last_warmup_by_underlying[underlying] = now_locked
                        try:
                            logger.info(f"♻️ Cache miss for {underlying} {expiry}; running on-demand market-aware warm-up")
                            await asyncio.wait_for(
                                authoritative_option_chain_service.populate_cache_with_market_aware_data(),
                                timeout=8.0,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ Warm-up timed out for {underlying}; serving cache miss response")
                        except Exception as warmup_error:
                            logger.warning(f"⚠️ Warm-up attempt failed for {underlying}: {warmup_error}")

                option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)

            if option_chain is None:
                try:
                    logger.info(f"♻️ Cache still missing for {underlying} {expiry}; running live-data bootstrap fallback")
                    await asyncio.wait_for(
                        authoritative_option_chain_service.populate_with_live_data(),
                        timeout=8.0,
                    )
                    option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Live-data bootstrap timed out for {underlying} {expiry}")
                except Exception as bootstrap_error:
                    logger.warning(f"⚠️ Live-data bootstrap failed for {underlying} {expiry}: {bootstrap_error}")

            if option_chain is None:
                try:
                    from app.market.closing_prices import get_closing_prices
                    closing_payload = get_closing_prices() or {}
                    if closing_payload:
                        authoritative_option_chain_service.populate_with_closing_prices_sync(closing_payload)
                        option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Closing-price fallback failed for {underlying} {expiry}: {fallback_error}")

            # If requested expiry is stale/missing, serve nearest available cached expiry instead of 404.
            if option_chain is None:
                available_expiries = authoritative_option_chain_service.get_available_expiries(underlying) or []
                if available_expiries:
                    requested_date = _parse_iso_date(expiry)
                    today = _today_ist_date()
                    parsed_available = [
                        (exp, _parse_iso_date(exp))
                        for exp in available_expiries
                    ]
                    parsed_available = [(exp, dt) for exp, dt in parsed_available if dt is not None]
                    parsed_available = [(exp, dt) for exp, dt in parsed_available if dt >= today]

                    if parsed_available:
                        if requested_date is not None and requested_date >= today:
                            future_or_same = [(exp, dt) for exp, dt in parsed_available if dt >= requested_date]
                            if future_or_same:
                                served_expiry = min(future_or_same, key=lambda item: item[1])[0]
                            else:
                                served_expiry = parsed_available[0][0]
                        else:
                            served_expiry = parsed_available[0][0]

                        option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, served_expiry)
                        fallback_used = option_chain is not None and served_expiry != expiry

                        if fallback_used:
                            logger.info(
                                f"🔁 Served fallback expiry for {underlying}: requested={expiry}, served={served_expiry}"
                            )

            if option_chain is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Option chain not found for {underlying} {expiry}"
                )
        
        try:
            from app.market.live_prices import get_price
            underlying_ltp = get_price(underlying)
        except Exception:
            underlying_ltp = None

        # Add metadata
        response = {
            "status": "success",
            "data": option_chain,
            "source": "central_cache",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": authoritative_option_chain_service.get_cache_statistics(),
            "underlying_ltp": underlying_ltp,
            "requested_expiry": expiry,
            "served_expiry": served_expiry,
            "expiry_fallback_used": fallback_used,
        }
        
        logger.info(f"✅ Served option chain for {underlying} {expiry}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to serve option chain: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.websocket("/ws/live")
async def option_chain_live_ws(
    ws: WebSocket,
    underlying: str,
    expiry: str,
):
    await ws.accept()
    symbol = str(underlying or "").strip().upper()
    exp = str(expiry or "").strip()
    try:
        while True:
            try:
                payload = await get_option_chain_live(underlying=symbol, expiry=exp)
                await ws.send_json(payload)
            except HTTPException as http_error:
                await ws.send_json({
                    "status": "error",
                    "detail": http_error.detail,
                    "underlying": symbol,
                    "expiry": exp,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as stream_error:
                await ws.send_json({
                    "status": "error",
                    "detail": str(stream_error),
                    "underlying": symbol,
                    "expiry": exp,
                    "timestamp": datetime.now().isoformat(),
                })

            sleep_seconds = 1 if _is_underlying_market_open(symbol) else 2
            await asyncio.sleep(sleep_seconds)
    except WebSocketDisconnect:
        logger.info(f"🔌 Option chain WS client disconnected: {symbol} {exp}")

@router.get("/available/underlyings")
async def get_available_underlyings() -> Dict[str, Any]:
    """Get list of available underlyings in cache"""
    try:
        underlyings = authoritative_option_chain_service.get_available_underlyings()
        
        return {
            "status": "success",
            "data": underlyings,
            "count": len(underlyings),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get available underlyings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/available/expiries")
async def get_available_expiries(
    underlying: str = Query(..., description="Underlying symbol")
) -> Dict[str, Any]:
    """Get list of available expiries for an underlying"""
    try:
        expiries = authoritative_option_chain_service.get_available_expiries(underlying)
        
        return {
            "status": "success",
            "underlying": underlying,
            "data": expiries,
            "count": len(expiries),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get available expiries: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/atm/{underlying}")
async def get_atm_strike(underlying: str) -> Dict[str, Any]:
    """Get current ATM strike for underlying"""
    try:
        atm_strike = authoritative_option_chain_service.get_atm_strike(underlying)
        
        if atm_strike is None:
            raise HTTPException(
                status_code=404,
                detail=f"ATM strike not available for {underlying}"
            )
        
        return {
            "status": "success",
            "underlying": underlying,
            "atm_strike": atm_strike,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get ATM strike: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/cache/stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """Get central cache statistics"""
    try:
        stats = authoritative_option_chain_service.get_cache_statistics()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get cache statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
