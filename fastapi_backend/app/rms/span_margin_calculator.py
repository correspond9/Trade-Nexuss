import re
from typing import Dict, List, Optional

from app.storage import models
from app.storage.db import SessionLocal

# ---------------- CONFIG ---------------- #

EXPOSURE_PERCENT_DEFAULT = 0.05


# ---------------- UTILS ---------------- #

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


def _is_fno_segment(exchange_segment: Optional[str]) -> bool:
    text = (exchange_segment or "").upper()
    if "MCX" in text:
        return False
    return "FNO" in text or "NFO" in text


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

    # Token formats: SYMBOL_EXPIRY_STRIKECE, SYMBOL_EXPIRY_FUT
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

    # Space-separated format: "SYMBOL EXPIRY STRIKE CE" or "SYMBOL EXPIRY FUT"
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


def fetch_user_positions(user_id) -> List[Dict[str, object]]:
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
            if not _is_fno_segment(pos.exchange_segment):
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


# ---------------- PORTFOLIO BUILD ---------------- #

def build_portfolio(positions):
    portfolio = {
        "futures": [],
        "long_options": [],
        "short_options": []
    }

    for p in positions:
        if p["instrument"] == "FUT":
            portfolio["futures"].append(p)
        elif p["instrument"] == "OPT":
            if p["quantity"] > 0:
                portfolio["long_options"].append(p)
            else:
                portfolio["short_options"].append(p)

    return portfolio


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


def calculate_futures_margin(portfolio, market_data):
    return 0


# ---------------- OPTION BUYING ---------------- #

def calculate_long_option_margin(portfolio, market_data):
    premium = 0

    for opt in portfolio["long_options"]:
        premium += (opt["price"] or 0.0) * abs(opt["quantity"])

    return premium


# ---------------- SHORT OPTION ---------------- #

def calculate_short_option_margin(portfolio, market_data):
    margin = 0
    for opt in portfolio["short_options"]:
        symbol = opt["symbol"]
        underlying = opt["underlying"]
        underlying_price = _get_ltp(market_data, symbol, underlying, opt["price"])
        try:
            from app.services.span_parameters_service import span_parameters_service
            risk_percent = span_parameters_service.get_short_option_addon(underlying or symbol, fallback=0.15)
        except Exception:
            risk_percent = 0.15
        strike = opt["strike"] or 0.0
        if opt["option_type"] == "PE":
            otm = max(0.0, underlying_price - strike)
        else:
            otm = max(0.0, strike - underlying_price)
        qty = abs(opt["quantity"])
        short_margin = (underlying_price * risk_percent * qty) - (otm * qty)
        margin += max(short_margin, underlying_price * 0.08 * qty)
    return margin


# ---------------- RISK ARRAY SIMULATION ---------------- #

def simulate_portfolio_risk(portfolio, market_data):
    try:
        from app.services.span_parameters_service import span_parameters_service
    except Exception:
        return 0
    arrays = []
    lots = []
    for fut in portfolio["futures"]:
        symbol = fut["symbol"]
        underlying = fut["underlying"]
        expiry = fut.get("expiry")
        arr = span_parameters_service.get_equity_risk_array("FUT", underlying or symbol, expiry, None, None)
        if arr:
            arrays.append(arr)
            lots.append(max(1, int(abs(fut["quantity"]) // _get_lot_size(market_data, symbol, underlying, 1))))
    for opt in portfolio["short_options"]:
        symbol = opt["symbol"]
        underlying = opt["underlying"]
        expiry = opt.get("expiry")
        strike = str(opt.get("strike")) if opt.get("strike") is not None else None
        opt_type = opt.get("option_type")
        arr = span_parameters_service.get_equity_risk_array("OPT", underlying or symbol, expiry, strike, opt_type)
        if arr:
            arrays.append(arr)
            lots.append(max(1, int(abs(opt["quantity"]) // _get_lot_size(market_data, symbol, underlying, 1))))
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


# ---------------- SPREAD BENEFIT ---------------- #

def calculate_spread_benefit(portfolio):
    hedge_benefit = 0

    # crude hedge detection example
    for short in portfolio["short_options"]:
        for long in portfolio["long_options"]:
            if short["underlying"] == long["underlying"]:
                if short["option_type"] == long["option_type"]:
                    qty = min(abs(short["quantity"]), abs(long["quantity"]))
                    hedge_benefit += 0.25 * qty

    return hedge_benefit


# ---------------- EXPOSURE MARGIN ---------------- #

def calculate_exposure_margin(portfolio, market_data):
    exposure = 0

    for fut in portfolio["futures"]:
        symbol = fut["symbol"]
        underlying = fut["underlying"]
        ltp = _get_ltp(market_data, symbol, underlying, fut["price"])
        try:
            from app.services.nse_reports_service import nse_reports_service
            percent = nse_reports_service.get_exposure_percent(underlying or symbol, default_percent=EXPOSURE_PERCENT_DEFAULT)
        except Exception:
            percent = EXPOSURE_PERCENT_DEFAULT
        exposure += (ltp * abs(fut["quantity"]) * percent)

    return exposure


# ---------------- MAIN CALCULATOR ---------------- #

def calculate_span_margin(user_id, market_data):
    positions = fetch_user_positions(user_id)
    return calculate_span_margin_for_positions(positions, market_data)


def calculate_span_margin_for_positions(positions, market_data):
    portfolio = build_portfolio(positions)

    futures_margin = calculate_futures_margin(portfolio, market_data)
    long_option_margin = calculate_long_option_margin(portfolio, market_data)
    short_option_margin = calculate_short_option_margin(portfolio, market_data)

    span_risk = simulate_portfolio_risk(portfolio, market_data)
    hedge_benefit = calculate_spread_benefit(portfolio)
    exposure_margin = calculate_exposure_margin(portfolio, market_data)

    total_margin = (
        futures_margin
        + long_option_margin
        + short_option_margin
        + span_risk
        + exposure_margin
        - hedge_benefit
    )
    total_lots = 0
    for fut in portfolio["futures"]:
        total_lots += max(1, int(abs(fut["quantity"]) // _get_lot_size(market_data, fut["symbol"], fut["underlying"], 1)))
    for opt in portfolio["short_options"]:
        total_lots += max(1, int(abs(opt["quantity"]) // _get_lot_size(market_data, opt["symbol"], opt["underlying"], 1)))
    per_lot = total_margin / max(1, total_lots)

    return {
        "total_margin": max(total_margin, 0),
        "futures_margin": futures_margin,
        "option_buy_margin": long_option_margin,
        "short_option_margin": short_option_margin,
        "span_risk": span_risk,
        "exposure_margin": exposure_margin,
        "hedge_benefit": hedge_benefit,
        "per_lot_margin": per_lot
    }
