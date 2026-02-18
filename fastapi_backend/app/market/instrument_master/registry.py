"""
Enhanced Instrument Registry for two-tier subscription system.
Indexes instruments by symbol, expiry, segment, and F&O eligibility.
Provides fast lookups and strike generation logic.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import threading

MASTER_PATH = Path(__file__).parent / "api-scrip-master-detailed.csv"

class InstrumentRegistry:
    """Indexed instrument master for fast lookups and strike generation"""
    
    def __init__(self):
        self.instruments = []  # All 289k+ records
        self.by_symbol = defaultdict(list)  # symbol -> [records]
        self.by_symbol_expiry = defaultdict(list)  # (symbol, expiry) -> [records]
        self.by_underlying = defaultdict(list)  # underlying_symbol -> [records]
        self.by_underlying_expiry = defaultdict(list)  # (underlying_symbol, expiry) -> [records]
        self.by_segment = defaultdict(list)  # segment -> [records]
        self.f_o_stocks = set()  # F&O-eligible stock symbols
        self.strike_steps = {}  # symbol -> strike_step (float)
        self.mcx_nearest_cache = {}  # symbol -> nearest MCX future cache
        self.loaded = False
        self._load_lock = threading.Lock()
        
    def load(self):
        """Load and index the instrument master CSV"""
        if self.loaded:
            return

        with self._load_lock:
            if self.loaded:
                return

            with open(MASTER_PATH, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    self.instruments.append(row)

                    symbol = row.get("SYMBOL_NAME", "").strip()
                    expiry = row.get("SM_EXPIRY_DATE", "").strip()
                    segment = row.get("SEGMENT", "").strip()
                    instrument_type = row.get("INSTRUMENT_TYPE", "").strip()
                    strike_price = row.get("STRIKE_PRICE", "").strip()
                    underlying = row.get("UNDERLYING_SYMBOL", "").strip().upper()

                    # Index by symbol
                    if symbol:
                        self.by_symbol[symbol].append(row)

                    # Index by (symbol, expiry)
                    if symbol and expiry:
                        self.by_symbol_expiry[(symbol, expiry)].append(row)

                    # Index by underlying symbol
                    if underlying:
                        self.by_underlying[underlying].append(row)
                        if expiry:
                            self.by_underlying_expiry[(underlying, expiry)].append(row)

                    # Index by segment
                    if segment:
                        self.by_segment[segment].append(row)

                    # Track F&O stocks
                    if instrument_type in ("FUTSTK", "OPTSTK"):
                        base_symbol = row.get("UNDERLYING_SYMBOL", symbol).strip()
                        self.f_o_stocks.add(base_symbol)

                    # Cache strike steps (from first occurrence of each symbol)
                    if symbol and strike_price:
                        try:
                            step = float(strike_price)
                            if step > 0 and symbol not in self.strike_steps:
                                self.strike_steps[symbol] = step
                        except (ValueError, TypeError):
                            pass

            self.loaded = True
            print(f"[OK] Instrument Registry loaded: {len(self.instruments)} records")
            print(f"[OK] F&O eligible stocks: {len(self.f_o_stocks)}")
            print(f"[OK] Unique symbols: {len(self.by_symbol)}")

    def ensure_loaded(self) -> None:
        """Load the instrument master lazily when needed."""
        if not self.loaded:
            self.load()
    
    def get_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all instruments for a symbol across all expiries"""
        self.ensure_loaded()
        return self.by_symbol.get(symbol, [])
    
    def get_by_symbol_expiry(self, symbol: str, expiry: str) -> List[Dict]:
        """Get instruments for a specific symbol+expiry"""
        self.ensure_loaded()
        return self.by_symbol_expiry.get((symbol, expiry), [])
    
    def get_strike_step(self, symbol: str) -> float:
        """Get the strike step for a symbol (or default to 1.0)"""
        self.ensure_loaded()
        if not symbol:
            return 1.0
        step = self.strike_steps.get(symbol)
        if step and step > 0:
            return step

        # Fallback: derive strike step from underlying option strikes
        underlying = symbol.upper()
        strikes = []
        for row in self.by_underlying.get(underlying, [])[:500]:
            raw = row.get("STRIKE_PRICE", "")
            try:
                val = float(raw)
                if val > 0:
                    strikes.append(val)
            except (TypeError, ValueError):
                continue

        strikes = sorted(set(strikes))
        if len(strikes) >= 2:
            diffs = [b - a for a, b in zip(strikes, strikes[1:]) if b - a > 0]
            if diffs:
                step = min(diffs)
                self.strike_steps[symbol] = step
                return step

        return 1.0
    
    def get_expiries_for_symbol(self, symbol: str) -> List[str]:
        """Get all unique expiries for a symbol"""
        self.ensure_loaded()
        expiries = set()
        for record in self.by_symbol.get(symbol, []):
            expiry = record.get("SM_EXPIRY_DATE", "").strip()
            if expiry and expiry != "":
                expiries.add(expiry)
        return sorted(list(expiries))

    def get_expiries_for_underlying(self, symbol: str) -> List[str]:
        """Get all unique expiries for an underlying symbol (options/futures)."""
        self.ensure_loaded()
        if not symbol:
            return []
        expiry_map = {}
        for record in self.by_underlying.get(symbol.upper(), []):
            expiry = (record.get("SM_EXPIRY_DATE", "") or "").strip()
            if not expiry:
                continue
            parsed = self._normalize_expiry(expiry)
            if parsed:
                expiry_map[expiry] = parsed
        return [e for e, _ in sorted(expiry_map.items(), key=lambda item: item[1])]
    
    def is_f_o_eligible(self, symbol: str) -> bool:
        """Check if stock has F&O contracts"""
        self.ensure_loaded()
        return symbol in self.f_o_stocks
    
    def get_equity_stocks_nse(self, limit: int = 2000) -> List[Dict]:
        """Get top N NSE equity stocks (SEGMENT='E')"""
        self.ensure_loaded()
        nse_equity = [
            r for r in self.by_segment.get("E", [])
            if r.get("EXCH_ID", "").strip() == "NSE"
        ]
        return nse_equity[:limit]
    
    def get_option_chain(
        self, 
        symbol: str, 
        expiry: str, 
        underlying_ltp: float
    ) -> Tuple[List[float], float]:
        """
        Generate option chain strikes based on ATM calculation.
        
        Returns: (strikes_list, atm_strike)
        where strikes_list is the ATM + symmetric strikes around it
        """
        self.ensure_loaded()
        strike_step = self.get_strike_step(symbol)
        
        # Calculate ATM
        atm = round(underlying_ltp / strike_step) * strike_step
        
        # Get symbol type to determine strike count
        records = self.get_by_symbol_expiry(symbol, expiry)
        if not records:
            # Try underlying symbol lookups (options use UNDERLYING_SYMBOL)
            records = self.by_underlying_expiry.get((symbol.upper(), expiry), [])

        if not records:
            # Try normalized expiry match against underlying symbol
            target_expiry = self._normalize_expiry(expiry)
            if target_expiry:
                for row in self.by_underlying.get(symbol.upper(), []):
                    row_expiry = self._normalize_expiry(row.get("SM_EXPIRY_DATE", ""))
                    if row_expiry and row_expiry == target_expiry:
                        records.append(row)
                if records:
                    # Cache for faster access next time
                    self.by_underlying_expiry[(symbol.upper(), expiry)] = records

        if not records:
            return ([], atm)
        
        instrument_type = records[0].get("INSTRUMENT_TYPE", "").strip()
        
        # Strike window based on type
        if symbol in ("NIFTY", "NIFTY50", "BANKNIFTY", "SENSEX"):  # Index options
            if symbol == "SENSEX":
                below = 50
                above = 50
            else:  # NIFTY, BANKNIFTY
                below = 50
                above = 50
        elif symbol in ("FINNIFTY", "MIDCPNIFTY", "BANKEX"):  # Mid-cap indices
            below = 25
            above = 24  # 50 total
        elif symbol in ("CRUDEOIL", "NATURALGAS"):  # MCX options
            below = 50
            above = 50
        else:  # Stock options
            below = 12
            above = 12
        
        # Generate strikes
        strikes = []
        for i in range(-below, above + 1):
            strike = atm + (i * strike_step)
            if strike > 0:
                strikes.append(strike)
        
        return (strikes, atm)

    def _normalize_expiry(self, expiry: Optional[str]) -> Optional[datetime.date]:
        if not expiry:
            return None
        text = expiry.strip().upper()
        for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%b%y", "%d%B%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None
    
    def get_nearest_mcx_future(self, symbol: str) -> Optional[Dict]:
        """
        Get the nearest-month MCX futures contract for a symbol.
        Automatically selects the contract with the closest expiry date.
        
        Args:
            symbol: MCX symbol (e.g., 'CRUDEOIL', 'NATURALGAS')
        
        Returns:
            Instrument record dict with security_id, expiry, exchange, etc.
        """
        if not symbol:
            return None
        
        symbol_upper = symbol.upper()
        today = datetime.now().date()

        # Return cached nearest-month contract if still valid
        cached = self.mcx_nearest_cache.get(symbol_upper)
        if cached:
            cached_expiry = cached.get("expiry_date")
            if cached_expiry and cached_expiry >= today:
                return {
                    "security_id": cached["security_id"],
                    "exchange": cached["exchange"],
                    "symbol": symbol_upper,
                    "expiry": cached["expiry"],
                }
        
        # Find all futures for this symbol (OPTION_TYPE='XX' or empty)
        futures = []
        for record in self.by_symbol.get(symbol_upper, []):
            # Check if it's a future (not option)
            option_type = (record.get("OPTION_TYPE") or "").strip().upper()
            if option_type and option_type not in ("XX", ""):
                continue
            
            # Check if it's MCX exchange
            exchange = (record.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            
            # Get expiry date
            expiry_str = record.get("SM_EXPIRY_DATE", "").strip()
            if not expiry_str:
                continue
            
            expiry_date = self._normalize_expiry(expiry_str)
            if not expiry_date or expiry_date < today:
                continue  # Skip expired contracts
            
            security_id = record.get("SECURITY_ID", "").strip()
            if not security_id:
                continue
            
            futures.append({
                "security_id": security_id,
                "expiry": expiry_str,
                "expiry_date": expiry_date,
                "symbol": symbol_upper,
                "exchange": 5,  # MCX exchange code
                "record": record
            })
        
        if not futures:
            return None
        
        # Sort by expiry date and return the nearest
        futures.sort(key=lambda x: x["expiry_date"])
        nearest = futures[0]

        # Cache and log once per refresh
        self.mcx_nearest_cache[symbol_upper] = nearest
        print(f"[MCX-AUTO] {symbol_upper}: Selected nearest-month contract {nearest['security_id']} (exp: {nearest['expiry']})")

        return {
            "security_id": nearest["security_id"],
            "exchange": nearest["exchange"],
            "symbol": symbol_upper,
            "expiry": nearest["expiry"],
        }


# Global registry instance
REGISTRY = InstrumentRegistry()

def load_instruments():
    """Initialize global registry"""
    REGISTRY.load()
    return REGISTRY
