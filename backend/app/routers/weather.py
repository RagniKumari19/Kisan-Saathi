from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_user
from app.core.errors import NotFound
from app.core.utils import data
from app.models import District, Farm, User
from app.services.weather import advisories, get_weather

router = APIRouter(prefix="/weather", tags=["weather"])

DISCLAIMER = (
    "Advisories are generated from forecast data by this app, not official government warnings. "
    "Check your local forecast before acting."
)


async def _farm_and_district(db: AsyncSession, user: User, farm_id: str) -> tuple[Farm, District]:
    farm = await db.get(Farm, farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    district = await db.get(District, farm.district_id)
    if district is None:
        raise NotFound("District not found for this farm.")
    return farm, district


@router.get("/current")
async def current(farm_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm, district = await _farm_and_district(db, user, farm_id)
    bundle = await get_weather(db, farm, district)
    return data({
        "location": bundle["location"],
        "current": bundle["current"],
        "provenance": bundle["provenance"],
        "disclaimer": DISCLAIMER,
    })


@router.get("/forecast")
async def forecast(farm_id: str, days: int = Query(5, ge=1, le=5),
                   user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm, district = await _farm_and_district(db, user, farm_id)
    bundle = await get_weather(db, farm, district)
    daily = bundle["daily"][:days]
    allowed = {d["date"] for d in daily}
    slots = [s for s in bundle["slots"] if s["at"][:10] in allowed]
    return data({
        "location": bundle["location"],
        "daily": daily,
        "slots": slots,
        "advisories": advisories(daily),
        "provenance": bundle["provenance"],
        "disclaimer": DISCLAIMER,
    })


@router.get("/advisories")
async def farm_advisories(farm_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm, district = await _farm_and_district(db, user, farm_id)
    bundle = await get_weather(db, farm, district)
    return data({
        "location": bundle["location"],
        "advisories": advisories(bundle["daily"]),
        "provenance": bundle["provenance"],
        "disclaimer": DISCLAIMER,
    })
