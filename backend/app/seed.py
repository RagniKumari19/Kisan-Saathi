"""Idempotent seed loader.

Reference data is inserted once by slug. Demo market prices are generated
deterministically for the last 30 days and flagged ``is_mock=True`` so the API
can label them honestly all the way to the UI.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import utcnow
from app.core.security import hash_password
from app.models import (
    Commodity,
    Crop,
    CropPlan,
    District,
    Disease,
    Farm,
    MandiPrice,
    Market,
    MspRate,
    PlanActivity,
    Treatment,
    User,
)
from app import seed_data as sd
from app.services.calendar import estimate_harvest, generate_activities, stage_for_day


def _hash01(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


async def _exists(db: AsyncSession, model, **filters) -> bool:
    stmt = select(func.count()).select_from(model)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model, k) == v)
    return (await db.scalar(stmt) or 0) > 0



async def seed_reference(db: AsyncSession) -> None:
    if not await _exists(db, District):
        db.add_all([District(**d) for d in sd.DISTRICTS])
        await db.flush()
    if not await _exists(db, Crop):
        for c in sd.CROPS:
            data = dict(c)
            db.add(Crop(
                slug=data["slug"], name_en=data["name_en"], name_hi=data["name_hi"],
                scientific_name=data.get("scientific_name"), category=data["category"],
                season=data["season"], duration_days=data.get("duration_days"),
                water_need=data["water_need"], ideal_ph_min=data["ideal_ph_min"],
                ideal_ph_max=data["ideal_ph_max"], n_target=data["n_target"],
                p_target=data["p_target"], k_target=data["k_target"], zones=data["zones"],
                description_en=data["description_en"], description_hi=data["description_hi"],
            ))
    if not await _exists(db, Disease):
        for d in sd.DISEASES:
            db.add(Disease(
                slug=d["slug"], crop_slug=d["crop_slug"], name_en=d["name_en"], name_hi=d["name_hi"],
                pathogen_type=d["pathogen_type"], symptoms_en=d["symptoms_en"],
                symptoms_hi=d["symptoms_hi"], spread_en=d["spread_en"],
                severity_default=d["severity_default"], risk_humidity_min=d.get("risk_humidity_min"),
                risk_temp_min=d.get("risk_temp_min"), risk_temp_max=d.get("risk_temp_max"),
            ))
            for t in d["treatments"]:
                db.add(Treatment(
                    disease_slug=d["slug"], kind=t["kind"], title=t["title"], detail=t["detail"],
                    dosage=t.get("dosage"), safety_notes=t.get("safety_notes"),
                    source_url=t["source_url"], last_verified=date(2026, 10, 20),
                    display_order=t["order"],
                ))
    if not await _exists(db, Commodity):
        db.add_all([
            Commodity(slug=c["slug"], name_en=c["name_en"], name_hi=c["name_hi"],
                      category=c["category"], aliases=c["aliases"])
            for c in sd.COMMODITIES
        ])
    await db.flush()

    if not await _exists(db, Market):
        districts = {d.slug: d for d in (await db.execute(select(District))).scalars()}
        for m in sd.MARKETS:
            d = districts[m["district"]]
            db.add(Market(
                district_id=d.id, name=m["name"],
                slug=f"{m['district']}/{m['name'].lower().replace(' ', '-').replace('(', '').replace(')', '')}",
                latitude=m["lat"], longitude=m["lon"],
            ))
        await db.flush()

    if not await _exists(db, MspRate):
        for m in sd.MSP_RATES:
            db.add(MspRate(
                commodity=m["commodity"], season=m["season"], marketing_year=m["marketing_year"],
                price_per_quintal=m["price"], source_url=sd.MSP_SOURCE,
                published_on=date(2025, 6, 18), last_verified=date(2026, 10, 20),
            ))
    await db.commit()


def _price_for(commodity: str, base: int, market: str, day_index: int) -> tuple[float, float, float]:
    season = 1 + 0.10 * __import__("math").sin((day_index + len(market)) / 6.0)
    noise = (_hash01(f"{commodity}:{market}:{day_index}") - 0.5) * 0.12
    market_factor = 0.94 + _hash01(f"{market}:{commodity}") * 0.14
    modal = base * season * market_factor * (1 + noise)
    spread = modal * (0.12 + _hash01(f"spread:{commodity}:{day_index}") * 0.10)
    return round(modal - spread, 2), round(modal + spread, 2), round(modal, 2)


async def seed_prices(db: AsyncSession) -> None:
    if await _exists(db, MandiPrice):
        return
    markets = (await db.execute(select(Market))).scalars().all()
    today = date.today()
    rows: list[MandiPrice] = []
    # Only commodities a mandi plausibly trades are generated; every row carries
    # a date so sparse reporting is visible rather than hidden.
    for m in markets:
        for commodity, base in sd.BASE_PRICES.items():
            for back in range(30):
                day = today - timedelta(days=back)
                key = f"skip:{m.id}:{commodity}:{day.isoformat()}"
                if _hash01(key) < 0.18:  # not every mandi reports every day
                    continue
                lo, hi, modal = _price_for(commodity, base, m.name, back)
                rows.append(MandiPrice(
                    market_id=m.id, commodity=commodity,
                    variety="Local" if commodity in {"onion", "tomato"} else "Other",
                    grade="FAQ", arrival_date=day,
                    min_price=lo, max_price=hi, modal_price=modal,
                    unit="quintal", source="demo_seed", is_mock=True,
                    ingested_at=utcnow(),
                ))
        await db.flush()
    db.add_all(rows)
    await db.commit()



async def seed_all(db: AsyncSession) -> None:
    await seed_reference(db)
    # No demo accounts, farms or plans are seeded; only genuine registrations create users.
    if settings.allow_mock_data:
        await seed_prices(db)
