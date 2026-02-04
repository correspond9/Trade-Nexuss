"""
ATM Calculation Engine.
Computes ATM strikes and generates option chains based on LTP.
Deterministic, cached, only recalculated on specific triggers.
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from app.market.instrument_master.registry import REGISTRY

class ATMEngine:
    """
    ATM calculation with caching.
    Recalculates ONLY when:
    - Underlying moves >= 1 strike step
    - Expiry changes
    - Option chain UI reopened
    """
    
    def __init__(self):
        self.cache = {}  # {symbol: {expiry: {atm, strikes, last_update, underlying_ltp}}}
        self.lock = threading.RLock()
        self.last_recalc = {}  # {symbol: timestamp}
    
    def should_recalculate(self, symbol: str, current_ltp: float) -> bool:
        """
        Check if ATM should be recalculated.
        Returns True if:
        1. No cached ATM exists
        2. Underlying moved >= 1 strike step since last calculation
        """
        with self.lock:
            if symbol not in self.cache:
                return True
            
            cache_data = self.cache.get(symbol, {})
            if not cache_data or "underlying_ltp" not in cache_data:
                return True
            
            last_ltp = cache_data.get("underlying_ltp", 0)
            strike_step = REGISTRY.get_strike_step(symbol)
            
            # Did price move by at least 1 strike step?
            ltp_diff = abs(current_ltp - last_ltp)
            if ltp_diff >= strike_step:
                return True
            
            return False
    
    def calculate_atm(self, symbol: str, underlying_ltp: float) -> float:
        """
        Calculate ATM strike deterministically.
        ATM = round(LTP / Strike_Step) * Strike_Step
        """
        strike_step = REGISTRY.get_strike_step(symbol)
        atm = round(underlying_ltp / strike_step) * strike_step
        return atm
    
    def generate_chain(
        self,
        symbol: str,
        expiry: str,
        underlying_ltp: float,
        force_recalc: bool = False
    ) -> Dict:
        """
        Generate option chain for symbol+expiry.
        
        Returns:
        {
            "symbol": "RELIANCE",
            "expiry": "26FEB2026",
            "underlying_ltp": 2641.5,
            "atm_strike": 2640.0,
            "strike_step": 5.0,
            "strikes": [2600, 2625, 2640, 2675, 2700, ...],  # All strikes
            "strikes_ce_pe": {  # For UI rendering
                "2600": {"CE": "RELIANCE_26FEB_2600CE", "PE": "RELIANCE_26FEB_2600PE"},
                ...
            },
            "cached_at": "2026-02-03 10:15:30",
            "cache_ttl_seconds": 300
        }
        """
        with self.lock:
            # Check if recalculation needed
            needs_calc = force_recalc or self.should_recalculate(symbol, underlying_ltp)
            
            if not needs_calc and symbol in self.cache:
                cache = self.cache[symbol]
                if expiry in cache:
                    return cache[expiry]
            
            # Generate fresh
            atm = self.calculate_atm(symbol, underlying_ltp)
            strikes, _ = REGISTRY.get_option_chain(symbol, expiry, underlying_ltp)
            strike_step = REGISTRY.get_strike_step(symbol)
            
            # Build strikes_ce_pe map for UI
            strikes_ce_pe = {}
            for strike in strikes:
                token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                strikes_ce_pe[str(strike)] = {
                    "CE": token_ce,
                    "PE": token_pe
                }
            
            result = {
                "symbol": symbol,
                "expiry": expiry,
                "underlying_ltp": underlying_ltp,
                "atm_strike": atm,
                "strike_step": strike_step,
                "strikes": strikes,
                "strikes_ce_pe": strikes_ce_pe,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_ttl_seconds": 300  # 5 min cache before recalc on demand
            }
            
            # Cache it
            if symbol not in self.cache:
                self.cache[symbol] = {}
            
            self.cache[symbol][expiry] = result
            self.cache[symbol]["underlying_ltp"] = underlying_ltp
            self.last_recalc[symbol] = datetime.utcnow()
            
            return result
    
    def invalidate_expiry(self, symbol: str, expiry: str):
        """Force recalculation for a specific symbol+expiry (e.g., on expiry rollover)"""
        with self.lock:
            if symbol in self.cache and expiry in self.cache[symbol]:
                del self.cache[symbol][expiry]
    
    def invalidate_symbol(self, symbol: str):
        """Force recalculation for all expiries of a symbol"""
        with self.lock:
            if symbol in self.cache:
                del self.cache[symbol]
    
    def get_cached_chain(self, symbol: str, expiry: str) -> Optional[Dict]:
        """Get cached chain without recalculation"""
        with self.lock:
            if symbol in self.cache and expiry in self.cache[symbol]:
                return self.cache[symbol][expiry]
            return None


# Global ATM engine instance
ATM_ENGINE = ATMEngine()

def get_atm_engine() -> ATMEngine:
    """Get global ATM engine"""
    return ATM_ENGINE
