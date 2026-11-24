from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_user
from app.core.errors import NotFound
from app.core.utils import data
from app.models import Crop, CropRecommendation, Disease, District, Farm, SoilReport, Treatment, User
from app.schemas import RecommendIn
from app.serializers import crop_out, disease_out
from app.services.crops import MODEL_VERSION, recommend
from app.services.weather import get_weather

router = APIRouter(prefix="/crops", tags=["crops"])

DISCLAIMER = (
    "Suggestion based on your soil values, forecast and published crop requirements. "
    "It is not a guarantee of yield. Confirm with your agriculture officer."
)


@router.get("")
async def list_crops(season: str | None = None, zone: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Crop).where(Crop.is_active.is_(True)).order_by(Crop.name_en)
    if season:
        stmt = stmt.where(Crop.season == season)
    rows = (await db.execute(stmt)).scalars().all()
    if zone:
        rows = [c for c in rows if zone in (c.zones or [])]
    return data([crop_out(c) for c in rows])


@router.get("/recommendations")
async def list_recommendations(farm_id: str | None = None, limit: int = Query(10, ge=1, le=50),
                               user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(CropRecommendation).where(CropRecommendation.user_id == user.id)
    if farm_id:
        stmt = stmt.where(CropRecommendation.farm_id == farm_id)
    rows = (await db.execute(stmt.order_by(CropRecommendation.created_at.desc()).limit(limit))).scalars().all()
    return data([_stored_out(r) for r in rows])


@router.get("/recommendations/{rec_id}")
async def get_recommendation(rec_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(CropRecommendation, rec_id)
    if row is None or row.user_id != user.id:
        raise NotFound("Recommendation not found.")
    return data(_stored_out(row))


def _stored_out(r: CropRecommendation) -> dict:
    return {
        "id": r.id, "farm_id": r.farm_id, "season": r.season,
        "model_version": r.model_version,
        "input_features": r.input_features,
        "results": r.results, "suppressed": r.suppressed,
        "created_at": r.created_at.replace(microsecond=0).isoformat() + "Z" if r.created_at else None,
        "provenance": {
            "source": "rules_engine", "model_version": r.model_version,
            "training_data": None, "is_mock": False, "stale": False,
        },
        "disclaimer": DISCLAIMER,
    }


@router.get("/{slug}")
async def crop_detail(slug: str, db: AsyncSession = Depends(get_db)):
    crop = (await db.execute(select(Crop).where(Crop.slug == slug))).scalar_one_or_none()
    if crop is None:
        raise NotFound("Crop not found.")
    payload = crop_out(crop)
    diseases = (await db.execute(
        select(Disease).where(Disease.crop_slug == slug, Disease.is_active.is_(True)).order_by(Disease.name_en)
    )).scalars().all()
    items = []
    for d in diseases:
        treatments = (await db.execute(
            select(Treatment).where(Treatment.disease_slug == d.slug).order_by(Treatment.display_order)
        )).scalars().all()
        items.append(disease_out(d, crop, [
            {
                "kind": t.kind, "title": t.title, "detail": t.detail, "dosage": t.dosage,
                "safety_notes": t.safety_notes, "source_url": t.source_url,
                "last_verified": t.last_verified.isoformat() if t.last_verified else None,
            } for t in treatments
        ]))
    payload["diseases"] = items
    return data(payload)


@router.post("/recommend", status_code=201)
async def recommend_crops(body: RecommendIn, user: User = Depends(current_user),
                          db: AsyncSession = Depends(get_db)):
    farm = await db.get(Farm, body.farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    district = await db.get(District, farm.district_id)
    if district is None:
        raise NotFound("District not found for this farm.")

    report = (await db.execute(
        select(SoilReport).where(SoilReport.farm_id == farm.id).order_by(SoilReport.created_at.desc())
    )).scalars().first()
    bundle = await get_weather(db, farm, district)
    rain_mm = round(sum(d["rain_mm"] for d in bundle["daily"]), 1)

    crops = (await db.execute(select(Crop).where(Crop.is_active.is_(True)))).scalars().all()
    result = recommend(crops, farm, district, report, body.season, rain_mm)

    features = {
        "soil_report_id": report.id if report else None,
        "soil_source": result["input_provenance"]["soil_source"],
        "season": body.season,
        "agro_zone": district.agro_zone,
        "irrigation_source": farm.irrigation_source,
        "rainfall_mm_6d": rain_mm,
        "rainfall_source": "forecast_6d",
        "missing_fields": result["input_provenance"]["missing_fields"],
    }
    row = CropRecommendation(
        user_id=user.id, farm_id=farm.id, season=body.season,
        input_features=features, model_version=MODEL_VERSION,
        results=result["results"], suppressed=result["suppressed"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    payload = {
        "id": row.id,
        "farm_id": farm.id,
        "season": body.season,
        "model_version": MODEL_VERSION,
        "input_features": features,
        "results": result["results"],
        "suppressed": result["suppressed"],
        "input_provenance": result["input_provenance"],
        "provenance": {
            "source": "rules_engine", "model_version": MODEL_VERSION,
            "training_data": None, "is_mock": False, "stale": False,
            "method": result["model"]["method"],
            "weather_is_mock": bundle["provenance"]["is_mock"],
        },
        "disclaimer": DISCLAIMER,
        "created_at": row.created_at.replace(microsecond=0).isoformat() + "Z",
    }
    if not result["results"]:
        payload["explanation"] = (
            "No crop passed the agro-zone and season rules for this farm. "
            "Check the suppressed list, or change the season."
        )
    return data(payload)
