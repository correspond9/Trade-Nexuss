from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Set


EQUITY_SOURCE_FILE = "EQUITY_LIST.csv"


@lru_cache(maxsize=1)
def get_tier_a_equity_symbols() -> Set[str]:
    """Load Tier-A equity symbols from curated EQUITY_LIST.csv."""
    csv_path = Path(__file__).resolve().parent / EQUITY_SOURCE_FILE
    if not csv_path.exists():
        return set()

    symbols: Set[str] = set()
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                raw = str(row.get("SYMBOL") or "").strip().strip('"').upper()
                if not raw or raw == "SYMBOL":
                    continue
                symbols.add(raw)
    except Exception:
        return set()

    return symbols
