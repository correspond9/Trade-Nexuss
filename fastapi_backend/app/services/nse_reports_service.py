import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Optional

import aiohttp
import os
import zipfile

logger = logging.getLogger(__name__)


@dataclass
class DailyReports:
    trade_date: Optional[date] = None
    equity_span_url: Optional[str] = None
    equity_exposure_url: Optional[str] = None
    commodity_span_url: Optional[str] = None
    exposures_fno: Dict[str, float] = field(default_factory=dict)


class NSEReportsService:
    def __init__(self) -> None:
        self.base_url = "https://www.nseindia.com/all-reports-derivatives"
        self.state = DailyReports()
        self._lock = asyncio.Lock()
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "nse")
        os.makedirs(self.cache_dir, exist_ok=True)

    async def refresh_daily_reports(self) -> None:
        async with self._lock:
            try:
                logger.info("Refreshing NSE daily derivative report links...")
                html = await self._fetch_html(self.base_url)
                if not html:
                    logger.warning("Failed to fetch NSE reports page")
                    return
                # Find exposure CSV link
                exposure_match = re.search(r'href="([^"]*ael_\d{8}\.csv)"', html, re.IGNORECASE)
                # Find equity SPAN zip link
                span_eq_match = re.search(r'href="([^"]*nsccl\.\d{8}\.i1\.zip)"', html, re.IGNORECASE)
                # Find commodity SPAN zip link
                span_com_match = re.search(r'href="([^"]*com.*\.\d{8}\.i1\.zip)"', html, re.IGNORECASE)

                self.state.equity_exposure_url = self._abs_url(exposure_match.group(1)) if exposure_match else None
                self.state.equity_span_url = self._abs_url(span_eq_match.group(1)) if span_eq_match else None
                self.state.commodity_span_url = self._abs_url(span_com_match.group(1)) if span_com_match else None
                self.state.trade_date = date.today()

                if self.state.equity_exposure_url:
                    await self._load_exposures_fno(self.state.equity_exposure_url)
                else:
                    logger.warning("Exposure CSV link not found; using defaults")

                # Download and cache SPAN files for the day (kept ready for parsing)
                if self.state.equity_span_url:
                    await self._download_and_extract_zip(self.state.equity_span_url, "equity_span")
                if self.state.commodity_span_url:
                    await self._download_and_extract_zip(self.state.commodity_span_url, "commodity_span")
                try:
                    from app.services.span_parameters_service import span_parameters_service
                    span_parameters_service.refresh_from_extracted()
                except Exception:
                    logger.warning("SPAN parameters refresh failed; using previous cache")
            except Exception as exc:
                logger.error("Error refreshing daily reports: %s", exc)

    async def _fetch_html(self, url: str) -> Optional[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Cache-Control": "no-cache",
        }
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning("GET %s -> %s", url, resp.status)
                    return None
                return await resp.text()

    async def _load_exposures_fno(self, csv_url: str) -> None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/csv,*/*;q=0.8",
            "Referer": "https://www.nseindia.com/",
        }
        timeout = aiohttp.ClientTimeout(total=15)
        exposures: Dict[str, float] = {}
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(csv_url) as resp:
                if resp.status != 200:
                    logger.warning("GET %s -> %s", csv_url, resp.status)
                    return
                text = await resp.text()
                for line in text.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 2:
                        continue
                    # Heuristic: first column underlying/symbol, second exposure percent (e.g., 0.05 or 5)
                    sym = parts[0].upper()
                    val_raw = parts[1].replace("%", "")
                    try:
                        val = float(val_raw)
                        if val > 1:
                            val = val / 100.0
                    except ValueError:
                        continue
                    if sym and 0 <= val <= 1:
                        exposures[sym] = val
        # Cache CSV to disk for audit
        try:
            fname = f"exposure_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            with open(os.path.join(self.cache_dir, fname), "w", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass
        if exposures:
            self.state.exposures_fno = exposures
            logger.info("Loaded %d exposure entries", len(exposures))
        else:
            logger.warning("No exposures parsed from CSV")

    def _abs_url(self, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        if href.startswith("http"):
            return href
        return f"https://www.nseindia.com{href}"

    async def _download_and_extract_zip(self, url: str, prefix: str) -> None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/zip,*/*;q=0.8",
            "Referer": "https://www.nseindia.com/",
        }
        timeout = aiohttp.ClientTimeout(total=30)
        zip_path = os.path.join(self.cache_dir, f"{prefix}_{datetime.utcnow().strftime('%Y%m%d')}.zip")
        extract_dir = os.path.join(self.cache_dir, f"{prefix}_{datetime.utcnow().strftime('%Y%m%d')}")
        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("GET %s -> %s", url, resp.status)
                        return
                    data = await resp.read()
                    with open(zip_path, "wb") as f:
                        f.write(data)
            # Extract zip
            try:
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(extract_dir)
                logger.info("Downloaded and extracted %s to %s", prefix, extract_dir)
            except Exception as exc:
                logger.warning("Failed to extract %s: %s", zip_path, exc)
        except Exception as exc:
            logger.warning("Failed to download %s: %s", url, exc)

    def get_exposure_percent(self, symbol_or_underlying: str, default_percent: float = 0.05) -> float:
        key = (symbol_or_underlying or "").upper()
        # Try direct symbol
        if key in self.state.exposures_fno:
            return self.state.exposures_fno[key]
        # Try stripping spaces (e.g., BANKNIFTY vs BANK NIFTY)
        compact = key.replace(" ", "")
        for k, v in self.state.exposures_fno.items():
            if k.replace(" ", "") == compact:
                return v
        return default_percent


nse_reports_service = NSEReportsService()
