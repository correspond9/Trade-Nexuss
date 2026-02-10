from app.ems.market_config import market_config

for ex in ["NSE", "BSE", "MCX"]:
    market_config.set_force(ex, "open")
    print(f"Set {ex} -> open")
