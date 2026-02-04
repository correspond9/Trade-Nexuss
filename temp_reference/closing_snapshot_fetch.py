import asyncio
import json

from app.services.authoritative_option_chain_service import authoritative_option_chain_service

UNDERLYINGS = ["NIFTY", "BANKNIFTY", "SENSEX"]

async def fetch_snapshot():
    await authoritative_option_chain_service.initialize()
    result = {}
    for underlying in UNDERLYINGS:
        market = await authoritative_option_chain_service._fetch_market_data_from_api(underlying)
        if not market:
            print(f"WARN: No market data for {underlying}")
            continue
        expiries = market.get("expiries", [])
        selected = authoritative_option_chain_service._select_current_next_expiries(underlying, expiries)
        result[underlying] = {
            "current_price": market.get("current_price", 0),
            "expiries": selected,
            "closing_prices": {},
        }
        for expiry in selected:
            chain = await authoritative_option_chain_service._fetch_option_chain_from_api(underlying, expiry)
            if not chain:
                print(f"WARN: No chain for {underlying} {expiry}")
                continue
            strikes_map = {}
            for strike in chain.get("strikes", []) or []:
                try:
                    strike_price = float(strike.get("strike_price", 0))
                except Exception:
                    continue
                if strike_price <= 0:
                    continue
                ce = strike.get("ce", {}) or strike.get("CE", {}) or {}
                pe = strike.get("pe", {}) or strike.get("PE", {}) or {}
                ce_ltp = ce.get("ltp") or ce.get("lastPrice") or strike.get("ce_ltp") or 0
                pe_ltp = pe.get("ltp") or pe.get("lastPrice") or strike.get("pe_ltp") or 0
                strikes_map[str(int(strike_price))] = {
                    "CE": float(ce_ltp) if ce_ltp else 0.0,
                    "PE": float(pe_ltp) if pe_ltp else 0.0,
                }
            result[underlying]["closing_prices"][expiry] = strikes_map
            await asyncio.sleep(0.25)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(fetch_snapshot())
