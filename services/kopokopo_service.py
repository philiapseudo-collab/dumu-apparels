"""
Kopo Kopo v1 API integration (K2) for M-PESA STK Push.

Implements:
- OAuth token exchange (client_credentials) via POST /oauth/token
- Incoming payments (STK Push) via POST /api/v1/incoming_payments
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class _TokenCache:
    access_token: str
    expires_at_epoch: float  # epoch seconds


class KopoKopoService:
    """
    Minimal Kopo Kopo v1 client for STK Push.
    """

    def __init__(self) -> None:
        self._token_cache: Optional[_TokenCache] = None

    async def _get_access_token(self) -> str:
        """
        Fetch an OAuth access token using client credentials.

        Endpoint: POST {KOPOKOPO_BASE_URL}/oauth/token
        Payload: client_id, client_secret, grant_type=client_credentials
        """
        settings = get_settings()

        # Simple in-memory cache (safe enough for single-instance demo use)
        if self._token_cache and time.time() < self._token_cache.expires_at_epoch:
            return self._token_cache.access_token

        url = f"{settings.kopokopo_base_url.rstrip('/')}/oauth/token"

        payload = {
            "client_id": settings.kopokopo_client_id,
            "client_secret": settings.kopokopo_client_secret,
            "grant_type": "client_credentials",
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)

        # Log full response for debugging (as requested), but do NOT log secrets.
        logger.info(
            "KopoKopo OAuth response: status=%s body=%s",
            resp.status_code,
            resp.text,
        )

        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"KopoKopo OAuth response missing access_token: {data}")

        expires_in = data.get("expires_in")
        try:
            expires_in_seconds = int(expires_in) if expires_in is not None else 3600
        except Exception:
            expires_in_seconds = 3600

        # Refresh a bit early to avoid edge expiry during requests.
        self._token_cache = _TokenCache(
            access_token=token,
            expires_at_epoch=time.time() + max(30, expires_in_seconds - 30),
        )
        return token

    async def initiate_stk_push(
        self,
        phone_number: str,
        amount: float,
        first_name: str,
        last_name: str,
        email: str,
        reference: str,
    ) -> Dict[str, Any]:
        """
        Initiate an M-PESA STK Push via Kopo Kopo v1.

        Endpoint: POST {KOPOKOPO_BASE_URL}/api/v1/incoming_payments
        Headers: Authorization: Bearer {token}, Accept: application/json
        """
        settings = get_settings()
        token = await self._get_access_token()

        url = f"{settings.kopokopo_base_url.rstrip('/')}/api/v1/incoming_payments"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        body = {
            "payment_channel": "M-PESA",
            "till_number": settings.kopokopo_till_number,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "amount": amount,
            "currency": "KES",
            "email": email,
            "callback_url": f"{settings.app_url.rstrip('/')}/kopokopo/callback",
            "metadata": {"reference": reference},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers)

        # Log full response for debugging (as requested)
        logger.info(
            "KopoKopo incoming_payments response: status=%s body=%s",
            resp.status_code,
            resp.text,
        )

        resp.raise_for_status()
        return resp.json()

