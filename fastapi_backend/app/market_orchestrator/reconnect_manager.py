"""Reconnect manager with exponential backoff and jitter."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ReconnectState:
    attempts: int = 0
    next_retry_at: float = 0.0
    last_error: Optional[str] = None


class ReconnectManager:
    def __init__(self, min_delay: float = 1.0, max_delay: float = 60.0, factor: float = 2.0, jitter: float = 0.2, max_attempts: int = 8) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.factor = factor
        self.jitter = jitter
        self.max_attempts = max_attempts
        self._states: Dict[int, ReconnectState] = {}

    def _next_delay(self, attempts: int) -> float:
        delay = min(self.max_delay, self.min_delay * (self.factor ** max(attempts - 1, 0)))
        return delay * random.uniform(1 - self.jitter, 1 + self.jitter)

    def mark_disconnected(self, ws_id: int, error: Optional[str] = None) -> None:
        state = self._states.setdefault(ws_id, ReconnectState())
        state.attempts += 1
        state.last_error = error
        state.next_retry_at = time.time() + self._next_delay(state.attempts)

    def mark_connected(self, ws_id: int) -> None:
        self._states[ws_id] = ReconnectState()

    def should_reconnect(self, ws_id: int) -> bool:
        state = self._states.setdefault(ws_id, ReconnectState())
        if state.attempts >= self.max_attempts:
            return False
        return time.time() >= state.next_retry_at

    def get_status(self) -> Dict[int, Dict[str, object]]:
        status = {}
        for ws_id, state in self._states.items():
            status[ws_id] = {
                "attempts": state.attempts,
                "next_retry_at": state.next_retry_at,
                "last_error": state.last_error,
            }
        return status
