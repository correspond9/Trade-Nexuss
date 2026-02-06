"""Route ticks to downstream engines based on segment and instrument type."""
from __future__ import annotations

from typing import Callable, Dict, Optional


class ExchangeRouter:
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Dict], None]] = {}

    def register_handler(self, kind: str, handler: Callable[[Dict], None]) -> None:
        self._handlers[kind] = handler

    def _infer_kind(self, tick: Dict) -> str:
        if tick.get("option_type"):
            return "options"
        if tick.get("instrument_type") in ("FUT", "FUTURE"):
            return "futures"
        if tick.get("expiry"):
            return "futures"
        if tick.get("is_index"):
            return "index"
        return "equities"

    def route_tick(self, tick: Dict) -> None:
        kind = self._infer_kind(tick)
        handler = self._handlers.get(kind)
        if handler:
            handler(tick)
            return

        if kind == "options":
            self._route_option_tick(tick)
        elif kind == "futures":
            self._route_future_tick(tick)

    def _route_option_tick(self, tick: Dict) -> None:
        try:
            from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
            if tick.get("segment") == "MCX":
                commodity_option_chain_service.update_option_tick(
                    symbol=str(tick.get("symbol")),
                    expiry=str(tick.get("expiry")),
                    strike=float(tick.get("strike")),
                    option_type=str(tick.get("option_type")),
                    ltp=tick.get("ltp"),
                    bid=tick.get("bid"),
                    ask=tick.get("ask"),
                    oi=tick.get("oi"),
                    volume=tick.get("volume"),
                    iv=tick.get("iv"),
                )
                return
        except Exception:
            pass

        try:
            from app.services.authoritative_option_chain_service import authoritative_option_chain_service
            authoritative_option_chain_service.update_option_tick_from_websocket(
                symbol=str(tick.get("symbol")),
                expiry=str(tick.get("expiry")),
                strike=float(tick.get("strike")),
                option_type=str(tick.get("option_type")),
                ltp=tick.get("ltp"),
                bid=tick.get("bid"),
                ask=tick.get("ask"),
                depth=tick.get("depth"),
                oi=tick.get("oi"),
                volume=tick.get("volume"),
                iv=tick.get("iv"),
            )
        except Exception:
            pass

    def _route_future_tick(self, tick: Dict) -> None:
        if tick.get("segment") == "MCX":
            try:
                from app.commodity_engine.commodity_futures_service import commodity_futures_service
                commodity_futures_service.update_future_tick(
                    symbol=str(tick.get("symbol")),
                    expiry=str(tick.get("expiry")),
                    ltp=tick.get("ltp"),
                    bid=tick.get("bid"),
                    ask=tick.get("ask"),
                    oi=tick.get("oi"),
                    volume=tick.get("volume"),
                )
                return
            except Exception:
                pass
