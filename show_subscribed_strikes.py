"""
Show the strike price ranges subscribed from WebSocket for Tier B.
Uses ATM Engine to calculate ATM and generate the 101-strike ranges.
"""
import sys
sys.path.insert(0, 'd:\\4.PROJECTS\\Broking_Terminal_V2\\data_server_backend\\fastapi_backend')

from app.market.instrument_master.loader import MASTER
from app.market.atm_engine import ATM_ENGINE
from app.market.live_prices import get_prices
from app.market.instrument_master.registry import REGISTRY

def show_tier_b_strikes():
    # Load instrument master first
    MASTER.load()
    """Show the strike ranges subscribed from WebSocket for each index"""
    
    # Get current prices
    all_prices = get_prices()
    
    indices = {
        "NIFTY": 16,
        "BANKNIFTY": 7,
        "SENSEX": 7,
    }
    
    print("\n" + "="*80)
    print("TIER B WEBSOCKET SUBSCRIPTIONS - STRIKE RANGES (ATM ±50)")
    print("="*80)
    
    for symbol, num_expiries in indices.items():
        print(f"\n{symbol}:")
        print("-" * 80)
        
        # Get expiries and LTP
        expiries = REGISTRY.get_expiries_for_underlying(symbol) or REGISTRY.get_expiries_for_symbol(symbol)
        expiries = expiries[:num_expiries]
        underlying_ltp = all_prices.get(symbol) or 25000
        
        print(f"  Underlying LTP: {underlying_ltp}")
        print(f"  Expiries subscribed: {len(expiries)}")
        print()
        
        for expiry in expiries:
            # Generate full chain (101 strikes = ATM ±50)
            option_chain = ATM_ENGINE.generate_chain(symbol, expiry, underlying_ltp)
            strikes = option_chain["strikes"]
            
            print(f"    {expiry}:")
            print(f"      ATM: {option_chain['atm_strike']}")
            print(f"      Min strike: {min(strikes)}")
            print(f"      Max strike: {max(strikes)}")
            print(f"      Total strikes: {len(strikes)}")
            print(f"      Range: {min(strikes)} → {max(strikes)}")
            print()
    
    print("="*80)
    print("\nNOTE: Each strike has both CE and PE subscribed (2x multiplier)")
    print("Example: NIFTY 02-10 with 101 strikes = 202 tokens (101 CE + 101 PE)")
    print("="*80 + "\n")

if __name__ == "__main__":
    show_tier_b_strikes()
