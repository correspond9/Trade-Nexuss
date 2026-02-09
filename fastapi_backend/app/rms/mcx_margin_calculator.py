import re
from typing import Dict, List, Optional

from app.storage import models
from app.storage.db import SessionLocal

# ---------------- CONFIG ---------------- #

EXPOSURE_PERCENT = 0.0


# ---------------- DB ---------------- #

def _coerce_user_id(user_id, db):
    if isinstance(user_id, int):
        return user_id
    if isinstance(user_id, str):
        text = user_id.strip()
        if text.isdigit():
            return int(text)
        user = db.query(models.UserAccount).filter(models.UserAccount.username == text).first()
        if user:
            return user.id
    return user_id


def _is_mcx_segment(exchange_segment: Optional[str]) -> bool:
    return "MCX" in (exchange_segment or "").upper()


def _parse_symbol(symbol: str) -> Dict[str, Optional[object]]:
    text = (symbol or "").strip()
    result = {
        "raw": text,
        "underlying": text,
        "instrument": "EQ",
        "expiry": None,
        "strike": None,
        "option_type": None,
    }

    if not text:
        return result

    if "_" in text:
        parts = text.split("_")
        if len(parts) >= 3:
            underlying = parts[0].strip()
            last = parts[-1].upper()
            if last == "FUT":
                result.update({
                    "underlying": underlying,
                    "instrument": "FUT",
                    "expiry": parts[-2].strip(),
                })
                return result

            match = re.match(r"^(?P<strike>\d+(?:\.\d+)?)(?P<opt>CE|PE)$", last)
            if match:
                result.update({
                    "underlying": underlying,
                    "instrument": "OPT",
                    "expiry": parts[-2].strip(),
                    "strike": float(match.group("strike")),
                    "option_type": match.group("opt"),
                })
                return result

    parts = text.split()
    if len(parts) >= 3:
        last = parts[-1].upper()
        if last in {"CE", "PE"}:
            strike = None
            try:
                strike = float(parts[-2])
            except ValueError:
                strike = None
            underlying = " ".join(parts[:-3]).strip() or parts[0]
            result.update({
                "underlying": underlying,
                "instrument": "OPT",
                "expiry": parts[-3].strip(),
                "strike": strike,
                "option_type": last,
            })
            return result
        if last == "FUT":
            underlying = " ".join(parts[:-2]).strip() or parts[0]
            result.update({
                "underlying": underlying,
                "instrument": "FUT",
                "expiry": parts[-2].strip(),
            })
            return result

    return result


def position_from_order(
    symbol: str,
    exchange_segment: Optional[str],
    transaction_type: str,
    quantity: int,
    price: float,
) -> Dict[str, object]:
    meta = _parse_symbol(symbol)
    qty = int(quantity or 0)
    if str(transaction_type or "BUY").upper() == "SELL":
        qty = -abs(qty)
    else:
        qty = abs(qty)

    return {
        "symbol": symbol,
        "exchange_segment": exchange_segment,
        "quantity": qty,
        "price": float(price or 0.0),
        "instrument": meta["instrument"],
        "option_type": meta["option_type"],
        "strike": meta["strike"],
        "expiry": meta["expiry"],
        "underlying": meta["underlying"],
    }


def fetch_mcx_positions(user_id) -> List[Dict[str, object]]:
    db = SessionLocal()
    try:
        resolved_user_id = _coerce_user_id(user_id, db)
        query = (
            db.query(models.MockPosition)
            .filter(models.MockPosition.user_id == resolved_user_id)
            .filter(models.MockPosition.quantity != 0)
        )
        positions = []
        for pos in query.all():
            if not _is_mcx_segment(pos.exchange_segment):
                continue

            meta = _parse_symbol(pos.symbol)
            positions.append({
                "symbol": pos.symbol,
                "exchange_segment": pos.exchange_segment,
                "quantity": pos.quantity,
                "price": pos.avg_price,
                "instrument": meta["instrument"],
                "option_type": meta["option_type"],
                "strike": meta["strike"],
                "expiry": meta["expiry"],
                "underlying": meta["underlying"],
            })

        return positions
    finally:
        db.close()


# ---------------- FUTURES MARGIN ---------------- #

def _market_lookup(market_data, symbol, underlying):
    return market_data.get(symbol) or market_data.get(underlying) or {}


def _get_ltp(market_data, symbol, underlying, fallback_price):
    data = _market_lookup(market_data, symbol, underlying)
    ltp = data.get("ltp")
    if ltp is None:
        return fallback_price or 0.0
    return ltp


def _get_lot_size(market_data, symbol, underlying, fallback_lot=1):
    data = _market_lookup(market_data, symbol, underlying)
    lot = data.get("lot_size")
    if not lot:
        try:
            from app.services.span_parameters_service import span_parameters_service
            return span_parameters_service.get_lot_size(underlying or symbol, fallback=fallback_lot)
        except Exception:
            return fallback_lot
    return lot


def calculate_futures_margin(positions, market_data):
    return 0


# ---------------- LONG OPTION ---------------- #

def calculate_long_option_margin(positions, market_data):
    premium = 0

    for p in positions:
        if p["instrument"] == "OPT" and p["quantity"] > 0:
            premium += (p["price"] or 0.0) * abs(p["quantity"])

    return premium


# ---------------- SHORT OPTION ---------------- #

def calculate_short_option_margin(positions, market_data):
    return 0


# ---------------- SHOCK SIMULATION ---------------- #

def simulate_mcx_risk(positions, market_data):
    try:
        from app.services.span_parameters_service import span_parameters_service
    except Exception:
        return 0
    arrays = []
    lots = []
    for p in positions:
        if p["instrument"] == "FUT":
            arr = span_parameters_service.get_mcx_risk_array("FUT", p["underlying"] or p["symbol"], p.get("expiry"), None, None)
            if arr:
                arrays.append(arr)
                lots.append(max(1, int(abs(p["quantity"]) // _get_lot_size(market_data, p["symbol"], p["underlying"], 1))))
        elif p["instrument"] == "OPT" and p["quantity"] < 0:
            strike = str(p.get("strike")) if p.get("strike") is not None else None
            arr = span_parameters_service.get_mcx_risk_array("OPT", p["underlying"] or p["symbol"], p.get("expiry"), strike, p.get("option_type"))
            if arr:
                arrays.append(arr)
                lots.append(max(1, int(abs(p["quantity"]) // _get_lot_size(market_data, p["symbol"], p["underlying"], 1))))
    if not arrays:
        return 0
    worst = 0
    for i in range(16):
        s = 0
        for idx, arr in enumerate(arrays):
            s += arr[i] * lots[idx]
        if s > worst:
            worst = s
    return worst


# ---------------- EXPOSURE ---------------- #

def calculate_exposure(positions, market_data):
    exposure = 0

    for p in positions:
        symbol = p["symbol"]
        underlying = p["underlying"]
        ltp = _get_ltp(market_data, symbol, underlying, p["price"])
        exposure += 0.0

    return exposure


# ---------------- MAIN ---------------- #

def calculate_mcx_margin(user_id, market_data):
    positions = fetch_mcx_positions(user_id)
    return calculate_mcx_margin_for_positions(positions, market_data)


def calculate_mcx_margin_for_positions(positions, market_data):
    futures_margin = calculate_futures_margin(positions, market_data)
    long_option_margin = calculate_long_option_margin(positions, market_data)
    short_option_margin = calculate_short_option_margin(positions, market_data)
    span_risk = simulate_mcx_risk(positions, market_data)
    exposure_margin = calculate_exposure(positions, market_data)

    total_margin = (
        0
        + long_option_margin
        + 0
        + span_risk
        + exposure_margin
    )
    total_lots = 0
    for p in positions:
        total_lots += max(1, int(abs(p["quantity"]) // _get_lot_size(market_data, p["symbol"], p["underlying"], 1)))
    per_lot = total_margin / max(1, total_lots)

    return {
        "total_margin": max(total_margin, 0),
        "futures_margin": 0,
        "long_option_margin": long_option_margin,
        "short_option_margin": 0,
        "span_risk": span_risk,
        "exposure_margin": exposure_margin,
        "per_lot_margin": per_lot
    }
