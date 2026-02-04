from datetime import datetime
from app.market.instrument_master.loader import MASTER


def _val(row, *keys):
    for k in keys:
        if k in row and row[k]:
            return str(row[k]).strip()
    return ""


def get_nifty_index():
    return None


def get_sensex_index():
    return None


def get_crudeoil_near_month():
    today = datetime.today().date()
    futures = []

    for r in MASTER.rows:
        sym = _val(r, "TradingSymbol", "tradingsymbol", "Symbol").upper()
        exp = _val(r, "Expiry", "expiry")
        if "CRUDEOIL" in sym and exp:
            try:
                futures.append((datetime.strptime(exp, "%Y-%m-%d").date(), r))
            except:
                pass

    futures.sort(key=lambda x: x[0])

    for exp, r in futures:
        if exp >= today:
            sid = _val(r, "SecurityId", "security_id")
            if sid:
                return int(sid)

    # ❗ NEVER CRASH
    print("[WARN] CRUDEOIL future not found - skipping subscription")
    return None
