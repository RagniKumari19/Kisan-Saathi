from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_user
from app.core.errors import NotFound, ValidationError
from app.core.utils import data, iso_date
from app.models import Crop, Farm, SoilAnalysis, SoilReport, User
from app.schemas import SoilIn
from app.services.soil import analyze_soil

router = APIRouter(prefix="/soil", tags=["soil"])

DISCLAIMER = (
    "General guidance based on your test values and a published threshold table. "
    "Confirm doses with your local Krishi Vigyan Kendra or agriculture officer."
)


def report_out(r: SoilReport) -> dict:
    return {
        "id": r.id, "farm_id": r.farm_id, "source": r.source,
        "tested_on": iso_date(r.tested_on),
        "nitrogen_kg_ha": r.nitrogen_kg_ha, "phosphorus_kg_ha": r.phosphorus_kg_ha,
        "potassium_kg_ha": r.potassium_kg_ha, "ph": r.ph,
        "organic_carbon_pct": r.organic_carbon_pct, "ec_ds_m": r.ec_ds_m,
        "lab_name": r.lab_name, "notes": r.notes,
        "created_at": r.created_at.replace(microsecond=0).isoformat() + "Z" if r.created_at else None,
    }


def analysis_out(a: SoilAnalysis) -> dict:
    return {
        "id": a.id, "soil_report_id": a.soil_report_id, "crop_slug": a.crop_slug,
        "statuses": a.statuses,
        "summary_en": a.summary_en, "summary_hi": a.summary_hi,
        "recommendations": a.recommendations,
        "ruleset_version": a.ruleset_version,
        "disclaimer": DISCLAIMER,
        "created_at": a.created_at.replace(microsecond=0).isoformat() + "Z" if a.created_at else None,
    }


async def _farm(db: AsyncSession, user: User, farm_id: str) -> Farm:
    farm = await db.get(Farm, farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    return farm


async def _build_report(db: AsyncSession, user: User, body: SoilIn) -> SoilReport:
    await _farm(db, user, body.farm_id)
    if body.crop_slug and not (await db.execute(select(Crop).where(Crop.slug == body.crop_slug))).scalar_one_or_none():
        raise ValidationError("Unknown crop.", [{"field": "crop_slug", "issue": "Crop not in the catalogue."}])
    measured = [body.nitrogen_kg_ha, body.phosphorus_kg_ha, body.potassium_kg_ha, body.ph,
                body.organic_carbon_pct, body.ec_ds_m]
    if all(v is None for v in measured):
        raise ValidationError(
            "Enter at least one soil measurement.",
            [{"field": "ph", "issue": "A report with no measurements cannot be interpreted."}],
        )
    report = SoilReport(
        farm_id=body.farm_id, user_id=user.id, source=body.source, tested_on=body.tested_on,
        nitrogen_kg_ha=body.nitrogen_kg_ha, phosphorus_kg_ha=body.phosphorus_kg_ha,
        potassium_kg_ha=body.potassium_kg_ha, ph=body.ph,
        organic_carbon_pct=body.organic_carbon_pct, ec_ds_m=body.ec_ds_m,
        lab_name=body.lab_name, notes=body.notes,
    )
    db.add(report)
    await db.flush()
    return report


@router.post("/reports", status_code=201)
async def create_report(body: SoilIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    report = await _build_report(db, user, body)
    await db.commit()
    await db.refresh(report)
    return data(report_out(report))


@router.get("/reports")
async def list_reports(farm_id: str | None = None, limit: int = Query(20, ge=1, le=100),
                       user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(SoilReport).where(SoilReport.user_id == user.id)
    if farm_id:
        stmt = stmt.where(SoilReport.farm_id == farm_id)
    rows = (await db.execute(stmt.order_by(SoilReport.created_at.desc()).limit(limit))).scalars().all()
    return data([report_out(r) for r in rows])


@router.get("/reports/{report_id}")
async def get_report(report_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    report = await db.get(SoilReport, report_id)
    if report is None or report.user_id != user.id:
        raise NotFound("Soil report not found.")
    analysis = (await db.execute(
        select(SoilAnalysis).where(SoilAnalysis.soil_report_id == report.id)
        .order_by(SoilAnalysis.created_at.desc())
    )).scalars().first()
    payload = report_out(report)
    payload["analysis"] = analysis_out(analysis) if analysis else None
    return data(payload)


@router.post("/analyze", status_code=201)
async def analyze(body: SoilIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    report = await _build_report(db, user, body)
    crop = None
    if body.crop_slug:
        crop = (await db.execute(select(Crop).where(Crop.slug == body.crop_slug))).scalar_one_or_none()
    result = analyze_soil(report, crop)
    analysis = SoilAnalysis(
        soil_report_id=report.id, crop_slug=body.crop_slug,
        statuses=result["statuses"], summary_en=result["summary_en"], summary_hi=result["summary_hi"],
        recommendations=result["recommendations"], ruleset_version=result["ruleset_version"],
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(report)
    await db.refresh(analysis)
    analysis_payload = analysis_out(analysis)
    analysis_payload["missing_fields"] = result["missing_fields"]
    return data({
        "report_id": report.id,
        "report": report_out(report),
        "analysis": analysis_payload,
    })
