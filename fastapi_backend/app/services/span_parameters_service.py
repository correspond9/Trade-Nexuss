import os
import re
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class SpanParametersService:
    def __init__(self) -> None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.cache_dir = os.path.join(base_dir, "cache", "nse")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.equity_span_percent: Dict[str, float] = {}
        self.mcx_span_percent: Dict[str, float] = {}
        self.short_option_addon_percent: Dict[str, float] = {}
        self.equity_risk_arrays: Dict[Tuple[str, str, Optional[str], Optional[str], Optional[str]], List[float]] = {}
        self.mcx_risk_arrays: Dict[Tuple[str, str, Optional[str], Optional[str], Optional[str]], List[float]] = {}
        self.lot_sizes: Dict[str, int] = {}

    def refresh_from_extracted(self) -> None:
        self.equity_span_percent = self._load_span_percent_from_dir(prefix="equity_span")
        self.mcx_span_percent = self._load_span_percent_from_dir(prefix="commodity_span")
        self.short_option_addon_percent = self._load_short_option_addon_from_dir(prefix="equity_span")
        self.equity_risk_arrays = self._load_spn_xml(prefix="equity_span")
        self.mcx_risk_arrays = self._load_spn_xml(prefix="commodity_span")
        self.lot_sizes = self._load_lot_sizes_from_dir()

    def _latest_extract_dir(self, prefix: str) -> Optional[str]:
        dirs = [d for d in os.listdir(self.cache_dir) if d.startswith(prefix + "_")]
        if not dirs:
            return None
        dirs.sort(reverse=True)
        return os.path.join(self.cache_dir, dirs[0])

    def _load_span_percent_from_dir(self, prefix: str) -> Dict[str, float]:
        result: Dict[str, float] = {}
        path = self._latest_extract_dir(prefix)
        if not path or not os.path.isdir(path):
            return result
        for root, _, files in os.walk(path):
            for name in files:
                if not (name.lower().endswith(".csv") or name.lower().endswith(".txt")):
                    continue
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            parts = [p.strip() for p in re.split(r"[,\t;]", line)]
                            if len(parts) < 2:
                                continue
                            sym = parts[0].upper()
                            val = parts[1].replace("%", "")
                            try:
                                pct = float(val)
                                if pct > 1:
                                    pct = pct / 100.0
                                if 0 < pct <= 1:
                                    result[sym] = pct
                            except ValueError:
                                continue
                except Exception as exc:
                    logger.debug("SPAN percent parse skip %s: %s", name, exc)
        return result

    def _load_short_option_addon_from_dir(self, prefix: str) -> Dict[str, float]:
        result: Dict[str, float] = {}
        path = self._latest_extract_dir(prefix)
        if not path or not os.path.isdir(path):
            return result
        for root, _, files in os.walk(path):
            for name in files:
                if not (name.lower().endswith(".csv") or name.lower().endswith(".txt")):
                    continue
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            parts = [p.strip() for p in re.split(r"[,\t;]", line)]
                            if len(parts) < 3:
                                continue
                            if parts[1].upper() not in {"SHORT_OPTION_ADDON", "SO_ADDON", "OPTION_ADDON"}:
                                continue
                            sym = parts[0].upper()
                            val = parts[2].replace("%", "")
                            try:
                                pct = float(val)
                                if pct > 1:
                                    pct = pct / 100.0
                                if 0 < pct <= 1:
                                    result[sym] = pct
                            except ValueError:
                                continue
                except Exception as exc:
                    logger.debug("SPAN addon parse skip %s: %s", name, exc)
        return result

    def get_equity_span_percent(self, underlying_or_symbol: str, default_index: float, default_stock: float) -> float:
        key = (underlying_or_symbol or "").upper()
        if key in self.equity_span_percent:
            return self.equity_span_percent[key]
        compact = key.replace(" ", "")
        for k, v in self.equity_span_percent.items():
            if k.replace(" ", "") == compact:
                return v
        if "NIFTY" in key or "BANK" in key or "SENSEX" in key:
            return default_index
        return default_stock

    def get_mcx_span_percent(self, underlying_or_symbol: str, fallback: float) -> float:
        key = (underlying_or_symbol or "").upper()
        if key in self.mcx_span_percent:
            return self.mcx_span_percent[key]
        compact = key.replace(" ", "")
        for k, v in self.mcx_span_percent.items():
            if k.replace(" ", "") == compact:
                return v
        return fallback

    def get_short_option_addon(self, underlying_or_symbol: str, fallback: float) -> float:
        key = (underlying_or_symbol or "").upper()
        if key in self.short_option_addon_percent:
            return self.short_option_addon_percent[key]
        compact = key.replace(" ", "")
        for k, v in self.short_option_addon_percent.items():
            if k.replace(" ", "") == compact:
                return v
        return fallback

    def _load_spn_xml(self, prefix: str) -> Dict[Tuple[str, str, Optional[str], Optional[str], Optional[str]], List[float]]:
        result: Dict[Tuple[str, str, Optional[str], Optional[str], Optional[str]], List[float]] = {}
        path = self._latest_extract_dir(prefix)
        if not path or not os.path.isdir(path):
            return result
        for root, _, files in os.walk(path):
            for name in files:
                if not name.lower().endswith(".spn"):
                    continue
                file_path = os.path.join(root, name)
                try:
                    tree = ET.parse(file_path)
                    doc = tree.getroot()
                except Exception as exc:
                    logger.debug("SPN XML parse failed %s: %s", name, exc)
                    continue
                for elem in doc.iter():
                    text = (elem.text or "").strip()
                    if not text:
                        continue
                    parts = re.split(r"[,\s]+", text)
                    floats: List[float] = []
                    ok = True
                    for p in parts:
                        if not p:
                            continue
                        try:
                            floats.append(float(p))
                        except ValueError:
                            ok = False
                            break
                    if not ok or len(floats) != 16:
                        continue
                    inst = None
                    und = None
                    exp = None
                    strike = None
                    opt = None
                    cur = elem
                    for _ in range(3):
                        if cur is None:
                            break
                        a = cur.attrib
                        inst = inst or a.get("instrument") or a.get("inst") or inst
                        und = und or a.get("symbol") or a.get("underlying") or und
                        exp = exp or a.get("expiry") or a.get("exp") or exp
                        strike = strike or a.get("strike") or a.get("str") or strike
                        opt = opt or a.get("optionType") or a.get("optType") or a.get("opt") or opt
                        cur = cur.getparent() if hasattr(cur, "getparent") else None
                    und_key = (und or "").upper()
                    inst_key = (inst or "").upper() if inst else None
                    opt_key = (opt or "").upper() if opt else None
                    strike_key = str(strike) if strike is not None else None
                    exp_key = (exp or "")
                    if not und_key or not inst_key:
                        continue
                    key = (inst_key, und_key, exp_key, strike_key, opt_key)
                    result[key] = floats
        return result

    def _load_lot_sizes_from_dir(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        path = self._latest_extract_dir("equity_span") or self._latest_extract_dir("commodity_span")
        if not path or not os.path.isdir(path):
            return result
        for root, _, files in os.walk(path):
            for name in files:
                if not (name.lower().endswith(".csv") or name.lower().endswith(".txt")):
                    continue
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            parts = [p.strip() for p in re.split(r"[,\t;]", line)]
                            if len(parts) < 3:
                                continue
                            sym = parts[0].upper()
                            try:
                                lot = int(float(parts[2]))
                                if lot > 0:
                                    result[sym] = lot
                            except ValueError:
                                continue
                except Exception as exc:
                    logger.debug("Lot size parse skip %s: %s", name, exc)
        return result

    def get_equity_risk_array(self, instrument: str, underlying: str, expiry: Optional[str], strike: Optional[str], option_type: Optional[str]) -> List[float]:
        key = (instrument.upper(), (underlying or "").upper(), expiry or "", strike, option_type)
        return self.equity_risk_arrays.get(key, [])

    def get_mcx_risk_array(self, instrument: str, underlying: str, expiry: Optional[str], strike: Optional[str], option_type: Optional[str]) -> List[float]:
        key = (instrument.upper(), (underlying or "").upper(), expiry or "", strike, option_type)
        return self.mcx_risk_arrays.get(key, [])

    def get_lot_size(self, underlying: str, fallback: int = 1) -> int:
        key = (underlying or "").upper()
        if key in self.lot_sizes:
            return self.lot_sizes[key]
        compact = key.replace(" ", "")
        for k, v in self.lot_sizes.items():
            if k.replace(" ", "") == compact:
                return v
        return fallback


span_parameters_service = SpanParametersService()
