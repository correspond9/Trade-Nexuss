from __future__ import annotations

import asyncio
import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def _ensure_local_sdk_on_path() -> None:
    try:
        root = Path(__file__).resolve().parents[3]
        local_sdk_src = root / "DhanHQ-py-main" / "src"
        if local_sdk_src.exists():
            sdk_path = str(local_sdk_src)
            if sdk_path not in sys.path:
                sys.path.insert(0, sdk_path)
    except Exception as exc:
        logger.warning("Failed to prepare local Dhan SDK path: %s", exc)


@lru_cache(maxsize=16)
def _get_client(client_id: str, access_token: str):
    _ensure_local_sdk_on_path()
    from dhanhq import DhanContext, dhanhq

    context = DhanContext(client_id=client_id, access_token=access_token)
    return dhanhq(context)


def _parse_sdk_response(response: Any) -> Dict[str, Any]:
    if not isinstance(response, dict):
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": "invalid response",
        }

    if response.get("status") == "success":
        return {
            "ok": True,
            "data": response.get("data"),
            "error_kind": None,
            "error": None,
        }

    remarks = response.get("remarks")
    if isinstance(remarks, dict):
        error_message = str(remarks.get("error_message") or "")
        error_code = str(remarks.get("error_code") or "")
        details = f"{error_code} {error_message}".strip()
    else:
        details = str(remarks or "")

    low = details.lower()
    if "401" in low or "403" in low or "auth" in low or "token" in low:
        error_kind = "auth"
    elif "429" in low or ("rate" in low and "limit" in low):
        error_kind = "rate"
    else:
        error_kind = "other"

    return {
        "ok": False,
        "data": None,
        "error_kind": error_kind,
        "error": details,
    }


def _client_from_creds(creds: Dict[str, str]):
    client_id = str(creds.get("client_id") or "").strip()
    access_token = str(creds.get("access_token") or "").strip()
    if not client_id or not access_token:
        raise ValueError("Missing Dhan credentials")
    return _get_client(client_id, access_token)


def sdk_quote_data(creds: Dict[str, str], securities: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = _client_from_creds(creds)
        response = client.quote_data(securities)
        return _parse_sdk_response(response)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


def sdk_ltp_data(creds: Dict[str, str], securities: Dict[str, Any]) -> Dict[str, Any]:
    """Call DhanHQ Market Quote LTP endpoint (/v2/marketfeed/ltp).

    Docs: https://dhanhq.co/docs/v2/market-quote/#ticker-data
    """
    try:
        client_id = str(creds.get("client_id") or "").strip()
        access_token = str(creds.get("access_token") or "").strip()
        if not client_id or not access_token:
            raise ValueError("Missing Dhan credentials")

        url = "https://api.dhan.co/v2/marketfeed/ltp"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": access_token,
            "client-id": client_id,
        }
        response = requests.post(url, headers=headers, json=securities or {}, timeout=15)
        response.raise_for_status()
        return _parse_sdk_response(response.json())
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


def sdk_expiry_list(creds: Dict[str, str], under_security_id: int, under_exchange_segment: str) -> Dict[str, Any]:
    try:
        client = _client_from_creds(creds)
        response = client.expiry_list(int(under_security_id), str(under_exchange_segment))
        return _parse_sdk_response(response)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


def sdk_option_chain(
    creds: Dict[str, str],
    under_security_id: int,
    under_exchange_segment: str,
    expiry: str,
) -> Dict[str, Any]:
    try:
        client = _client_from_creds(creds)
        response = client.option_chain(int(under_security_id), str(under_exchange_segment), str(expiry))
        return _parse_sdk_response(response)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


def sdk_margin_calculator(
    creds: Dict[str, str],
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    product_type: str,
    price: float,
    trigger_price: float = 0,
) -> Dict[str, Any]:
    try:
        client = _client_from_creds(creds)
        response = client.margin_calculator(
            security_id=str(security_id),
            exchange_segment=str(exchange_segment),
            transaction_type=str(transaction_type),
            quantity=int(quantity),
            product_type=str(product_type),
            price=float(price),
            trigger_price=float(trigger_price),
        )
        return _parse_sdk_response(response)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


async def sdk_quote_data_async(creds: Dict[str, str], securities: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(sdk_quote_data, creds, securities)


async def sdk_expiry_list_async(
    creds: Dict[str, str],
    under_security_id: int,
    under_exchange_segment: str,
) -> Dict[str, Any]:
    return await asyncio.to_thread(sdk_expiry_list, creds, under_security_id, under_exchange_segment)


async def sdk_option_chain_async(
    creds: Dict[str, str],
    under_security_id: int,
    under_exchange_segment: str,
    expiry: str,
) -> Dict[str, Any]:
    return await asyncio.to_thread(sdk_option_chain, creds, under_security_id, under_exchange_segment, expiry)


async def sdk_margin_calculator_async(
    creds: Dict[str, str],
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    product_type: str,
    price: float,
    trigger_price: float = 0,
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        sdk_margin_calculator,
        creds,
        security_id,
        exchange_segment,
        transaction_type,
        quantity,
        product_type,
        price,
        trigger_price,
    )


def sdk_get_fund_limits(creds: Dict[str, str]) -> Dict[str, Any]:
    try:
        client = _client_from_creds(creds)
        response = client.get_fund_limits()
        return _parse_sdk_response(response)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error_kind": "other",
            "error": str(exc),
        }


async def sdk_get_fund_limits_async(creds: Dict[str, str]) -> Dict[str, Any]:
    return await asyncio.to_thread(sdk_get_fund_limits, creds)