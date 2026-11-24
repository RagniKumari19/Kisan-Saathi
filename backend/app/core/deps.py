"""Authentication dependencies and role gates."""
from __future__ import annotations

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AuthRequired, Forbidden, TokenExpired
from app.core.security import decode_access_token
from app.models import User


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise AuthRequired("Sign in to continue.")
    token = header.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired("Your session expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthRequired("Your session is not valid. Please sign in again.") from exc

    user_id = payload.get("sub")
    user = await db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AuthRequired("Your account is not available. Please sign in again.")
    request.state.user = user
    return user


async def optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        payload = decode_access_token(header.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    user = await db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    return user


def require_role(*roles: str):
    async def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise Forbidden("You do not have permission to do that.")
        return user

    return guard
