"""Phone verification: code generation, keyed hashing, rate limits and attempts.

Rules enforced here (all persisted, so they survive a restart):
  * one live challenge per phone and purpose,
  * a resend cooldown, plus hourly caps per phone and per IP,
  * a 5 minute expiry and a fixed number of attempts per code,
  * single use, and a cooldown after repeated wrong codes for a number.

Only an HMAC of the code is stored. The plain code is returned to the caller
solely so the API can echo it in development mode.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import Conflict, OtpInvalid, RateLimited, SmsUnavailable, ValidationError
from app.core.utils import normalise_phone
from app.models import OtpChallenge, User
from app.services import sms

log = logging.getLogger("app.otp")

INDIAN_MOBILE = re.compile(r"^\+91[6-9]\d{9}$")
PURPOSES = {"signup", "login", "recovery"}
FAILURE_WINDOW_MINUTES = 15
FAILURE_LIMIT = 10


def normalise_mobile(raw: str) -> str:
    phone = normalise_phone(raw)
    if not INDIAN_MOBILE.match(phone):
        raise ValidationError(
            "Enter a valid 10-digit Indian mobile number.",
            [{"field": "phone", "issue": "Indian mobile numbers start with 6, 7, 8 or 9."}],
        )
    return phone


def _code_hash(code: str, phone: str, purpose: str) -> str:
    message = f"{phone}:{purpose}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def _rate_limit(message: str, retry_after: int) -> RateLimited:
    error = RateLimited(message)
    error.retry_after = retry_after  # type: ignore[attr-defined]
    return error


async def _count_since(
    db: AsyncSession, since: datetime, *, phone: str | None = None, ip: str | None = None
) -> int:
    stmt = select(func.count()).select_from(OtpChallenge).where(OtpChallenge.created_at >= since)
    if phone is not None:
        stmt = stmt.where(OtpChallenge.phone == phone)
    if ip is not None:
        stmt = stmt.where(OtpChallenge.request_ip == ip)
    return (await db.execute(stmt)).scalar() or 0


async def request_otp(
    db: AsyncSession,
    *,
    raw_phone: str,
    purpose: str,
    ip: str | None,
    payload: dict,
) -> tuple[OtpChallenge, str]:
    """Create a challenge. Returns (challenge, channel). The code is never returned to callers."""
    if purpose not in PURPOSES:
        raise ValidationError("Unknown verification purpose.")

    phone = normalise_mobile(raw_phone)
    now = utcnow()

    existing = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if purpose == "signup":
        if existing is not None:
            raise Conflict("This number is already registered. Sign in instead.")
        if not str(payload.get("full_name") or "").strip():
            raise ValidationError(
                "Enter your full name.", [{"field": "full_name", "issue": "This is required."}]
            )

    if not settings.sms_configured and settings.is_production:
        raise SmsUnavailable("SMS verification is not configured on this server.")

    last = (await db.execute(
        select(OtpChallenge).where(OtpChallenge.phone == phone)
        .order_by(OtpChallenge.created_at.desc())
    )).scalars().first()
    if last is not None:
        wait = settings.otp_resend_seconds - int((now - last.created_at).total_seconds())
        if wait > 0:
            raise _rate_limit(f"Please wait {wait} seconds before requesting another code.", wait)

    if await _count_since(db, now - timedelta(hours=1), phone=phone) >= settings.otp_max_per_hour:
        raise _rate_limit("Too many codes requested for this number. Try again later.", 900)
    if ip and await _count_since(db, now - timedelta(hours=1), ip=ip) >= settings.otp_max_per_ip_hour:
        raise _rate_limit("Too many codes requested. Try again later.", 900)

    # Any earlier live code for this phone and purpose is retired.
    await db.execute(
        update(OtpChallenge)
        .where(
            OtpChallenge.phone == phone,
            OtpChallenge.purpose == purpose,
            OtpChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        phone=phone,
        purpose=purpose,
        code_hash=_code_hash(code, phone, purpose),
        payload=payload,
        max_attempts=settings.otp_max_attempts,
        expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        request_ip=ip,
    )
    db.add(challenge)
    await db.flush()

    channel = "sms" if settings.sms_configured else "dev"
    if channel == "sms":
        await sms.send_otp(phone, code)
    elif not settings.is_production:
        # Development only: never returned to the client, only logged server-side.
        log.info("DEV OTP for %s (%s): %s", phone, purpose, code)
    return challenge, channel


async def verify_otp(db: AsyncSession, *, request_id: str, code: str) -> OtpChallenge:
    now = utcnow()
    challenge = (await db.execute(
        select(OtpChallenge).where(OtpChallenge.id == request_id)
    )).scalar_one_or_none()
    if challenge is None:
        raise OtpInvalid("This code is no longer valid. Request a new one.")
    if challenge.consumed_at is not None:
        raise OtpInvalid("This code was already used. Request a new one.")
    if challenge.expires_at <= now:
        raise OtpInvalid("This code has expired. Request a new one.")
    if challenge.attempts >= challenge.max_attempts:
        raise _rate_limit("Too many incorrect attempts. Request a new code.", settings.otp_resend_seconds)

    recent_failures = (await db.execute(
        select(func.coalesce(func.sum(OtpChallenge.attempts), 0)).where(
            OtpChallenge.phone == challenge.phone,
            OtpChallenge.created_at >= now - timedelta(minutes=FAILURE_WINDOW_MINUTES),
        )
    )).scalar() or 0
    if recent_failures >= FAILURE_LIMIT:
        raise _rate_limit("Too many incorrect attempts for this number. Try again in 15 minutes.", 900)

    supplied = code.strip()
    if not hmac.compare_digest(challenge.code_hash, _code_hash(supplied, challenge.phone, challenge.purpose)):
        challenge.attempts += 1
        await db.flush()
        remaining = challenge.max_attempts - challenge.attempts
        raise OtpInvalid(
            "That code is not correct.",
            [{
                "field": "code",
                "issue": f"{remaining} attempt(s) left." if remaining > 0 else "Request a new code.",
            }],
        )

    challenge.consumed_at = now
    await db.flush()
    return challenge
