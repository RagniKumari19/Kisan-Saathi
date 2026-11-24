from __future__ import annotations

from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import settings
from app.core.db import get_db, utcnow
from app.core.deps import require_role
from app.core.errors import NotImplementedYet
from app.core.utils import data, iso, page
from app.models import (
    AuditLog, CropRecommendation, Detection, District, Farm, IngestionRun, MandiPrice,
    Market, SoilReport, User,
)

router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
async def stats(_admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    async def count(model, *where):
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return (await db.execute(stmt)).scalar() or 0

    roles = {}
    for role in ("farmer", "expert", "admin"):
        roles[role] = await count(User, User.role == role)
    return data({
        "users": {"total": sum(roles.values()), **roles},
        "farms": await count(Farm),
        "soil_reports": await count(SoilReport),
        "recommendations": await count(CropRecommendation),
        "detections": await count(Detection),
        "detections_uncertain": await count(Detection, Detection.status == "uncertain"),
        "reviews_pending": await count(Detection, Detection.review_status == "pending_expert"),
        "price_rows": await count(MandiPrice),
        "markets": await count(Market),
        "districts": await count(District),
    })


@router.get("/admin/ingestion-runs")
async def ingestion_runs(limit: int = Query(20, ge=1, le=100),
                         _admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    )).scalars().all()
    return data([
        {
            "id": r.id, "source": r.source, "status": r.status, "rows_received": r.rows_received,
            "rows_upserted": r.rows_upserted,
            "started_at": iso(r.started_at), "finished_at": iso(r.finished_at), "error": r.error_message,
        } for r in rows
    ])


@router.post("/admin/ingestion/run", status_code=202)
async def trigger_ingestion(admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    if not settings.agmarknet_api_key:
        raise NotImplementedYet(
            "Live price ingestion needs AGMARKNET_API_KEY in the backend environment. "
            "Until then the app serves clearly-labelled demo prices."
        )
    run = IngestionRun(source="agmarknet", status="running", started_at=utcnow())
    db.add(run)
    await db.commit()
    await db.refresh(run)

    params = {
        "api-key": settings.agmarknet_api_key,
        "format": "json",
        "limit": 1000,
        "offset": 0,
    }
    rows_ingested = 0
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"https://api.data.gov.in/resource/{settings.agmarknet_resource_id}", params=params
            )
            r.raise_for_status()
            records = r.json().get("records", [])
        markets = {m.name.lower(): m for m in (await db.execute(select(Market))).scalars().all()}
        for rec in records:
            market = markets.get(str(rec.get("market", "")).strip().lower())
            if market is None:
                continue
            commodity = str(rec.get("commodity", "")).strip().lower()
            try:
                arrived = datetime.strptime(str(rec.get("arrival_date")), "%d/%m/%Y").date()
                lo = float(rec.get("min_price"))
                hi = float(rec.get("max_price"))
                modal = float(rec.get("modal_price"))
            except (ValueError, TypeError):
                continue
            exists = (await db.execute(
                select(MandiPrice.id).where(
                    MandiPrice.market_id == market.id, MandiPrice.commodity == commodity,
                    MandiPrice.variety == str(rec.get("variety", "Other")),
                    MandiPrice.grade == str(rec.get("grade", "FAQ")),
                    MandiPrice.arrival_date == arrived,
                )
            )).scalar_one_or_none()
            if exists:
                continue
            db.add(MandiPrice(
                market_id=market.id, commodity=commodity,
                variety=str(rec.get("variety", "Other"))[:80],
                grade=str(rec.get("grade", "FAQ"))[:20],
                arrival_date=arrived, min_price=lo, max_price=hi, modal_price=modal,
                unit="quintal", source="agmarknet", is_mock=False,
            ))
            rows_ingested += 1
        run.status = "succeeded"
        run.rows_received = len(records) if 'records' in locals() else 0
        run.rows_upserted = rows_ingested
        run.finished_at = utcnow()
    except (httpx.HTTPError, ValueError) as exc:
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.finished_at = utcnow()
    await audit(db, admin.id, "ingestion.run", "ingestion_run", run.id, {"status": run.status})
    await db.commit()
    return data({
        "id": run.id, "status": run.status, "rows_received": run.rows_received,
        "rows_upserted": run.rows_upserted, "error": run.error_message,
    })


@router.get("/admin/audit-logs")
async def audit_logs(page_no: int = Query(1, ge=1, alias="page"), limit: int = Query(50, ge=1, le=200),
                     _admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar() or 0
    rows = (await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page_no - 1) * limit).limit(limit)
    )).scalars().all()
    return page([
        {
            "id": r.id, "actor_id": r.actor_id, "action": r.action,
            "entity": r.entity, "entity_id": r.entity_id, "after": r.after,
            "created_at": iso(r.created_at),
        } for r in rows
    ], page_no, limit, total)
