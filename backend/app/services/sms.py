"""SMS adapter for OTP delivery.

A real message is sent only when ``SMS_PROVIDER`` names an Indian DLT-registered
gateway and an API key is present. The ``dev`` provider sends nothing; the API
returns the code outside production so the flow stays testable. Codes are never
logged, and gateway error bodies are not surfaced because they can echo them.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.core.errors import SmsUnavailable, UpstreamUnavailable

log = logging.getLogger("app.sms")


def provider() -> str:
    return settings.sms_provider.strip().lower()


async def send_otp(phone: str, code: str) -> None:
    name = provider()
    if name in {"", "dev", "console"}:
        return
    if not settings.sms_api_key:
        raise SmsUnavailable("SMS verification is not configured on this server.")
    if name == "msg91":
        await _msg91(phone, code)
        return
    if name == "fast2sms":
        await _fast2sms(phone, code)
        return
    if name == "twilio":
        await _twilio(phone, code)
        return
    raise SmsUnavailable(f"Unknown SMS provider '{name}'.")


async def _post(url: str, *, headers: dict, params: dict | None = None, json: dict | None = None) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, params=params, json=json)
    except httpx.HTTPError as exc:
        log.warning("sms gateway request failed: %s", type(exc).__name__)
        raise UpstreamUnavailable("The SMS gateway could not be reached. Try again.") from exc
    if response.status_code >= 400:
        log.warning("sms gateway rejected the request with status %s", response.status_code)
        raise UpstreamUnavailable("The SMS gateway rejected the message. Try again later.")


async def _msg91(phone: str, code: str) -> None:
    """MSG91 OTP API (v5). Requires a DLT-approved template id."""
    if not settings.sms_template_id:
        raise SmsUnavailable("SMS_TEMPLATE_ID is required for MSG91.")
    params = {
        "template_id": settings.sms_template_id,
        "mobile": phone.lstrip("+"),
        "otp": code,
    }
    if settings.sms_sender_id:
        params["sender"] = settings.sms_sender_id
    await _post(
        "https://control.msg91.com/api/v5/otp",
        headers={"authkey": settings.sms_api_key},
        params=params,
    )


async def _fast2sms(phone: str, code: str) -> None:
    """Fast2SMS OTP route for Indian numbers."""
    payload = {"route": "otp", "variables_values": code, "numbers": phone[-10:]}
    if settings.sms_sender_id:
        payload["sender_id"] = settings.sms_sender_id
    await _post(
        "https://www.fast2sms.com/dev/bulkV2",
        headers={"authorization": settings.sms_api_key},
        json=payload,
    )


async def _twilio(phone: str, code: str) -> None:
    """Twilio SMS API."""
    from app.core.config import settings as s

    url = f"https://api.twilio.com/2010-04-01/Accounts/{s.sms_account_sid}/Messages.json"
    body = f"Your verification code is {code}. It expires in 5 minutes."
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                data={"To": phone, "From": s.sms_from_number, "Body": body},
                auth=(s.sms_account_sid, s.sms_auth_token),
            )
    except httpx.HTTPError as exc:
        log.warning("sms gateway request failed: %s", type(exc).__name__)
        raise UpstreamUnavailable("The SMS gateway could not be reached. Try again.") from exc
    if response.status_code >= 400:
        log.warning("sms gateway rejected the request with status %s", response.status_code)
        raise UpstreamUnavailable("The SMS gateway rejected the message. Try again later.")
