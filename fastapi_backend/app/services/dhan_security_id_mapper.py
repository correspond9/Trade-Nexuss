"""
DhanHQ Security ID Mapper
Maps option tokens to real DhanHQ security IDs from official CSV data
"""

import csv
import io
import requests
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


MCX_LOT_SIZE_OVERRIDES = {
    "CRUDEOIL": 100,
    "NATURALGAS": 1250,
    "COPPER": 2500,
    "GOLD": 1,
    "GOLDM": 100,
    "SILVER": 30,
    "SILVERM": 5,
    "SILVERMIC": 1,
    "ALUMINIUM": 5000,
}

class DhanSecurityIdMapper:
    """Maps option tokens to real DhanHQ security IDs"""
    
    def __init__(self):
        self.security_id_cache: Dict[str, int] = {}
        self.csv_data: Dict[str, Dict] = {}
        self.lot_size_by_underlying: Dict[str, int] = {}
        self.last_updated = None
        self._load_lock = threading.Lock()
        
    async def load_security_ids(self) -> bool:
        """Load security IDs from official DhanHQ CSV"""
        with self._load_lock:
            try:
                if self.last_updated and self.security_id_cache and self.csv_data:
                    return True

                logger.info("Loading DhanHQ security IDs from official CSV...")

                url = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                csv_text = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_text))

                local_security_id_cache: Dict[str, int] = {}
                local_csv_data: Dict[str, Dict] = {}
                local_lot_size_by_underlying: Dict[str, int] = dict(self.lot_size_by_underlying)

                for row in csv_reader:
                    exchange = (row.get('EXCHANGE') or row.get('EXCH_ID') or '').strip()
                    symbol = (row.get('UNDERLYING_SYMBOL') or row.get('SYMBOL') or row.get('SYMBOL_NAME') or '').strip()
                    security_id = (row.get('SECURITY_ID') or '').strip()
                    instrument_type = (row.get('INSTRUMENT') or row.get('INSTRUMENT_TYPE') or '').strip()
                    expiry = (row.get('EXPIRY_DATE') or row.get('SM_EXPIRY_DATE') or '').strip()
                    strike = (row.get('STRIKE_PRICE') or '').strip()
                    option_type = (row.get('OPTION_TYPE') or '').strip()
                    segment = (row.get('SEGMENT') or '').strip()
                    lot_size_raw = row.get('LOT_SIZE') or row.get('MARKET_LOT') or row.get('LOT') or ''

                    try:
                        lot_val = int(float(str(lot_size_raw).strip())) if str(lot_size_raw).strip() else None
                        if lot_val and lot_val > 0 and symbol:
                            key = symbol.strip().upper()
                            if key not in local_lot_size_by_underlying:
                                local_lot_size_by_underlying[key] = lot_val
                    except Exception:
                        pass

                    if 'OPTIDX' not in instrument_type:
                        continue

                    if not all([exchange, symbol, security_id, expiry, strike, option_type]):
                        continue

                    try:
                        security_id_int = int(security_id)
                        strike_float = float(strike)
                    except (ValueError, TypeError):
                        continue

                    try:
                        expiry_formatted = self._format_expiry_date(expiry)
                    except Exception:
                        continue

                    token_key = f"{option_type}_{symbol}_{strike_float}_{expiry_formatted}"
                    local_security_id_cache[token_key] = security_id_int

                    instrument_upper = instrument_type.upper()
                    exchange_upper = exchange.upper()
                    if "OPT" in instrument_upper:
                        if "BSE" in exchange_upper:
                            segment = "BSE_FNO"
                        elif "NSE" in exchange_upper:
                            segment = "NSE_FNO"

                    local_csv_data[token_key] = {
                        'exchange': exchange,
                        'symbol': symbol,
                        'security_id': security_id_int,
                        'expiry': expiry_formatted,
                        'strike': strike_float,
                        'option_type': option_type,
                        'segment': segment
                    }

                self.security_id_cache = local_security_id_cache
                self.csv_data = local_csv_data
                self.lot_size_by_underlying = local_lot_size_by_underlying
                self.last_updated = datetime.now()

                nifty_count = len([k for k in self.security_id_cache.keys() if 'NIFTY' in k])
                banknifty_count = len([k for k in self.security_id_cache.keys() if 'BANKNIFTY' in k])
                sensex_count = len([k for k in self.security_id_cache.keys() if 'SENSEX' in k])

                logger.info(f"✅ Loaded {len(self.security_id_cache):,} security IDs:")
                logger.info(f"   • NIFTY options: {nifty_count:,}")
                logger.info(f"   • BANKNIFTY options: {banknifty_count:,}")
                logger.info(f"   • SENSEX options: {sensex_count:,}")
                if self.lot_size_by_underlying:
                    logger.info(f"   • Lot sizes mapped: {len(self.lot_size_by_underlying)} underlyings")

                return True

            except Exception as e:
                logger.error(f"❌ Failed to load DhanHQ security IDs: {e}")
                return False
    
    def _format_expiry_date(self, expiry: str) -> str:
        """Convert DD-MMM-YYYY to YYYY-MM-DD format"""
        try:
            # Handle various date formats
            if '-' in expiry:
                parts = expiry.split('-')
                if len(parts) == 3:
                    day = parts[0].zfill(2)
                    month = parts[1].upper()
                    year = parts[2]
                    
                    # Convert month abbreviation to number
                    month_map = {
                        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                    }
                    
                    month_num = month_map.get(month[:3])
                    if month_num:
                        return f"{year}-{month_num}-{day}"
        except:
            pass
        
        # Fallback: return as-is
        return expiry
    
    def get_security_id(self, token: str) -> Optional[int]:
        """Get real DhanHQ security ID for a token"""
        return self.security_id_cache.get(token)
    
    def get_option_data(self, token: str) -> Optional[Dict]:
        """Get full option data for a token"""
        return self.csv_data.get(token)
    
    def find_security_id_by_components(self, symbol: str, strike: float, expiry: str, option_type: str) -> Optional[int]:
        """Find security ID by components (fallback method)"""
        token_key = f"{option_type}_{symbol}_{strike}_{expiry}"
        return self.security_id_cache.get(token_key)
    
    def get_lot_size(self, underlying: str) -> Optional[int]:
        """Get lot size for an underlying symbol (stocks, indices, MCX) from CSV"""
        if not underlying:
            return None
        key = underlying.strip().upper()
        if key in MCX_LOT_SIZE_OVERRIDES:
            return MCX_LOT_SIZE_OVERRIDES[key]
        return self.lot_size_by_underlying.get(key)
    
    def get_statistics(self) -> Dict:
        """Get loading statistics"""
        if not self.last_updated:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'total_security_ids': len(self.security_id_cache),
            'last_updated': self.last_updated.isoformat(),
            'symbols': {
                'NIFTY': len([k for k in self.security_id_cache.keys() if 'NIFTY' in k]),
                'BANKNIFTY': len([k for k in self.security_id_cache.keys() if 'BANKNIFTY' in k]),
                'SENSEX': len([k for k in self.security_id_cache.keys() if 'SENSEX' in k]),
            }
        }

# Global instance
dhan_security_mapper = DhanSecurityIdMapper()
