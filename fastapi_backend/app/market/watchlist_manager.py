"""
Watchlist module for Tier A (on-demand) subscriptions.
Users add stocks/expiries, system subscribes to option chains on demand.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional
from app.storage.db import SessionLocal
from app.storage.models import Watchlist
from app.market.subscription_manager import get_subscription_manager
from app.market.atm_engine import get_atm_engine
from app.market.instrument_master.registry import REGISTRY

class WatchlistManager:
    """
    User watchlists for on-demand (Tier A) subscriptions.
    
    Lifecycle:
    1. User searches for stock
    2. User adds to watchlist (symbol + expiry)
    3. System generates option chain (ATM-based strikes)
    4. System subscribes to all strikes (CE + PE)
    5. At EOD 3:30 PM: unsubscribe all Tier A + clear watchlist
    """
    
    def __init__(self):
        self.db = SessionLocal()
        self.lock = threading.RLock()
        self.sub_mgr = get_subscription_manager()
        self.atm_engine = get_atm_engine()
    
    def add_to_watchlist(
        self,
        user_id: int,
        symbol: str,
        expiry: str,
        instrument_type: str = "STOCK_OPTION",
        underlying_ltp: Optional[float] = None
    ) -> Dict:
        """
        Add stock/option to user watchlist and subscribe to chains.
        
        Returns:
        {
            "success": bool,
            "message": str,
            "option_chain": {...} if successful,  # For UI rendering
            "error": str if failed
        }
        """
        with self.lock:
            try:
                # Check if already in watchlist
                existing = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                    Watchlist.symbol == symbol,
                    Watchlist.expiry_date == expiry
                ).first()
                
                if existing:
                    return {
                        "success": False,
                        "message": f"{symbol} already in watchlist for {expiry}",
                        "error": "DUPLICATE"
                    }
                
                # Enforce Tier-A/Tier-B-only universe
                allowed_indices = {"NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"}
                equities = set()
                try:
                    for r in REGISTRY.get_equity_stocks_nse(limit=2000):
                        sym = (r.get("UNDERLYING_SYMBOL") or r.get("SYMBOL") or "").strip().upper()
                        if sym:
                            equities.add(sym)
                except Exception:
                    pass
                allowed_symbols = set(REGISTRY.f_o_stocks) | allowed_indices | equities
                if symbol.upper() not in allowed_symbols:
                    return {
                        "success": False,
                        "message": f"{symbol} not allowed in watchlist",
                        "error": "SYMBOL_NOT_ALLOWED"
                    }
                
                # Allow only EQUITY, STOCK_OPTION, INDEX_OPTION
                if instrument_type not in ("EQUITY", "STOCK_OPTION", "INDEX_OPTION"):
                    return {
                        "success": False,
                        "message": f"instrument_type {instrument_type} not allowed",
                        "error": "INSTRUMENT_TYPE_NOT_ALLOWED"
                    }
                
                # Get added_order (for LRU eviction)
                max_order = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id
                ).count()
                added_order = max_order + 1
                
                # Add to watchlist
                watchlist_entry = Watchlist(
                    user_id=user_id,
                    symbol=symbol,
                    expiry_date=expiry,
                    instrument_type=instrument_type,
                    added_order=added_order
                )
                self.db.add(watchlist_entry)
                self.db.commit()
                
                # Generate and subscribe option chain
                if instrument_type in ("STOCK_OPTION", "INDEX_OPTION"):
                    if underlying_ltp is None:
                        return {
                            "success": False,
                            "message": "underlying_ltp required for option chains",
                            "error": "MISSING_LTP"
                        }
                    
                    # Generate chain
                    chain = self.atm_engine.generate_chain(
                        symbol=symbol,
                        expiry=expiry,
                        underlying_ltp=underlying_ltp,
                        force_recalc=True
                    )
                    
                    # Subscribe to all strikes (CE + PE)
                    strikes = chain["strikes"]
                    failed_strikes = []
                    
                    for strike in strikes:
                        # CE
                        token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                        success, msg, ws_id = self.sub_mgr.subscribe(
                            token=token_ce,
                            symbol=symbol,
                            expiry=expiry,
                            strike=strike,
                            option_type="CE",
                            tier="TIER_A"
                        )
                        if not success:
                            failed_strikes.append(token_ce)
                        
                        # PE
                        token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                        success, msg, ws_id = self.sub_mgr.subscribe(
                            token=token_pe,
                            symbol=symbol,
                            expiry=expiry,
                            strike=strike,
                            option_type="PE",
                            tier="TIER_A"
                        )
                        if not success:
                            failed_strikes.append(token_pe)
                    
                    if failed_strikes:
                        return {
                            "success": False,
                            "message": f"Failed to subscribe {len(failed_strikes)} strikes",
                            "error": "SUBSCRIPTION_FAILED",
                            "failed_count": len(failed_strikes)
                        }
                    
                    return {
                        "success": True,
                        "message": f"Added {symbol} to watchlist ({expiry})",
                        "option_chain": chain,
                        "strikes_subscribed": len(strikes) * 2  # CE + PE
                    }
                
                else:
                    # EQUITY on-demand subscription (single token)
                    token_eq = f"EQUITY_{symbol.upper()}"
                    success, msg, ws_id = self.sub_mgr.subscribe(
                        token=token_eq,
                        symbol=symbol,
                        expiry=None,
                        strike=None,
                        option_type=None,
                        tier="TIER_A"
                    )
                    if not success:
                        return {
                            "success": False,
                            "message": f"Failed to subscribe equity {symbol}",
                            "error": "SUBSCRIPTION_FAILED"
                        }
                    return {
                        "success": True,
                        "message": f"Added {symbol} equity to watchlist",
                        "instrument_type": "EQUITY",
                        "token": token_eq,
                        "ws_id": ws_id
                    }
            
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error adding to watchlist: {str(e)}",
                    "error": "EXCEPTION"
                }
    
    def remove_from_watchlist(self, user_id: int, symbol: str, expiry: str) -> Dict:
        """Remove from watchlist and unsubscribe all related chains"""
        with self.lock:
            try:
                # Find watchlist entry
                entry = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                    Watchlist.symbol == symbol,
                    Watchlist.expiry_date == expiry
                ).first()
                
                if not entry:
                    return {
                        "success": False,
                        "message": f"{symbol} not in watchlist"
                    }
                
                # Unsubscribe all related chains (if option)
                if entry.instrument_type in ("STOCK_OPTION", "INDEX_OPTION"):
                    # Get all strikes for this symbol+expiry
                    chain = self.atm_engine.get_cached_chain(symbol, expiry)
                    if chain:
                        strikes = chain["strikes"]
                        for strike in strikes:
                            token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                            token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                            self.sub_mgr.unsubscribe(token_ce, reason="USER_REMOVAL")
                            self.sub_mgr.unsubscribe(token_pe, reason="USER_REMOVAL")
                
                # Delete from watchlist
                self.db.delete(entry)
                self.db.commit()
                
                return {
                    "success": True,
                    "message": f"Removed {symbol} from watchlist"
                }
            
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error removing from watchlist: {str(e)}"
                }
    
    def get_user_watchlist(self, user_id: int) -> List[Dict]:
        """Get user's watchlist"""
        with self.lock:
            entries = self.db.query(Watchlist).filter(
                Watchlist.user_id == user_id
            ).order_by(Watchlist.added_at.desc()).all()
            
            return [
                {
                    "id": e.id,
                    "symbol": e.symbol,
                    "expiry_date": e.expiry_date,
                    "instrument_type": e.instrument_type,
                    "added_at": e.added_at.isoformat(),
                    "added_order": e.added_order
                }
                for e in entries
            ]
    
    def clear_all_user_watchlist(self, user_id: int) -> Dict:
        """Clear entire user watchlist (used at EOD)"""
        with self.lock:
            try:
                entries = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id
                ).all()
                
                count = 0
                for entry in entries:
                    # Skip clearing if there is an open position for this symbol+expiry
                    try:
                        from app.storage.models import MockPosition
                        from app.rms.span_margin_calculator import _parse_symbol as parse_fno_symbol
                        from app.rms.mcx_margin_calculator import _parse_symbol as parse_mcx_symbol
                        pos_query = self.db.query(MockPosition).filter(
                            MockPosition.user_id == user_id,
                            MockPosition.quantity != 0,
                            MockPosition.status == "OPEN"
                        ).all()
                        has_open = False
                        for pos in pos_query:
                            sym = (pos.symbol or "").strip()
                            meta = parse_fno_symbol(sym)
                            if not meta or not meta.get("underlying"):
                                meta = parse_mcx_symbol(sym)
                            underlying = (meta.get("underlying") or "").upper()
                            expiry = meta.get("expiry")
                            if underlying == (entry.symbol or "").upper() and (expiry == entry.expiry_date):
                                has_open = True
                                break
                        if has_open:
                            continue
                    except Exception:
                        pass
                    
                    # Unsubscribe related chains
                    if entry.instrument_type in ("STOCK_OPTION", "INDEX_OPTION"):
                        chain = self.atm_engine.get_cached_chain(
                            entry.symbol,
                            entry.expiry_date
                        )
                        if chain:
                            strikes = chain["strikes"]
                            for strike in strikes:
                                token_ce = f"{entry.symbol}_{entry.expiry_date}_{strike:.0f}CE"
                                token_pe = f"{entry.symbol}_{entry.expiry_date}_{strike:.0f}PE"
                                self.sub_mgr.unsubscribe(token_ce, reason="EOD_CLEANUP")
                                self.sub_mgr.unsubscribe(token_pe, reason="EOD_CLEANUP")
                    
                    self.db.delete(entry)
                    count += 1
                
                self.db.commit()
                
                return {
                    "success": True,
                    "cleared_count": count
                }
            
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error clearing watchlist: {str(e)}"
                }


# Global watchlist manager
WATCHLIST_MGR = WatchlistManager()

def get_watchlist_manager() -> WatchlistManager:
    """Get global watchlist manager"""
    return WATCHLIST_MGR
