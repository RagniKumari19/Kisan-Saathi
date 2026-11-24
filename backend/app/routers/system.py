from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.utils import data, iso, iso_date
from app.models import Commodity, Crop, Detection, District, MandiPrice, WeatherSnapshot
from app.serializers import district_out

router = APIRouter(tags=["system"])


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(func.count()).select_from(District))
    except Exception:
        return {"status": "not_ready", "database": "unavailable"}
    return {"status": "ready", "database": "ok"}


@router.get("/districts")
async def districts(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(District).order_by(District.state, District.name))).scalars().all()
    return data([district_out(d) for d in rows])


@router.get("/commodities")
async def commodities(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Commodity).order_by(Commodity.name_en))).scalars().all()
    return data([
        {"slug": c.slug, "name_en": c.name_en, "name_hi": c.name_hi, "category": c.category}
        for c in rows
    ])


@router.get("/meta")
async def meta(db: AsyncSession = Depends(get_db)):
    latest_price = (await db.execute(select(func.max(MandiPrice.arrival_date)))).scalar()
    weather_snap = (await db.execute(
        select(WeatherSnapshot).order_by(WeatherSnapshot.fetched_at.desc())
    )).scalars().first()
    crops = (await db.execute(select(func.count()).select_from(Crop))).scalar() or 0
    detections = (await db.execute(select(func.count()).select_from(Detection))).scalar() or 0
    return data({
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "model_versions": {
            "disease": "heuristic-v0",
            "crop_rec": "croprec-rules-v1",
            "soil": "soil-rules-v1",
        },
        "data_freshness": {
            "agmarknet": iso_date(latest_price),
            "weather_cache": iso(weather_snap.fetched_at) if weather_snap else None,
        },
        "features": {
            "voice": False,
            "sms": settings.sms_configured,
            "sms_provider": settings.sms_provider,
            "otp_login": True,
            "expert_review": True,
            "live_weather": bool(settings.openweather_api_key),
            "live_mandi_prices": False,
        },
        "provenance": {
            "weather_is_mock": not bool(settings.openweather_api_key),
            "mandi_prices_are_mock": True,
            "disease_model_is_mock": True,
            "crop_model": "deterministic rules, not trained ML",
        },
        "counts": {"crops": crops, "detections": detections},
        "limitations": [
            "Mandi prices are demo fixtures labelled is_mock; no live AGMARKNET feed is connected.",
            "Disease detection is a demonstration heuristic, not a trained image model.",
            "Crop recommendations use a transparent rules engine, not a trained yield model.",
        ],
    })
