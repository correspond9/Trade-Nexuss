"""
Watchlist module for Tier A (on-demand) subscriptions.
Users add stocks/expiries, system subscribes to option chains on demand.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from app.storage.db import SessionLocal
from app.storage.models import Watchlist
from app.market.subscription_manager import get_subscription_manager
from app.market.atm_engine import get_atm_engine
from app.market.instrument_master.registry import REGISTRY
from app.market.instrument_master.tier_a_equity_symbols import get_tier_a_equity_symbols

EQUITY_EXPIRY_MARKER = "EQ"

class WatchlistManager:
    """
    User watchlists for on-demand (Tier A) subscriptions.
    
    Lifecycle:
    1. User searches for stock
    2. User adds to watchlist (symbol + expiry)
    3. System generates option chain (ATM-based strikes)
    4. System subscribes to all strikes (CE + PE)
    5. At EOD 4:00 PM: unsubscribe Tier A + clear watchlists (except protected open-position symbols)
    """
    
    def __init__(self):
        self.db = SessionLocal()
        self.lock = threading.RLock()
        self.sub_mgr = get_subscription_manager()
        self.atm_engine = get_atm_engine()

    def _normalize_expiry(self, expiry: Optional[str], instrument_type: Optional[str]) -> str:
        normalized_type = (instrument_type or "").upper()
        expiry_text = (expiry or "").strip()
        if normalized_type == "EQUITY":
            return expiry_text or EQUITY_EXPIRY_MARKER
        return expiry_text

    def _get_live_ltp(self, symbol: Optional[str]) -> Optional[float]:
        try:
            from app.market.live_prices import get_price
            value = get_price((symbol or "").upper())
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
    
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
                instrument_type = (instrument_type or "").upper()
                symbol = (symbol or "").strip().upper()
                expiry = self._normalize_expiry(expiry, instrument_type)

                # Check if already in watchlist
                existing = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                    Watchlist.symbol == symbol,
                    Watchlist.expiry_date == expiry
                ).first()
                
                if existing:
                    existing_type = (existing.instrument_type or instrument_type or "").upper()
                    if existing_type in ("STOCK_OPTION", "INDEX_OPTION"):
                        ltp_value = underlying_ltp
                        if ltp_value is None:
                            try:
                                from app.market.live_prices import get_price
                                ltp_value = get_price((symbol or "").upper())
                            except Exception:
                                ltp_value = None

                        if ltp_value is not None:
                            chain = self.atm_engine.generate_chain(
                                symbol=symbol,
                                expiry=expiry,
                                underlying_ltp=ltp_value,
                                force_recalc=True
                            )
                            strikes = chain.get("strikes", [])
                            subscribed = 0
                            for strike in strikes:
                                token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                                success_ce, _msg_ce, _ws_id_ce = self.sub_mgr.subscribe(
                                    token=token_ce,
                                    symbol=symbol,
                                    expiry=expiry,
                                    strike=strike,
                                    option_type="CE",
                                    tier="TIER_A"
                                )
                                if success_ce:
                                    subscribed += 1

                                token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                                success_pe, _msg_pe, _ws_id_pe = self.sub_mgr.subscribe(
                                    token=token_pe,
                                    symbol=symbol,
                                    expiry=expiry,
                                    strike=strike,
                                    option_type="PE",
                                    tier="TIER_A"
                                )
                                if success_pe:
                                    subscribed += 1

                            return {
                                "success": True,
                                "message": f"{symbol} already in watchlist for {expiry}; ensured subscriptions",
                                "error": "DUPLICATE",
                                "strikes_subscribed": subscribed
                            }

                    if existing_type == "EQUITY":
                        token_eq = f"EQUITY_{symbol.upper()}"
                        self.sub_mgr.subscribe(
                            token=token_eq,
                            symbol=symbol,
                            expiry=None,
                            strike=None,
                            option_type=None,
                            tier="TIER_A"
                        )
                        return {
                            "success": True,
                            "message": f"{symbol} already in watchlist; ensured equity subscription",
                            "error": "DUPLICATE",
                            "token": token_eq
                        }

                    return {
                        "success": False,
                        "message": f"{symbol} already in watchlist for {expiry}",
                        "error": "DUPLICATE"
                    }
                
                # Enforce Tier-A/Tier-B-only universe
                if not REGISTRY.loaded:
                    REGISTRY.load()
                allowed_indices = {"NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"}
                allowed_equities = set()
                try:
                    allowed_equities = get_tier_a_equity_symbols()
                except Exception:
                    allowed_equities = set()
                allowed_symbols = set(REGISTRY.f_o_stocks) | allowed_indices | allowed_equities
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
                        "ws_id": ws_id,
                        "ltp": self._get_live_ltp(symbol),
                    }
            
            except Exception as e:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                return {
                    "success": False,
                    "message": f"Error adding to watchlist: {str(e)}",
                    "error": "EXCEPTION"
                }
    
    def remove_from_watchlist(self, user_id: int, symbol: str, expiry: str) -> Dict:
        """Remove from watchlist and unsubscribe all related chains"""
        with self.lock:
            try:
                symbol = (symbol or "").strip().upper()
                expiry_text = (expiry or "").strip()

                # Find watchlist entry
                query = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                    Watchlist.symbol == symbol,
                )

                if expiry_text:
                    entry = query.filter(Watchlist.expiry_date == expiry_text).first()
                else:
                    entry = query.first()

                if not entry and expiry_text != EQUITY_EXPIRY_MARKER:
                    entry = query.filter(Watchlist.expiry_date == EQUITY_EXPIRY_MARKER).first()
                
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
                try:
                    self.db.rollback()
                except Exception:
                    pass
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

            rows = []
            for e in entries:
                rows.append(
                    {
                        "id": e.id,
                        "symbol": e.symbol,
                        "expiry_date": None if (e.instrument_type or "").upper() == "EQUITY" and e.expiry_date == EQUITY_EXPIRY_MARKER else e.expiry_date,
                        "instrument_type": e.instrument_type,
                        "added_at": e.added_at.isoformat(),
                        "added_order": e.added_order,
                        "ltp": self._get_live_ltp(e.symbol),
                    }
                )
            return rows
    
    def clear_all_user_watchlist(self, user_id: int) -> Dict:
        """Clear entire user watchlist (used at EOD)"""
        return self.clear_all_user_watchlist_with_protection(user_id=user_id, protected_keys=None)

    @staticmethod
    def _normalize_eod_key(symbol: Optional[str], expiry: Optional[str], instrument_type: Optional[str]) -> Tuple[str, Optional[str]]:
        normalized_symbol = (symbol or "").strip().upper()
        normalized_type = (instrument_type or "").upper()
        if normalized_type == "EQUITY":
            return normalized_symbol, None
        normalized_expiry = (expiry or "").strip().upper() or None
        return normalized_symbol, normalized_expiry

    def clear_all_user_watchlist_with_protection(
        self,
        user_id: int,
        protected_keys: Optional[Set[Tuple[str, Optional[str]]]]
    ) -> Dict:
        """Clear user watchlist while preserving globally protected symbol+expiry keys."""
        with self.lock:
            try:
                entries = self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id
                ).all()
                
                count = 0
                skipped = 0
                protected = protected_keys or set()
                for entry in entries:
                    entry_key = self._normalize_eod_key(
                        entry.symbol,
                        entry.expiry_date,
                        entry.instrument_type
                    )
                    if entry_key in protected:
                        skipped += 1
                        continue
                    
                    self.db.delete(entry)
                    count += 1
                
                self.db.commit()
                
                return {
                    "success": True,
                    "cleared_count": count,
                    "skipped_count": skipped
                }
            
            except Exception as e:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                return {
                    "success": False,
                    "message": f"Error clearing watchlist: {str(e)}"
                }

    def clear_all_watchlists(self, protected_keys: Optional[Set[Tuple[str, Optional[str]]]] = None) -> Dict:
        """Clear all users' watchlists while preserving globally protected symbol+expiry keys."""
        with self.lock:
            try:
                entries = self.db.query(Watchlist).all()

                count = 0
                skipped = 0
                protected = protected_keys or set()

                for entry in entries:
                    entry_key = self._normalize_eod_key(
                        entry.symbol,
                        entry.expiry_date,
                        entry.instrument_type
                    )
                    if entry_key in protected:
                        skipped += 1
                        continue

                    self.db.delete(entry)
                    count += 1

                self.db.commit()
                return {
                    "success": True,
                    "cleared_count": count,
                    "skipped_count": skipped
                }
            except Exception as e:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                return {
                    "success": False,
                    "message": f"Error clearing all watchlists: {str(e)}"
                }


# Global watchlist manager
WATCHLIST_MGR = WatchlistManager()

def get_watchlist_manager() -> WatchlistManager:
    """Get global watchlist manager"""
    return WATCHLIST_MGR
