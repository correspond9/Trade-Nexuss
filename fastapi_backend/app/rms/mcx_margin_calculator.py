import re
from typing import Dict, List, Optional

from app.storage import models
from app.storage.db import SessionLocal

# ---------------- CONFIG ---------------- #

MCX_SPAN_PERCENT = {
    "CRUDEOIL": 0.12,
    "NATURALGAS": 0.14,
    "COPPER": 0.10,
    "ALUMINIUM": 0.10,
    "GOLD": 0.09,
    "GOLDM": 0.09,
    "SILVER": 0.11,
    "SILVERM": 0.11
}

EXPOSURE_PERCENT = 0.05

PRICE_SHOCKS = [-0.12, -0.08, -0.05, 0.05, 0.08, 0.12]
VOL_SHOCKS = [0.2, 0.4]


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
        return fallback_lot
    return lot


def calculate_futures_margin(positions, market_data):
    margin = 0

    for p in positions:
        if p["instrument"] != "FUT":
            continue

        symbol = p["symbol"]
        underlying = p["underlying"]
        ltp = _get_ltp(market_data, symbol, underlying, p["price"])
        lot = _get_lot_size(market_data, symbol, underlying)

        span_percent = MCX_SPAN_PERCENT.get(underlying or symbol, 0.12)

        contract_value = ltp * lot * abs(p["quantity"])
        margin += contract_value * span_percent

    return margin


# ---------------- LONG OPTION ---------------- #

def calculate_long_option_margin(positions, market_data):
    premium = 0

    for p in positions:
        if p["instrument"] == "OPT" and p["quantity"] > 0:
            lot = _get_lot_size(market_data, p["symbol"], p["underlying"])
            premium += (p["price"] or 0.0) * lot * abs(p["quantity"])

    return premium


# ---------------- SHORT OPTION ---------------- #

def calculate_short_option_margin(positions, market_data):
    margin = 0

    for p in positions:
        if p["instrument"] != "OPT" or p["quantity"] >= 0:
            continue

        symbol = p["symbol"]
        underlying_key = p["underlying"]
        underlying = _get_ltp(market_data, symbol, underlying_key, p["price"])
        lot = _get_lot_size(market_data, symbol, underlying_key)

        strike = p["strike"] or 0.0
        if p["option_type"] == "PE":
            intrinsic = max(0.0, strike - underlying)
        else:
            intrinsic = max(0.0, underlying - strike)
        base_margin = underlying * 0.15 * lot

        margin += max(base_margin - intrinsic, underlying * 0.1 * lot)

    return margin


# ---------------- SHOCK SIMULATION ---------------- #

def simulate_mcx_risk(positions, market_data):
    worst_loss = 0

    for price_move in PRICE_SHOCKS:
        for vol_move in VOL_SHOCKS:
            effective_move = price_move * (1 + vol_move)

            pnl = 0

            for p in positions:
                symbol = p["symbol"]
                underlying = p["underlying"]
                ltp = _get_ltp(market_data, symbol, underlying, p["price"])
                shocked_price = ltp * (1 + effective_move)
                lot = _get_lot_size(market_data, symbol, underlying)

                if p["instrument"] == "FUT":
                    pnl += (shocked_price - (p["price"] or 0.0)) * p["quantity"] * lot

                elif p["instrument"] == "OPT":
                    strike = p["strike"] or 0.0
                    if p["option_type"] == "PE":
                        intrinsic = max(0.0, strike - shocked_price)
                    else:
                        intrinsic = max(0.0, shocked_price - strike)
                    pnl -= intrinsic * lot * abs(p["quantity"])

            worst_loss = min(worst_loss, pnl)

    return abs(worst_loss)


# ---------------- EXPOSURE ---------------- #

def calculate_exposure(positions, market_data):
    exposure = 0

    for p in positions:
        symbol = p["symbol"]
        underlying = p["underlying"]
        ltp = _get_ltp(market_data, symbol, underlying, p["price"])
        lot = _get_lot_size(market_data, symbol, underlying)
        exposure += ltp * lot * abs(p["quantity"]) * EXPOSURE_PERCENT

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
        futures_margin
        + long_option_margin
        + short_option_margin
        + span_risk
        + exposure_margin
    )

    return {
        "total_margin": max(total_margin, 0),
        "futures_margin": futures_margin,
        "long_option_margin": long_option_margin,
        "short_option_margin": short_option_margin,
        "span_risk": span_risk,
        "exposure_margin": exposure_margin
    }
