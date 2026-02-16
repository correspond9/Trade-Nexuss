"""Execution simulator engine orchestrating fills, queues, and logging."""
from __future__ import annotations

from datetime import datetime, timedelta

# IST timezone offset (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)

def ist_now():
    """Get current IST time"""
    return datetime.utcnow() + IST_OFFSET
import time
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.execution_simulator.execution_config import ExecutionConfig
from app.execution_simulator.latency_model import LatencyModel
from app.execution_simulator.slippage_model import SlippageModel
from app.execution_simulator.fill_engine import FillEngine
from app.execution_simulator.order_queue_manager import OrderQueueManager
from app.execution_simulator.rejection_engine import RejectionEngine
from app.market_cache.equities import get_equity
from app.market_cache.futures import list_futures
from app.market_cache.options import list_option_chains
from app.storage import models


class ExecutionEngine:
    def __init__(self, config: Optional[ExecutionConfig] = None) -> None:
        self.config = config or ExecutionConfig.load()
        self.latency_model = LatencyModel(self.config)
        self.slippage_model = SlippageModel(self.config)
        self.fill_engine = FillEngine(self.slippage_model)
        self.rejection_engine = RejectionEngine(self.config)
        self.queue_manager = OrderQueueManager()

    def _snapshot_for_order(self, symbol: str, exchange_segment: str) -> Dict[str, object]:
        symbol_text = (symbol or "").upper().strip()
        parts = symbol_text.split()
        try:
            from app.market.market_state import state
            depth = (state.get("depth") or {}).get(symbol_text)
            if isinstance(depth, dict):
                bids = depth.get("bids") or depth.get("bid") or []
                asks = depth.get("asks") or depth.get("ask") or []
                best_bid = bids[0].get("price") if bids else None
                best_ask = asks[0].get("price") if asks else None
                bid_qty = bids[0].get("qty") if bids else None
                ask_qty = asks[0].get("qty") if asks else None
                if best_bid is not None or best_ask is not None:
                    return {
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "bid_qty": bid_qty,
                        "ask_qty": ask_qty,
                        "last_update_time": ist_now().isoformat(),
                    }
        except Exception:
            pass
        if len(parts) >= 3 and parts[-1] in {"CE", "PE"}:
            try:
                strike_val = float(parts[-2])
                expiry_hint = None
                if len(parts) >= 4 and any(ch.isalpha() for ch in parts[-3]) and any(ch.isdigit() for ch in parts[-3]):
                    expiry_hint = parts[-3]
                    underlying = " ".join(parts[:-3]).strip()
                else:
                    underlying = " ".join(parts[:-2]).strip()
                if underlying:
                    try:
                        from app.services.authoritative_option_chain_service import authoritative_option_chain_service
                        chains = authoritative_option_chain_service.option_chain_cache.get(underlying, {})
                        best = None
                        for expiry, skeleton in chains.items():
                            if expiry_hint and expiry != expiry_hint:
                                continue
                            leg = skeleton.strikes.get(strike_val)
                            if not leg:
                                leg = skeleton.strikes.get(float(strike_val))
                            if not leg:
                                continue
                            data = leg.CE if parts[-1] == "CE" else leg.PE
                            if not data:
                                continue
                            best = data
                            break

                        if best:
                            bid = best.bid if best.bid is not None else best.ltp
                            ask = best.ask if best.ask is not None else best.ltp
                            return {
                                "best_bid": bid,
                                "best_ask": ask,
                                "bid_qty": None,
                                "ask_qty": None,
                                "last_update_time": ist_now().isoformat(),
                            }
                    except Exception:
                        pass
            except Exception:
                pass

        symbol_upper = (symbol or "").upper()
        exchange_prefix = (exchange_segment or "").split("_")[0].upper()
        equity = get_equity(exchange_prefix, symbol_upper)
        if equity:
            bid = equity.get("bid") or equity.get("ltp")
            ask = equity.get("ask") or equity.get("ltp")
            return {
                "best_bid": bid,
                "best_ask": ask,
                "bid_qty": equity.get("bid_qty"),
                "ask_qty": equity.get("ask_qty"),
                "last_update_time": equity.get("timestamp"),
            }

        futures = list_futures(exchange=exchange_prefix, symbol=symbol_upper)
        if futures:
            entry = futures[0]
            bid = entry.get("bid") or entry.get("ltp")
            ask = entry.get("ask") or entry.get("ltp")
            return {
                "best_bid": bid,
                "best_ask": ask,
                "bid_qty": entry.get("bid_qty"),
                "ask_qty": entry.get("ask_qty"),
                "last_update_time": entry.get("timestamp"),
            }

        chains = list_option_chains(exchange=exchange_prefix, symbol=symbol_upper)
        if chains:
            entry = chains[0]
            bid = entry.get("bid") or entry.get("ltp")
            ask = entry.get("ask") or entry.get("ltp")
            return {
                "best_bid": bid,
                "best_ask": ask,
                "bid_qty": entry.get("bid_qty"),
                "ask_qty": entry.get("ask_qty"),
                "last_update_time": entry.get("timestamp"),
            }

        # Fallback: use dashboard/live prices if available
        try:
            from app.market.live_prices import get_prices
            prices = get_prices()
            base = symbol_upper.split()[0]
            p = prices.get(base)
            if p is not None:
                return {
                    "best_bid": p,
                    "best_ask": p,
                    "bid_qty": None,
                    "ask_qty": None,
                    "last_update_time": None,
                }
        except Exception:
            pass

        return {
            "best_bid": None,
            "best_ask": None,
            "bid_qty": None,
            "ask_qty": None,
            "last_update_time": None,
        }

    def _exchange_from_segment(self, exchange_segment: str) -> str:
        prefix = (exchange_segment or "").split("_")[0].upper()
        return prefix or "NSE"

    def _normalize_underlying(self, text: str) -> str:
        value = (text or "").strip().upper()
        if value in {"NIFTY 50", "NIFTY50"}:
            return "NIFTY"
        if value in {"BANK NIFTY", "NIFTY BANK", "BANKNIFTY"}:
            return "BANKNIFTY"
        if value in {"BSE SENSEX", "S&P BSE SENSEX", "SENSEX 50"}:
            return "SENSEX"
        return value

    def _extract_underlying_from_symbol(self, symbol: str) -> str:
        parts = (symbol or "").strip().upper().split()
        if len(parts) >= 3 and parts[-1] in {"CE", "PE"}:
            return self._normalize_underlying(" ".join(parts[:-2]))
        if parts:
            return self._normalize_underlying(parts[0])
        return ""

    def _resolve_lot_step(self, order: models.MockOrder) -> int:
        try:
            segment = (order.exchange_segment or "").upper()
            symbol_text = (order.symbol or "").upper()
            is_derivative = (
                "FNO" in segment or "NFO" in segment or "MCX" in segment or symbol_text.endswith(" CE") or symbol_text.endswith(" PE")
            )
            if not is_derivative:
                return 1

            underlying = self._extract_underlying_from_symbol(symbol_text)
            if not underlying:
                return 1

            try:
                from app.services.dhan_security_id_mapper import dhan_security_mapper
                lot = dhan_security_mapper.get_lot_size(underlying)
                if lot and int(lot) > 1:
                    return int(lot)
            except Exception:
                pass

            try:
                from app.services.span_parameters_service import span_parameters_service
                lot = span_parameters_service.get_lot_size(underlying, fallback=1)
                if lot and int(lot) > 1:
                    return int(lot)
            except Exception:
                pass
        except Exception:
            pass
        return 1

    def _log_event(self, db: Session, order: models.MockOrder, event_type: str, decision_price: Optional[float], fill_price: Optional[float], fill_qty: Optional[int], reason: Optional[str], latency_ms: Optional[int], slippage: Optional[float]) -> None:
        event = models.ExecutionEvent(
            order_id=order.id if order else None,
            user_id=order.user_id if order else None,
            symbol=order.symbol if order else "UNKNOWN",
            event_type=event_type,
            decision_time_price=decision_price,
            fill_price=fill_price,
            fill_quantity=fill_qty,
            reason=reason,
            latency_ms=latency_ms,
            slippage=slippage,
        )
        db.add(event)

    def _apply_fill(self, db: Session, order: models.MockOrder, fill_price: float, fill_qty: int) -> None:
        previous_filled_qty = int(order.filled_qty or 0)
        new_filled_qty = previous_filled_qty + int(fill_qty)
        order.filled_qty = new_filled_qty

        existing_price = float(order.price or 0.0)
        if order.order_type == "MARKET" or existing_price <= 0:
            if previous_filled_qty <= 0:
                order.price = float(fill_price)
            else:
                weighted_avg = ((existing_price * previous_filled_qty) + (float(fill_price) * int(fill_qty))) / max(1, new_filled_qty)
                order.price = float(weighted_avg)

        if order.filled_qty >= order.quantity:
            order.status = "EXECUTED"
        else:
            order.status = "PARTIAL"
        order.updated_at = ist_now()

        trade = models.MockTrade(
            order_id=order.id,
            user_id=order.user_id,
            price=fill_price,
            qty=fill_qty,
        )
        db.add(trade)

        user = db.query(models.UserAccount).filter(models.UserAccount.id == order.user_id).first()
        if not user:
            return

        margin = db.query(models.MarginAccount).filter(models.MarginAccount.user_id == order.user_id).first()
        if not margin:
            margin = models.MarginAccount(user_id=order.user_id, available_margin=0.0, used_margin=0.0)
            db.add(margin)
            db.flush()

        turnover = fill_price * fill_qty
        brokerage_plan = None
        if user.brokerage_plan_id:
            brokerage_plan = db.query(models.BrokeragePlan).filter(models.BrokeragePlan.id == user.brokerage_plan_id).first()
        if not brokerage_plan:
            brokerage_plan = db.query(models.BrokeragePlan).filter(models.BrokeragePlan.name == "DEFAULT").first()
        if not brokerage_plan:
            brokerage_plan = models.BrokeragePlan(name="DEFAULT", flat_fee=20.0, percent_fee=0.0, max_fee=20.0)
            db.add(brokerage_plan)
            db.flush()

        brokerage = brokerage_plan.flat_fee + (turnover * (brokerage_plan.percent_fee or 0.0))
        brokerage = min(brokerage, brokerage_plan.max_fee or brokerage)

        multiplier = float(user.margin_multiplier or 5.0)
        if multiplier <= 0:
            multiplier = 5.0
        required_margin = abs(fill_price * fill_qty)
        if order.product_type == "MIS":
            required_margin = required_margin / multiplier
        margin.used_margin += required_margin
        margin.available_margin -= required_margin
        margin.updated_at = ist_now()

        if order.transaction_type == "BUY":
            user.wallet_balance = (user.wallet_balance or 0.0) - (turnover + brokerage)
            entry = models.LedgerEntry(user_id=user.id, entry_type="TRADE_PNL", credit=0.0, debit=turnover + brokerage, balance=user.wallet_balance, remarks="Order filled BUY")
        else:
            user.wallet_balance = (user.wallet_balance or 0.0) + (turnover - brokerage)
            entry = models.LedgerEntry(user_id=user.id, entry_type="TRADE_PNL", credit=turnover - brokerage, debit=0.0, balance=user.wallet_balance, remarks="Order filled SELL")
        db.add(entry)

        position = (
            db.query(models.MockPosition)
            .filter(
                models.MockPosition.user_id == order.user_id,
                models.MockPosition.symbol == order.symbol,
                models.MockPosition.product_type == order.product_type,
            )
            .first()
        )
        if not position:
            position = models.MockPosition(
                user_id=order.user_id,
                symbol=order.symbol,
                exchange_segment=order.exchange_segment,
                product_type=order.product_type,
                quantity=0,
                avg_price=0.0,
                realized_pnl=0.0,
                status="OPEN",
            )
            db.add(position)
            db.flush()

        qty = fill_qty if order.transaction_type == "BUY" else -fill_qty
        new_qty = position.quantity + qty
        
        # Check if this is a closing transaction (opposite direction)
        is_closing = (position.quantity > 0 and qty < 0) or (position.quantity < 0 and qty > 0)
        
        if is_closing:
            # This is a closing transaction - calculate closing quantity and PnL
            closing_qty = min(abs(position.quantity), abs(qty))
            pnl = (fill_price - position.avg_price) * closing_qty
            if position.quantity < 0:
                pnl = -pnl
            position.realized_pnl += pnl
            position.quantity = new_qty
            if position.quantity == 0:
                position.status = "CLOSED"
            else:
                position.avg_price = fill_price
        else:
            # This is adding to position - update average price
            total_qty = position.quantity + qty
            if total_qty != 0:
                position.avg_price = ((position.avg_price * position.quantity) + (fill_price * qty)) / total_qty
            position.quantity = total_qty
        position.updated_at = ist_now()
        db.commit()  # Commit position update immediately

    def process_new_order(self, db: Session, order: models.MockOrder) -> None:
        exchange = self._exchange_from_segment(order.exchange_segment)
        snapshot = self._snapshot_for_order(order.symbol, order.exchange_segment)
        effective_type = order.order_type
        bid = snapshot.get("best_bid")
        ask = snapshot.get("best_ask")
        trigger = order.trigger_price
        if order.order_type in {"SL-M", "SL-L", "TRIGGER", "GTT"}:
            if trigger is None:
                order.status = "REJECTED"
                order.remarks = "INVALID_TRIGGER"
                order.updated_at = ist_now()
                self._log_event(db, order, "ORDER_REJECTED", ask or bid, None, None, "INVALID_TRIGGER", None, None)
                return
            if order.transaction_type == "BUY" and ask is not None and ask >= trigger:
                effective_type = "MARKET" if order.order_type in {"SL-M", "TRIGGER"} else "LIMIT"
            elif order.transaction_type == "SELL" and bid is not None and bid <= trigger:
                effective_type = "MARKET" if order.order_type in {"SL-M", "TRIGGER"} else "LIMIT"
            else:
                order.status = "PENDING"
                return

        lot_step = self._resolve_lot_step(order)
        reason = self.rejection_engine.validate(
            exchange,
            effective_type,
            order.transaction_type,
            order.price,
            order.quantity,
            snapshot,
            lot_step=lot_step,
        )
        if reason:
            order.status = "REJECTED"
            order.remarks = reason
            order.updated_at = ist_now()
            self._log_event(db, order, "ORDER_REJECTED", snapshot.get("best_ask") or snapshot.get("best_bid"), None, None, reason, None, None)
            return

        latency_ms = self.latency_model.sample_latency_ms(exchange, order.user_id)
        time.sleep(latency_ms / 1000.0)

        decision_price = snapshot.get("best_ask") if order.transaction_type == "BUY" else snapshot.get("best_bid")
        self._log_event(db, order, "ORDER_ACCEPTED", decision_price, None, None, None, latency_ms, None)

        remaining = order.quantity - order.filled_qty
        if remaining <= 0:
            return

        bid_qty = snapshot.get("bid_qty") or self.config.default_bid_qty
        ask_qty = snapshot.get("ask_qty") or self.config.default_ask_qty
        spread = (ask - bid) if ask is not None and bid is not None else 0.0
        lot_step = self._resolve_lot_step(order)

        if effective_type == "MARKET":
            top_price = ask if order.transaction_type == "BUY" else bid
            top_qty = ask_qty if order.transaction_type == "BUY" else bid_qty
            fills = self.fill_engine.compute_fills(exchange, order.transaction_type, remaining, top_price, top_qty, spread, lot_step=lot_step)
            if not fills:
                return
            for fill in fills:
                self._apply_fill(db, order, fill.fill_price, fill.fill_quantity)
                event_type = "FULL_FILL" if order.filled_qty >= order.quantity else "PARTIAL_FILL"
                self._log_event(db, order, event_type, top_price, fill.fill_price, fill.fill_quantity, None, latency_ms, fill.slippage)
            return

        if effective_type == "LIMIT":
            if order.transaction_type == "BUY" and ask is not None and order.price >= ask:
                top_price = ask
                top_qty = ask_qty
            elif order.transaction_type == "SELL" and bid is not None and order.price <= bid:
                top_price = bid
                top_qty = bid_qty
            else:
                self.queue_manager.enqueue(order.symbol, order.transaction_type, order.price or 0.0, order.id)
                order.status = "PENDING"
                return

            fills = self.fill_engine.compute_fills(exchange, order.transaction_type, remaining, top_price, top_qty, spread, lot_step=lot_step)
            if not fills:
                return
            for fill in fills:
                self._apply_fill(db, order, fill.fill_price, fill.fill_quantity)
                event_type = "FULL_FILL" if order.filled_qty >= order.quantity else "PARTIAL_FILL"
                self._log_event(db, order, event_type, top_price, fill.fill_price, fill.fill_quantity, None, latency_ms, fill.slippage)
            return

        order.status = "PENDING"

    def process_pending_orders(self, db: Session) -> None:
        pending = (
            db.query(models.MockOrder)
            .filter(models.MockOrder.status.in_(["PENDING", "PARTIAL"]))
            .order_by(models.MockOrder.created_at.asc())
        )
        for order in pending:
            exchange = self._exchange_from_segment(order.exchange_segment)
            snapshot = self._snapshot_for_order(order.symbol, order.exchange_segment)
            cfg = self.config.for_exchange(exchange)
            now = ist_now()
            if order.created_at and (now - order.created_at).total_seconds() > cfg.timeout_seconds:
                order.status = "REJECTED"
                order.remarks = "NO_LIQUIDITY_TIMEOUT"
                order.updated_at = ist_now()
                self._log_event(db, order, "ORDER_REJECTED", snapshot.get("best_ask") or snapshot.get("best_bid"), None, None, "NO_LIQUIDITY_TIMEOUT", None, None)
                continue

            remaining = order.quantity - order.filled_qty
            if remaining <= 0:
                continue

            bid = snapshot.get("best_bid")
            ask = snapshot.get("best_ask")
            bid_qty = snapshot.get("bid_qty") or self.config.default_bid_qty
            ask_qty = snapshot.get("ask_qty") or self.config.default_ask_qty
            if bid is None or ask is None:
                continue

            spread = ask - bid
            lot_step = self._resolve_lot_step(order)
            effective_type = order.order_type
            trigger = order.trigger_price
            if order.order_type in {"SL-M", "SL-L", "TRIGGER", "GTT"} and trigger is not None:
                if order.transaction_type == "BUY" and ask >= trigger:
                    effective_type = "MARKET" if order.order_type in {"SL-M", "TRIGGER"} else "LIMIT"
                elif order.transaction_type == "SELL" and bid <= trigger:
                    effective_type = "MARKET" if order.order_type in {"SL-M", "TRIGGER"} else "LIMIT"
                else:
                    continue

            if effective_type == "MARKET":
                top_price = ask if order.transaction_type == "BUY" else bid
                top_qty = ask_qty if order.transaction_type == "BUY" else bid_qty
            else:
                if order.transaction_type == "BUY" and order.price >= ask:
                    top_price = ask
                    top_qty = ask_qty
                elif order.transaction_type == "SELL" and order.price <= bid:
                    top_price = bid
                    top_qty = bid_qty
                else:
                    continue

            fills = self.fill_engine.compute_fills(exchange, order.transaction_type, remaining, top_price, top_qty, spread, lot_step=lot_step)
            if not fills:
                continue
            latency_ms = self.latency_model.sample_latency_ms(exchange, order.user_id)
            for fill in fills:
                self._apply_fill(db, order, fill.fill_price, fill.fill_quantity)
                event_type = "FULL_FILL" if order.filled_qty >= order.quantity else "PARTIAL_FILL"
                self._log_event(db, order, event_type, top_price, fill.fill_price, fill.fill_quantity, None, latency_ms, fill.slippage)

_ENGINE = ExecutionEngine()


def get_execution_engine() -> ExecutionEngine:
    return _ENGINE
