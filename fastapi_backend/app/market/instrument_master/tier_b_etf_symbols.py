from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Set


ETF_SOURCE_FILE = "MW-ETF-16-Feb-2026.csv"


@lru_cache(maxsize=1)
def get_tier_b_etf_symbols() -> Set[str]:
    """Load Tier-B ETF symbols (optional; controlled independently from Tier-B equities)."""
    enabled = (os.getenv("ENABLE_TIER_B_ETF") or "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return set()

    csv_path = Path(__file__).resolve().parent / ETF_SOURCE_FILE
    if not csv_path.exists():
        return set()

    symbols: Set[str] = set()
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            _header = next(reader, None)
            for row in reader:
                if not row:
                    continue
                raw = str(row[0] or "").strip().strip('"').upper()
                if not raw or raw == "SYMBOL":
                    continue
                symbols.add(raw)
    except Exception:
        return set()

    return symbols
