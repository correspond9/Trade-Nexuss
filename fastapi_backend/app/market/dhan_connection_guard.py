from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


_lock = threading.RLock()


def _config_dir() -> Path:
    # Align with app.storage.settings_manager which writes to fastapi_backend/config
    return Path(__file__).resolve().parents[2] / "config"


def _state_file() -> Path:
    return _config_dir() / "dhan_connection_guard.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_forces_disabled() -> bool:
    # Backwards-compatible flags already used in orchestrator/live_feed.
    flag = (
        os.getenv("DISABLE_DHAN_WS")
        or os.getenv("BACKEND_OFFLINE")
        or os.getenv("DISABLE_MARKET_STREAMS")
        or ""
    ).strip().lower()
    return flag in ("1", "true", "yes", "on")


_state: Dict[str, Any] = {
    "manual_enabled": True,
    "manual_reason": None,
    "manual_updated_at": None,
    "manual_updated_by": None,
}


def _load_from_disk() -> None:
    path = _state_file()
    if not path.exists():
        return
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            _state.update({
                "manual_enabled": bool(data.get("manual_enabled", True)),
                "manual_reason": data.get("manual_reason"),
                "manual_updated_at": data.get("manual_updated_at"),
                "manual_updated_by": data.get("manual_updated_by"),
            })
    except Exception:
        # If the guard file is corrupted, default to enabled (fail-open) to avoid
        # taking production down unexpectedly. Env flags still force-disable.
        return


def _save_to_disk() -> None:
    directory = _config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "manual_enabled": bool(_state.get("manual_enabled", True)),
        "manual_reason": _state.get("manual_reason"),
        "manual_updated_at": _state.get("manual_updated_at"),
        "manual_updated_by": _state.get("manual_updated_by"),
    }
    _state_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


with _lock:
    _load_from_disk()


def get_status() -> Dict[str, Any]:
    with _lock:
        env_forced_disabled = _env_forces_disabled()
        manual_enabled = bool(_state.get("manual_enabled", True))
        effective_enabled = (not env_forced_disabled) and manual_enabled

        return {
            "effective_enabled": effective_enabled,
            "env_forced_disabled": env_forced_disabled,
            "manual_enabled": manual_enabled,
            "manual_reason": _state.get("manual_reason"),
            "manual_updated_at": _state.get("manual_updated_at"),
            "manual_updated_by": _state.get("manual_updated_by"),
        }


def is_enabled() -> bool:
    return bool(get_status().get("effective_enabled"))


def disable(reason: Optional[str] = None, actor: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        _state["manual_enabled"] = False
        _state["manual_reason"] = (reason or "Emergency disconnect").strip() if reason is not None else "Emergency disconnect"
        _state["manual_updated_at"] = _utc_now_iso()
        _state["manual_updated_by"] = (actor or "admin")
        _save_to_disk()
        return get_status()


def enable(actor: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        _state["manual_enabled"] = True
        _state["manual_reason"] = None
        _state["manual_updated_at"] = _utc_now_iso()
        _state["manual_updated_by"] = (actor or "admin")
        _save_to_disk()
        return get_status()


def ensure_enabled(purpose: str = "Dhan connection") -> None:
    if is_enabled():
        return
    status = get_status()
    # Provide a deterministic message for clients/logs.
    raise RuntimeError(
        f"{purpose} blocked: manual_enabled={status.get('manual_enabled')} env_forced_disabled={status.get('env_forced_disabled')}"
    )
