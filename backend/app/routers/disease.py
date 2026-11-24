from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import current_user, require_role
from app.core.errors import NotFound, UnsupportedMediaType, ValidationError
from app.core.utils import data, page
from app.models import Crop, Detection, Disease, District, Farm, Treatment, User
from app.schemas import ReviewIn
from app.serializers import detection_list_out, disease_out
from app.services.disease import classify, risk_alerts, serialize_detection
from app.services.weather import get_weather

router = APIRouter(prefix="/disease", tags=["disease"])


def _treatments(rows) -> list[dict]:
    return [
        {
            "kind": t.kind, "title": t.title, "detail": t.detail, "dosage": t.dosage,
            "safety_notes": t.safety_notes, "source_url": t.source_url,
            "last_verified": t.last_verified.isoformat() if t.last_verified else None,
        }
        for t in rows
    ]


async def _detection_for(db: AsyncSession, user: User, det_id: str) -> Detection:
    det = await db.get(Detection, det_id)
    if det is None:
        raise NotFound("Detection not found.")
    if det.user_id != user.id and user.role not in {"expert", "admin"}:
        raise NotFound("Detection not found.")
    return det


@router.post("/detect", status_code=201)
async def detect(
    request: Request,
    image: UploadFile = File(...),
    farm_id: str | None = Form(default=None),
    crop_slug: str | None = Form(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    content_type = (image.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise UnsupportedMediaType("Please upload a photo (JPG, PNG or WEBP).")

    farm = None
    if farm_id:
        farm = await db.get(Farm, farm_id)
        if farm is None or farm.user_id != user.id:
            raise NotFound("Farm not found.")
    if not crop_slug and farm and farm.primary_crop_slug:
        crop_slug = farm.primary_crop_slug
    if crop_slug and not (await db.execute(select(Crop).where(Crop.slug == crop_slug))).scalar_one_or_none():
        raise ValidationError("Unknown crop.", [{"field": "crop_slug", "issue": "Crop not found."}])

    raw = await image.read()
    detection, payload = await classify(db, user.id, raw, crop_slug)
    if farm:
        detection.farm_id = farm.id
        await db.commit()
        await db.refresh(detection)
    await audit(db, user.id, "disease.detect", "detection", detection.id,
                {"status": detection.status, "confidence": detection.confidence},
                request.client.host if request.client else None)
    await db.commit()
    return data(payload)


@router.get("/detections")
async def history(
    farm_id: str | None = None, crop_slug: str | None = None,
    page_no: int = Query(1, ge=1, alias="page"), limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db),
):
    stmt = select(Detection).where(Detection.user_id == user.id)
    count_stmt = select(func.count()).select_from(Detection).where(Detection.user_id == user.id)
    if farm_id:
        stmt = stmt.where(Detection.farm_id == farm_id)
        count_stmt = count_stmt.where(Detection.farm_id == farm_id)
    if crop_slug:
        stmt = stmt.where(Detection.crop_slug == crop_slug)
        count_stmt = count_stmt.where(Detection.crop_slug == crop_slug)
    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(
        stmt.order_by(Detection.created_at.desc()).offset((page_no - 1) * limit).limit(limit)
    )).scalars().all()
    return page([detection_list_out(d) for d in rows], page_no, limit, total)


@router.get("/queue")
async def expert_queue(limit: int = Query(30, ge=1, le=100),
                       _staff: User = Depends(require_role("expert", "admin")),
                       db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Detection).where(Detection.review_status == "pending_expert")
        .order_by(Detection.created_at).limit(limit)
    )).scalars().all()
    items = []
    for d in rows:
        item = detection_list_out(d)
        item["image_url"] = d.image_key
        item["image_key"] = d.image_key
        items.append(item)
    return data(items)


@router.get("/library")
async def library(crop_slug: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Disease).where(Disease.is_active.is_(True)).order_by(Disease.crop_slug, Disease.name_en)
    if crop_slug:
        stmt = stmt.where(Disease.crop_slug == crop_slug)
    rows = (await db.execute(stmt)).scalars().all()
    crops = {c.slug: c for c in (await db.execute(select(Crop))).scalars().all()}
    items = []
    for d in rows:
        treatments = (await db.execute(
            select(Treatment).where(Treatment.disease_slug == d.slug).order_by(Treatment.display_order)
        )).scalars().all()
        items.append(disease_out(d, crops.get(d.crop_slug), _treatments(treatments)))
    return data(items)


@router.get("/library/{slug}")
async def library_item(slug: str, db: AsyncSession = Depends(get_db)):
    d = (await db.execute(select(Disease).where(Disease.slug == slug))).scalar_one_or_none()
    if d is None:
        raise NotFound("Disease not found.")
    crop = (await db.execute(select(Crop).where(Crop.slug == d.crop_slug))).scalar_one_or_none()
    treatments = (await db.execute(
        select(Treatment).where(Treatment.disease_slug == d.slug).order_by(Treatment.display_order)
    )).scalars().all()
    payload = disease_out(d, crop, _treatments(treatments))
    payload["disclaimer"] = (
        "Reference information curated from public extension sources. Chemical doses are general; "
        "confirm with your local agriculture officer before spraying."
    )
    return data(payload)


@router.get("/risk-alerts")
async def farm_risk_alerts(farm_id: str, crop_slug: str | None = None,
                           user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm = await db.get(Farm, farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    district = await db.get(District, farm.district_id)
    crop = crop_slug or farm.primary_crop_slug
    if not crop:
        return data({
            "farm_id": farm.id, "crop_slug": None, "alerts": [],
            "note": "Set a primary crop for this farm to see disease risk alerts.",
        })
    bundle = await get_weather(db, farm, district)
    today = bundle["daily"][0]
    alerts = await risk_alerts(db, crop, today["humidity_pct"], today["temp_max_c"])
    return data({
        "farm_id": farm.id, "crop_slug": crop,
        "alerts": alerts,
        "weather": {"humidity_pct": today["humidity_pct"], "temp_max_c": today["temp_max_c"]},
        "provenance": bundle["provenance"],
        "note": "Risk windows are reference conditions for each disease, not a confirmed outbreak.",
    })


@router.get("/detections/{det_id}")
async def detection_detail(det_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    det = await _detection_for(db, user, det_id)
    payload = await serialize_detection(db, det)
    if det.farm_id:
        payload["farm_id"] = det.farm_id
    return data(payload)


@router.post("/detections/{det_id}/escalate")
async def escalate(det_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    det = await _detection_for(db, user, det_id)
    if det.user_id != user.id:
        raise NotFound("Detection not found.")
    if det.review_status == "pending_expert":
        return data({"id": det.id, "review_status": det.review_status, "message": "Already waiting for expert review."})
    if det.expert_slug and det.review_status in {"confirmed", "corrected"}:
        return data({"id": det.id, "review_status": det.review_status, "message": "An expert has already reviewed this photo."})
    det.review_status = "pending_expert"
    await audit(db, user.id, "disease.escalate", "detection", det.id)
    await db.commit()
    return data({
        "id": det.id, "review_status": det.review_status,
        "message": "Sent to an expert. You will see their note on this photo when it is reviewed.",
    })


@router.patch("/detections/{det_id}/review")
async def review(det_id: str, body: ReviewIn, request: Request,
                 expert: User = Depends(require_role("expert", "admin")),
                 db: AsyncSession = Depends(get_db)):
    det = await db.get(Detection, det_id)
    if det is None:
        raise NotFound("Detection not found.")
    disease = None
    if body.decision == "corrected":
        if not body.disease_slug:
            raise ValidationError("Choose the correct disease.",
                                  [{"field": "disease_slug", "issue": "Required when correcting."}])
        disease = (await db.execute(select(Disease).where(Disease.slug == body.disease_slug))).scalar_one_or_none()
        if disease is None:
            raise ValidationError("Unknown disease.", [{"field": "disease_slug", "issue": "Not in the catalogue."}])
    elif body.decision == "confirmed":
        if not det.predicted_slug:
            raise ValidationError(
                "This detection is uncertain, so it cannot be confirmed.",
                [{"field": "decision", "issue": "Correct it to a disease instead."}],
            )
        disease = (await db.execute(select(Disease).where(Disease.slug == det.predicted_slug))).scalar_one_or_none()

    det.expert_id = expert.id
    det.expert_slug = disease.slug if disease and body.decision != "rejected" else None
    det.expert_note = body.note
    det.reviewed_at = utcnow()
    det.review_status = body.decision
    if body.decision != "rejected":
        det.status = "completed"
        det.crop_slug = disease.crop_slug if disease else det.crop_slug

    await audit(db, expert.id, f"disease.review.{body.decision}", "detection", det.id,
                {"disease_slug": det.expert_slug, "note": body.note},
                request.client.host if request.client else None)
    await db.commit()
    await db.refresh(det)
    return data(await serialize_detection(db, det))
