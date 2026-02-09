"""Canonical security-id mappings for core instruments.

Provides reusable helpers so that both subscription bookkeeping and the
WebSocket feed can map between user-friendly symbols and the security IDs
required by DhanHQ. Keeping this in a single module avoids ad-hoc hardcoding
scattered across the codebase.
"""
from __future__ import annotations

from typing import Dict, Optional

# Exchange codes understood by DhanHQ feed
EXCHANGE_CODE_IDX = 0
EXCHANGE_CODE_NSE = 1
EXCHANGE_CODE_NSE_FNO = 2
EXCHANGE_CODE_BSE = 4
EXCHANGE_CODE_MCX = 5

# Canonical index instruments we always want on feed
_DEFAULT_INDEX_SECURITY_IDS: Dict[str, Dict[str, object]] = {
    "NIFTY": {"security_id": "13", "exchange": EXCHANGE_CODE_IDX},
    "NIFTY50": {"security_id": "13", "exchange": EXCHANGE_CODE_IDX},
    "BANKNIFTY": {"security_id": "25", "exchange": EXCHANGE_CODE_IDX},
    "SENSEX": {"security_id": "51", "exchange": EXCHANGE_CODE_IDX},
}

# Always-on equities disabled to enforce Tier-A/Tier-B-only policy
_DEFAULT_EQUITY_SECURITY_IDS: Dict[str, Dict[str, object]] = {}

# MCX fallback IDs (used only if instrument master auto-resolution fails)
# Updated to current month (Feb 2026) - Security ID from instrument master
_MCX_FALLBACK_SECURITY_IDS: Dict[str, Dict[str, object]] = {
    "CRUDEOIL": {"security_id": "467013", "exchange": EXCHANGE_CODE_MCX},  # CRUDEOIL FEB FUT (exp: 2026-02-19)
    "NATURALGAS": {"security_id": "467016", "exchange": EXCHANGE_CODE_MCX},  # Placeholder - will auto-resolve
}

# Aliases for symbols that we want to treat as canonical entries
_ALIAS_MAP = {
    "NIFTY50": "NIFTY",
}


def canonical_symbol(symbol: Optional[str]) -> str:
    """Return uppercase canonical symbol used across the backend."""
    if not symbol:
        return ""
    upper = symbol.upper()
    return _ALIAS_MAP.get(upper, upper)


def get_default_index_security(symbol: str) -> Optional[Dict[str, object]]:
    """Lookup the static index security metadata for a symbol."""
    canonical = canonical_symbol(symbol)
    entry = _DEFAULT_INDEX_SECURITY_IDS.get(canonical)
    if not entry:
        return None
    return {**entry, "symbol": canonical}


def get_default_equity_security(symbol: str) -> Optional[Dict[str, object]]:
    """Lookup the static equity security metadata for a symbol."""
    canonical = canonical_symbol(symbol)
    entry = _DEFAULT_EQUITY_SECURITY_IDS.get(canonical)
    if not entry:
        return None
    return {**entry, "symbol": canonical}


def iter_default_index_targets() -> Dict[str, Dict[str, object]]:
    """Return a mapping of security_id -> metadata for default instruments."""
    targets: Dict[str, Dict[str, object]] = {}
    combined = {**_DEFAULT_INDEX_SECURITY_IDS, **_DEFAULT_EQUITY_SECURITY_IDS}
    for symbol, entry in combined.items():
        sec_id = str(entry["security_id"])
        targets[sec_id] = {
            "security_id": sec_id,
            "exchange": entry["exchange"],
            "symbol": canonical_symbol(symbol),
        }
    return targets


def get_mcx_fallback(symbol: str) -> Optional[Dict[str, object]]:
    """
    Get MCX metadata by auto-selecting nearest-month contract.
    No longer uses hardcoded fallbacks - dynamically resolves from instrument master.
    """
    from app.market.instrument_master.registry import REGISTRY
    
    canonical = canonical_symbol(symbol)
    
    # Try to get nearest-month contract from instrument master
    nearest = REGISTRY.get_nearest_mcx_future(canonical)
    if nearest:
        return nearest
    
    # Only fall back to hardcoded if instrument master fails
    entry = _MCX_FALLBACK_SECURITY_IDS.get(canonical)
    if entry:
        print(f"[MCX-FALLBACK] {canonical}: Using hardcoded fallback (instrument master unavailable)")
        return {**entry, "symbol": canonical}
    
    return None


def mcx_watch_symbols() -> Dict[str, Dict[str, object]]:
    """Return canonical MCX symbols we care about and their fallbacks."""
    return {symbol: {**entry, "symbol": symbol} for symbol, entry in _MCX_FALLBACK_SECURITY_IDS.items()}
