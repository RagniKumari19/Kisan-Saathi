from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db
from app.core.deps import current_user, require_role
from app.core.errors import Conflict, NotFound, ValidationError
from app.core.utils import data, page
from app.models import District, Farm, User
from app.schemas import FarmIn, FarmPatch, ProfileIn, RoleIn
from app.serializers import farm_out, user_out

router = APIRouter(tags=["users"])
MAX_FARMS = 10


async def _farm_with_district(db: AsyncSession, farm: Farm) -> dict:
    d = await db.get(District, farm.district_id)
    return farm_out(farm, d)


async def owned_farm(db: AsyncSession, user: User, farm_id: str) -> Farm:
    farm = await db.get(Farm, farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    return farm


@router.get("/users/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farms = (await db.execute(select(Farm).where(Farm.user_id == user.id).order_by(Farm.created_at))).scalars().all()
    primary = next((f for f in farms if f.is_primary), farms[0] if farms else None)
    payload = user_out(user)
    payload["primary_farm"] = await _farm_with_district(db, primary) if primary else None
    payload["farm_count"] = len(farms)
    return data(payload)


@router.patch("/users/me")
async def update_me(body: ProfileIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.language is not None:
        user.language = body.language
    await db.commit()
    await db.refresh(user)
    return data(user_out(user))


@router.get("/users/me/farms")
async def list_farms(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Farm, District).join(District, District.id == Farm.district_id)
        .where(Farm.user_id == user.id).order_by(Farm.is_primary.desc(), Farm.created_at)
    )).all()
    return data([farm_out(f, d) for f, d in rows])


@router.post("/users/me/farms", status_code=201)
async def create_farm(body: FarmIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    count = (await db.execute(select(func.count()).select_from(Farm).where(Farm.user_id == user.id))).scalar() or 0
    if count >= MAX_FARMS:
        raise Conflict(f"You can save up to {MAX_FARMS} farms. Remove one before adding another.")

    district = None
    if body.district_id:
        district = await db.get(District, body.district_id)
    elif body.district_slug:
        district = (await db.execute(select(District).where(District.slug == body.district_slug))).scalar_one_or_none()
    if district is None:
        raise ValidationError("Choose a district.", [{"field": "district_id", "issue": "District not found."}])

    is_first = count == 0
    farm = Farm(
        user_id=user.id, name=body.name.strip(), district_id=district.id, village=body.village,
        latitude=body.latitude, longitude=body.longitude, area_acres=body.area_acres,
        soil_type=body.soil_type, irrigation_source=body.irrigation_source,
        primary_crop_slug=body.primary_crop_slug, is_primary=is_first or body.is_primary,
    )
    if farm.is_primary:
        for other in (await db.execute(select(Farm).where(Farm.user_id == user.id))).scalars():
            other.is_primary = False
    db.add(farm)
    await audit(db, user.id, "farm.create", "farm", farm.id, {"name": farm.name})
    await db.commit()
    await db.refresh(farm)
    return data(farm_out(farm, district))


@router.get("/users/me/farms/{farm_id}")
async def get_farm(farm_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm = await owned_farm(db, user, farm_id)
    return data(await _farm_with_district(db, farm))


@router.patch("/users/me/farms/{farm_id}")
async def patch_farm(farm_id: str, body: FarmPatch, user: User = Depends(current_user),
                     db: AsyncSession = Depends(get_db)):
    farm = await owned_farm(db, user, farm_id)
    for field in ("name", "village", "latitude", "longitude", "area_acres", "soil_type",
                  "irrigation_source", "primary_crop_slug"):
        value = getattr(body, field)
        if value is not None:
            setattr(farm, field, value)
    await db.commit()
    await db.refresh(farm)
    return data(await _farm_with_district(db, farm))


@router.delete("/users/me/farms/{farm_id}")
async def delete_farm(farm_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm = await owned_farm(db, user, farm_id)
    count = (await db.execute(select(func.count()).select_from(Farm).where(Farm.user_id == user.id))).scalar() or 0
    if count <= 1:
        raise Conflict("This is your only farm. Add another farm before removing it.")
    was_primary = farm.is_primary
    await db.delete(farm)
    await db.flush()
    if was_primary:
        remaining = (await db.execute(
            select(Farm).where(Farm.user_id == user.id).order_by(Farm.created_at)
        )).scalars().first()
        if remaining:
            remaining.is_primary = True
    await audit(db, user.id, "farm.delete", "farm", farm_id)
    await db.commit()
    return data({"ok": True})


@router.post("/users/me/farms/{farm_id}/primary")
async def make_primary(farm_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm = await owned_farm(db, user, farm_id)
    for other in (await db.execute(select(Farm).where(Farm.user_id == user.id))).scalars():
        other.is_primary = other.id == farm.id
    await db.commit()
    await db.refresh(farm)
    return data(await _farm_with_district(db, farm))


@router.get("/users")
async def admin_list_users(
    role: str | None = None, q: str | None = None,
    page_no: int = Query(1, ge=1, alias="page"), limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if q:
        like = f"%{q.strip()}%"
        cond = or_(User.phone.ilike(like), User.full_name.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page_no - 1) * limit).limit(limit)
    )).scalars().all()
    return page([user_out(u) for u in rows], page_no, limit, total)


@router.patch("/users/{user_id}/role")
async def admin_set_role(user_id: str, body: RoleIn, request: Request,
                         admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if target is None:
        raise NotFound("User not found.")
    previous = target.role
    target.role = body.role
    await audit(db, admin.id, "user.role_change", "user", target.id,
                {"from": previous, "to": body.role},
                request.client.host if request.client else None)
    await db.commit()
    return data(user_out(target))
