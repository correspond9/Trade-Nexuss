"""
Show strike ranges that SHOULD be subscribed based on hooks.py logic.
Since the backend uses ATM Engine with 101 strikes (ATM ±50), we calculate ranges.
"""

# Index configurations from authoritative_option_chain_service.py
INDEX_CONFIG = {
    "NIFTY": {
        "strike_interval": 50.0,
        "expiries_to_subscribe": 16,
    },
    "BANKNIFTY": {
        "strike_interval": 100.0,
        "expiries_to_subscribe": 7,
    },
    "SENSEX": {
        "strike_interval": 100.0,
        "expiries_to_subscribe": 7,
    }
}

# Current LTPs (approximate)
LTP = {
    "NIFTY": 24900,
    "BANKNIFTY": 51750,
    "SENSEX": 76500
}

print("\n" + "="*90)
print("TIER B WEBSOCKET SUBSCRIPTIONS - STRIKE RANGES (ATM ±50 for 101-strike chains)")
print("="*90)

for symbol, config in INDEX_CONFIG.items():
    strike_interval = config["strike_interval"]
    expiry_count = config["expiries_to_subscribe"]
    ltp = LTP[symbol]
    
    # Calculate ATM
    atm = round(ltp / strike_interval) * strike_interval
    
    # Calculate strike range: ATM ±50 strikes = ATM ± (50 * strike_interval)
    min_strike = atm - (50 * strike_interval)
    max_strike = atm + (50 * strike_interval)
    
    print(f"\n{symbol}:")
    print(f"  Current LTP: {ltp}")
    print(f"  ATM Strike: {atm}")
    print(f"  Strike Interval: {strike_interval}")
    print(f"  Expiries subscribed: {expiry_count}")
    print(f"  ")
    print(f"  Strike Range per expiry (101 strikes = ATM ±50):")
    print(f"    FROM: {int(min_strike)}")
    print(f"    TO:   {int(max_strike)}")
    print(f"    Total: 101 strikes")
    print(f"  ")
    print(f"  WebSocket tokens per expiry: {101 * 2} (101 CE + 101 PE)")
    print(f"  Total tokens for {expiry_count} expiries: {101 * 2 * expiry_count:,}")

print("\n" + "="*90)
print("\nSUMMARY:")
print("-" * 90)

total_tokens = 0
for symbol, config in INDEX_CONFIG.items():
    tokens_per_symbol = 101 * 2 * config["expiries_to_subscribe"]
    total_tokens += tokens_per_symbol
    print(f"{symbol:15} x {config['expiries_to_subscribe']:2} expiries = {tokens_per_symbol:5,} tokens")

print("-" * 90)
print(f"{'TOTAL TIER B':15}                      {total_tokens:5,} tokens")
print(f"{'Limit':15}                      {25000:5,} tokens")
print(f"{'Utilization':15}                      {(total_tokens/25000*100):5.1f}%")
print("="*90 + "\n")

print("NOTE: Each expiry has its own ATM calculation based on current LTP.")
print("If LTP changes significantly, ATM shifts and strike range adjusts accordingly.")
