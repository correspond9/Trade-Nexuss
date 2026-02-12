from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
import logging

from app.services.authoritative_option_chain_service import authoritative_option_chain_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/option-chain/{symbol}")
def get_option_chain(symbol: str, expiry: Optional[str] = Query(None), underlying_ltp: Optional[float] = Query(None)) -> Dict[str, Any]:
    """Compatibility endpoint: GET /api/v2/option-chain/{symbol}
    Tries to return option-chain from the authoritative cache when available.
    """
    try:
        sym = (symbol or "").upper()
        if expiry:
            oc = authoritative_option_chain_service.get_option_chain_from_cache(sym, expiry)
            if not oc:
                raise HTTPException(status_code=404, detail="Option chain not found")
            return {"status": "success", "chain": oc}

        # No expiry provided: try to return first available expiry
        expiries = authoritative_option_chain_service.get_available_expiries(sym)
        if not expiries:
            raise HTTPException(status_code=404, detail="No expiries available")
        first = expiries[0]
        oc = authoritative_option_chain_service.get_option_chain_from_cache(sym, first)
        if not oc:
            raise HTTPException(status_code=404, detail="Option chain not found")
        return {"status": "success", "chain": oc}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to serve option-chain compatibility: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/option-chain/live-straddle/{symbol}")
def get_live_straddle(symbol: str, expiry: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Return a simple live straddle snapshot built from authoritative cache."""
    try:
        sym = (symbol or "").upper()
        expiries = authoritative_option_chain_service.get_available_expiries(sym)
        if expiry:
            target = expiry
        else:
            if not expiries:
                raise HTTPException(status_code=404, detail="No expiries available")
            target = expiries[0]

        oc = authoritative_option_chain_service.get_option_chain_from_cache(sym, target)
        if not oc:
            raise HTTPException(status_code=404, detail="Option chain not found")

        atm = authoritative_option_chain_service.get_atm_strike(sym)
        strikes = oc.get("strikes", {})
        # find ATM strike data
        atm_key = str(atm)
        atm_data = strikes.get(atm_key)
        if not atm_data:
            # fallback: pick middle strike
            keys = sorted([float(k) for k in strikes.keys()])
            if not keys:
                raise HTTPException(status_code=404, detail="No strikes available")
            mid = keys[len(keys) // 2]
            atm_data = strikes.get(str(mid))

        return {"status": "success", "underlying": sym, "expiry": target, "atm_strike": atm, "straddle": atm_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to compute live straddle: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/option-chain/atm-by-lowest-premium/{symbol}/{expiry}")
def atm_by_lowest_premium(symbol: str, expiry: str) -> Dict[str, Any]:
    try:
        sym = (symbol or "").upper()
        oc = authoritative_option_chain_service.get_option_chain_from_cache(sym, expiry)
        if not oc:
            raise HTTPException(status_code=404, detail="Option chain not found")

        strikes = oc.get("strikes", {})
        best = None
        for s_str, s_data in strikes.items():
            try:
                ce = s_data.get("CE") or {}
                pe = s_data.get("PE") or {}
                premium = (ce.get("ltp") or 0) + (pe.get("ltp") or 0)
            except Exception:
                premium = None
            if premium is None:
                continue
            if best is None or premium < best[0]:
                best = (premium, float(s_str), s_data)

        if not best:
            raise HTTPException(status_code=404, detail="No premium data available")

        return {"status": "success", "symbol": sym, "expiry": expiry, "strike": best[1], "premium": best[0], "data": best[2]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to compute atm by lowest premium: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/option-chain/straddle-range/{symbol}/{expiry}/{atm_strike}")
def straddle_range(symbol: str, expiry: str, atm_strike: float, range_width: int = Query(5)) -> Dict[str, Any]:
    try:
        sym = (symbol or "").upper()
        oc = authoritative_option_chain_service.get_option_chain_from_cache(sym, expiry)
        if not oc:
            raise HTTPException(status_code=404, detail="Option chain not found")

        strikes = oc.get("strikes", {})
        keys = sorted([float(k) for k in strikes.keys()])
        # select strikes within +/- range_width strikes from atm_strike
        step = 1
        selected = []
        for k in keys:
            if abs(k - atm_strike) <= range_width * step:
                selected.append({"strike": k, "data": strikes.get(str(k))})

        return {"status": "success", "symbol": sym, "expiry": expiry, "atm_strike": atm_strike, "straddle_range": selected}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to compute straddle range: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Compatibility: search strikes endpoint used by frontend (watchlist/lookup)
@router.get("/options/strikes/search")
def search_strikes(q: str, limit: int = Query(20), underlying: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Search option strikes across authoritative cache and return lightweight results.
    Query params:
    - q: search text
    - limit: max results
    - underlying: optional filter for underlying symbol
    """
    try:
        text = (q or "").strip().upper()
        results: List[Dict[str, Any]] = []

        # Iterate relevant underlyings only (filter if provided)
        underlyings = [underlying] if underlying else authoritative_option_chain_service.get_available_underlyings()

        for u in underlyings:
            expiries = authoritative_option_chain_service.get_available_expiries(u)
            for exp in expiries:
                oc = authoritative_option_chain_service.get_option_chain_from_cache(u, exp)
                if not oc:
                    continue
                strikes = oc.get("strikes", {})
                for s_str, s_data in strikes.items():
                    try:
                        strike_val = float(s_str)
                    except Exception:
                        continue

                    # CE and PE entries
                    for opt_type in ("CE", "PE"):
                        opt = s_data.get(opt_type) or {}
                        symbol = opt.get("token") or f"{opt_type}_{u}_{strike_val}_{exp}"
                        display = f"{u} {exp} {int(strike_val)} {opt_type}"
                        # Match if query appears in symbol or display
                        if text in (str(symbol).upper()) or text in display:
                            results.append({
                                "token": str(opt.get("token") or symbol),
                                "symbol": u,
                                "option_type": opt_type,
                                "expiry": exp,
                                "strike": strike_val,
                                "exchange": "NSE",
                            })
                            if len(results) >= limit:
                                return {"results": results}

        return {"results": results}
    except Exception as e:
        logger.exception("Failed to search strikes: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
