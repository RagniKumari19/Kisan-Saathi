from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import settings
from app.core.db import get_db, utcnow
from app.core.deps import current_user, optional_user
from app.core.errors import (
    AuthRequired, Conflict, InvalidCredentials, RefreshReused, TokenExpired, ValidationError,
)
from app.core.security import (
    create_access_token, hash_password, hash_refresh_token, new_refresh_token,
    refresh_expiry, verify_password,
)
from app.core.utils import data, normalise_phone
from app.models import OtpChallenge, RefreshToken, User
from app.schemas import LoginIn, LogoutIn, OtpRequestIn, OtpVerifyIn, PasswordChangeIn, RefreshIn, RegisterIn
from app.serializers import user_out
from app.services import otp as otp_service

router = APIRouter(prefix="/auth", tags=["auth"])

COMMON_PASSWORDS = {"password", "password1", "12345678", "qwerty123", "india123", "farmer1234"}


async def issue_tokens(db: AsyncSession, user: User, request: Request) -> dict:
    access, expires_in = create_access_token(user.id, user.role, user.language)
    raw_refresh = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_expiry(), user_agent=(request.headers.get("user-agent") or "")[:255],
    ))
    await db.flush()
    return {
        "access_token": access, "refresh_token": raw_refresh,
        "token_type": "bearer", "expires_in": expires_in,
        "refresh_expires_in": int((refresh_expiry() - utcnow()).total_seconds()),
    }


@router.post("/register", status_code=201)
async def register(body: RegisterIn, request: Request, db: AsyncSession = Depends(get_db)):
    phone = normalise_phone(body.phone)
    if body.password.lower() in COMMON_PASSWORDS or body.password == phone:
        raise ValidationError(
            "Choose a stronger password.",
            [{"field": "password", "issue": "This password is too common or matches your phone number."}],
        )
    existing = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if existing:
        raise Conflict("An account with this phone number already exists. Try signing in.")
    user = User(
        phone=phone, password_hash=hash_password(body.password),
        full_name=body.full_name.strip(), language=body.language, role="farmer",
    )
    db.add(user)
    await db.flush()
    tokens = await issue_tokens(db, user, request)
    await audit(db, user.id, "auth.register", "user", user.id, {"role": "farmer"},
                request.client.host if request.client else None)
    await db.commit()
    await db.refresh(user)
    return data({"user": user_out(user), "tokens": tokens})


@router.post("/login")
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    phone = normalise_phone(body.phone)
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise InvalidCredentials("Phone number or password is incorrect.")
    if not user.is_active or user.deleted_at is not None:
        raise InvalidCredentials("This account is not active. Contact support.")
    user.last_login_at = utcnow()
    tokens = await issue_tokens(db, user, request)
    await audit(db, user.id, "auth.login", "user", user.id, None,
                request.client.host if request.client else None)
    await db.commit()
    await db.refresh(user)
    return data({"user": user_out(user), "tokens": tokens})


@router.post("/refresh")
async def refresh(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalar_one_or_none()
    if row is None:
        raise AuthRequired("Session not recognised. Please sign in again.")
    if row.revoked_at is not None:
        await db.execute(
            update(RefreshToken).where(RefreshToken.user_id == row.user_id).values(revoked_at=utcnow())
        )
        await db.commit()
        raise RefreshReused("This session was already used. All sessions have been signed out for safety.")
    if row.expires_at < utcnow():
        raise TokenExpired("Your session expired. Please sign in again.")
    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthRequired("This account is not active.")

    access, expires_in = create_access_token(user.id, user.role, user.language)
    raw = new_refresh_token()
    new_row = RefreshToken(
        user_id=user.id, token_hash=hash_refresh_token(raw), expires_at=refresh_expiry(),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(new_row)
    await db.flush()
    row.revoked_at = utcnow()
    row.replaced_by_id = new_row.id
    await db.commit()
    return data({"tokens": {
        "access_token": access, "refresh_token": raw, "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_expires_in": int((new_row.expires_at - utcnow()).total_seconds()),
    }})


@router.post("/logout")
async def logout(body: LogoutIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.refresh_token:
        row = (await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
        )).scalar_one_or_none()
        if row and row.user_id == user.id and row.revoked_at is None:
            row.revoked_at = utcnow()
    await audit(db, user.id, "auth.logout", "user", user.id)
    await db.commit()
    return data({"ok": True})


@router.patch("/password")
async def change_password(body: PasswordChangeIn, user: User = Depends(current_user),
                          db: AsyncSession = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise InvalidCredentials("Current password is incorrect.")
    if body.new_password.lower() in COMMON_PASSWORDS:
        raise ValidationError("Choose a stronger password.", [{"field": "new_password", "issue": "Too common."}])
    user.password_hash = hash_password(body.new_password)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    await audit(db, user.id, "auth.password_change", "user", user.id)
    await db.commit()
    return data({"ok": True, "message": "Password updated. Please sign in again on other devices."})


@router.post("/otp/request", status_code=201)
async def otp_request(body: OtpRequestIn, request: Request,
                      user: User | None = Depends(optional_user),
                      db: AsyncSession = Depends(get_db)):
    # An authenticated user may never redirect an OTP to an arbitrary number:
    # the challenge always goes to their registered phone.
    raw_phone = user.phone if user is not None else body.phone
    challenge, channel = await otp_service.request_otp(
        db,
        raw_phone=raw_phone,
        purpose=body.purpose,
        ip=request.client.host if request.client else None,
        payload={
            "full_name": (body.full_name or "").strip(),
            "language": body.language,
        },
    )
    await audit(db, None, "auth.otp_request", "otp_challenge", challenge.id,
                {"purpose": body.purpose, "channel": channel})
    await db.commit()

    payload = {
        "request_id": challenge.id,
        "phone": challenge.phone,
        "purpose": challenge.purpose,
        "expires_in": settings.otp_ttl_seconds,
        "resend_after": settings.otp_resend_seconds,
        "attempts_allowed": challenge.max_attempts,
        "channel": channel,
    }
    return data(payload)


@router.post("/otp/verify")
async def otp_verify(body: OtpVerifyIn, request: Request, db: AsyncSession = Depends(get_db)):
    challenge: OtpChallenge = await otp_service.verify_otp(
        db, request_id=body.request_id, code=body.code
    )
    user = (await db.execute(select(User).where(User.phone == challenge.phone))).scalar_one_or_none()

    if user is None:
        if challenge.purpose != "signup":
            raise InvalidCredentials("This number is not registered. Create an account first.")
        full_name = str((challenge.payload or {}).get("full_name") or "").strip()
        language = str((challenge.payload or {}).get("language") or "en")
        user = User(
            phone=challenge.phone,
            password_hash=None,
            full_name=full_name or None,
            language=language if language in {"en", "hi", "mr"} else "en",
            role="farmer",
            phone_verified_at=utcnow(),
        )
        db.add(user)
        await db.flush()
        await audit(db, user.id, "auth.register_otp", "user", user.id, {"role": "farmer"})
    else:
        if not user.is_active or user.deleted_at is not None:
            raise InvalidCredentials("This account is not active. Contact support.")
        if user.phone_verified_at is None:
            user.phone_verified_at = utcnow()

    user.last_login_at = utcnow()
    tokens = await issue_tokens(db, user, request)
    await audit(db, user.id, "auth.login_otp", "user", user.id, {"purpose": challenge.purpose})
    await db.commit()
    await db.refresh(user)
    return data({"user": user_out(user), "tokens": tokens})
