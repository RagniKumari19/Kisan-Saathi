from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, utcnow
from app.core.deps import current_user, optional_user
from app.core.errors import NotFound, ValidationError
from app.core.utils import data, iso, iso_date, page
from app.models import Commodity, District, Farm, IngestionRun, MandiPrice, Market, User
from app.services import markets as svc

router = APIRouter(prefix="/markets", tags=["markets"])

TRANSPORT_RATE_PER_KM = 0.45  # ₹ per km per quintal, shared-truck estimate
NOTES = [
    "Prices are per quintal, as reported by each mandi on the date shown.",
    "Not every mandi reports every day; a missing date is not a zero price.",
    "Modal price is the most common price, not an average.",
    "Transport cost is an estimate, not a quote.",
]


async def _commodity(db: AsyncSession, key: str) -> Commodity:
    k = key.strip().lower()
    row = (await db.execute(
        select(Commodity).where(
            or_(Commodity.slug == k, Commodity.name_en.ilike(k))
        )
    )).scalar_one_or_none()
    if row is None:
        rows = (await db.execute(select(Commodity))).scalars().all()
        for c in rows:
            if any(a.lower() == k for a in (c.aliases or [])):
                row = c
                break
    if row is None:
        raise NotFound(f"No commodity named '{key}'.")
    return row


def _provenance(rows: list[MandiPrice], newest: date | None) -> dict:
    mock = any(r.is_mock for r in rows) if rows else True
    source = rows[0].source if rows else "none"
    return {
        "source": source, "source_url": None,
        "retrieved_at": iso(utcnow()),
        "data_date": iso_date(newest),
        "is_mock": mock,
        "stale": bool(newest and (date.today() - newest).days > 1),
        "note": "Demo price fixtures for this build; connect AGMARKNET for live data." if mock else None,
    }


@router.get("")
async def list_markets(state: str | None = None, district_id: str | None = None, q: str | None = None,
                       db: AsyncSession = Depends(get_db)):
    stmt = select(Market, District).join(District, District.id == Market.district_id).where(Market.is_active.is_(True))
    if district_id:
        stmt = stmt.where(Market.district_id == district_id)
    if state:
        stmt = stmt.where(District.state.ilike(f"%{state}%"))
    if q:
        stmt = stmt.where(Market.name.ilike(f"%{q.strip()}%"))
    rows = (await db.execute(stmt.order_by(District.name, Market.name))).all()
    return data([
        {
            "id": m.id, "name": m.name, "slug": m.slug,
            "district_id": d.id, "district": d.name, "state": d.state,
            "latitude": m.latitude, "longitude": m.longitude,
        } for m, d in rows
    ])


@router.get("/prices")
async def prices(commodity: str, district_id: str | None = None, state: str | None = None,
                 date_from: date | None = Query(None, alias="date"),
                 variety: str | None = None, grade: str | None = None,
                 page_no: int = Query(1, ge=1, alias="page"), limit: int = Query(50, ge=1, le=200),
                 db: AsyncSession = Depends(get_db)):
    c = await _commodity(db, commodity)
    stmt = (
        select(MandiPrice, Market, District)
        .join(Market, Market.id == MandiPrice.market_id)
        .join(District, District.id == Market.district_id)
        .where(MandiPrice.commodity == c.slug)
        .order_by(MandiPrice.arrival_date.desc())
    )
    if district_id:
        stmt = stmt.where(Market.district_id == district_id)
    if state:
        stmt = stmt.where(District.state.ilike(f"%{state}%"))
    if date_from:
        stmt = stmt.where(MandiPrice.arrival_date == date_from)
    if variety:
        stmt = stmt.where(MandiPrice.variety.ilike(variety))
    if grade:
        stmt = stmt.where(MandiPrice.grade.ilike(grade))
    rows = (await db.execute(stmt)).all()
    if not date_from:
        latest: dict[str, tuple] = {}
        for p, m, d in rows:
            latest.setdefault(m.id, (p, m, d))
        rows = list(latest.values())
    total = len(rows)
    sliced = rows[(page_no - 1) * limit: page_no * limit]
    items = []
    for p, m, d in sliced:
        items.append({
            "market_id": m.id, "market_name": m.name, "district": d.name, "state": d.state,
            "district_id": d.id,
            "commodity": c.slug, "commodity_name_en": c.name_en, "commodity_name_hi": c.name_hi,
            "variety": p.variety, "grade": p.grade,
            "arrival_date": iso_date(p.arrival_date),
            "min_price": round(p.min_price, 2), "max_price": round(p.max_price, 2),
            "modal_price": round(p.modal_price, 2), "unit": p.unit,
            "source": p.source, "is_mock": p.is_mock,
        })
    newest = max((p.arrival_date for p, _, _ in rows), default=None)
    payload = page(items, page_no, limit, total)
    payload["meta"]["provenance"] = _provenance([r[0] for r in rows], newest)
    if not items:
        payload["meta"]["reason"] = "NO_DATA_FOR_DISTRICT" if district_id else "NO_DATA"
    return payload


@router.get("/compare")
async def compare(commodity: str, district_id: str | None = None, radius_km: float | None = Query(None, gt=0, le=500),
                  farm_id: str | None = None, user: User | None = Depends(optional_user),
                  limit: int = Query(20, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    c = await _commodity(db, commodity)
    farm = None
    if farm_id:
        farm = await db.get(Farm, farm_id)
        if farm is None or user is None or farm.user_id != user.id:
            raise NotFound("Farm not found.")
        district_id = district_id or farm.district_id
    result = await svc.compare(db, c.slug, district_id, farm, limit)
    items = []
    for item in result["items"]:
        if radius_km and item["distance_km"] is not None and item["distance_km"] > radius_km:
            continue
        net = None
        note = None
        if item["distance_km"] is not None:
            cost = round(item["distance_km"] * TRANSPORT_RATE_PER_KM, 2)
            net = round(item["modal_price"] - cost, 2)
            note = f"Estimated: {item['distance_km']} km × ₹{TRANSPORT_RATE_PER_KM:.2f}/km/quintal"
        items.append({**item, "net_after_transport": net, "transport_note": note})
    newest = result.get("data_date")
    rows = (await db.execute(
        select(MandiPrice).where(MandiPrice.commodity == c.slug, MandiPrice.arrival_date == newest)
    )).scalars().all() if newest else []
    payload = {
        "commodity": {"slug": c.slug, "name_en": c.name_en, "name_hi": c.name_hi},
        "unit": "quintal",
        "markets": items,
        "spread": result.get("spread"),
        "spread_pct": result.get("spread_pct"),
        "provenance": _provenance(rows, date.fromisoformat(newest) if newest else None),
        "notes": NOTES,
    }
    if not items:
        payload["meta"] = {"reason": "NO_DATA_FOR_DISTRICT" if district_id else "NO_DATA"}
    return data(payload)


@router.get("/trends")
async def trends(commodity: str, district_id: str | None = None, market_id: str | None = None,
                 days: int = Query(30, ge=7, le=90), db: AsyncSession = Depends(get_db)):
    c = await _commodity(db, commodity)
    result = await svc.trends(db, c.slug, market_id, district_id, days)
    result["commodity"] = {"slug": c.slug, "name_en": c.name_en, "name_hi": c.name_hi}
    result["provenance"] = {
        "source": "demo_seed", "is_mock": True, "stale": False,
        "data_date": date.today().isoformat(), "retrieved_at": iso(utcnow()),
    }
    return data(result)


@router.get("/suggestions")
async def suggestions(farm_id: str, commodity: str | None = None,
                      user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    farm = await db.get(Farm, farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    district = await db.get(District, farm.district_id)
    slug = commodity or farm.primary_crop_slug
    if not slug:
        raise ValidationError(
            "Choose a commodity.", [{"field": "commodity", "issue": "This farm has no primary crop set."}]
        )
    c = await _commodity(db, slug)
    result = await svc.suggestions(db, farm, c.slug, district)
    result["commodity"] = {"slug": c.slug, "name_en": c.name_en, "name_hi": c.name_hi}
    result["provenance"] = {
        "source": "demo_seed", "is_mock": True, "stale": False,
        "data_date": result.get("data_date"), "retrieved_at": iso(utcnow()),
    }
    return data(result)


@router.get("/msp")
async def msp(commodity: str | None = None, db: AsyncSession = Depends(get_db)):
    return data(await svc.msp_list(db, commodity))


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(MandiPrice))).scalar() or 0
    newest = (await db.execute(select(func.max(MandiPrice.arrival_date)))).scalar()
    oldest = (await db.execute(select(func.min(MandiPrice.arrival_date)))).scalar()
    markets = (await db.execute(select(func.count(func.distinct(MandiPrice.market_id))))).scalar() or 0
    mock_rows = (await db.execute(
        select(func.count()).select_from(MandiPrice).where(MandiPrice.is_mock.is_(True))
    )).scalar() or 0
    run = (await db.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()))).scalars().first()
    return data({
        "rows": total,
        "markets_reporting": markets,
        "oldest_date": iso_date(oldest),
        "latest_date": iso_date(newest),
        "freshness_days": (date.today() - newest).days if newest else None,
        "mock_share": round(mock_rows / total, 3) if total else None,
        "is_mock": total > 0 and mock_rows == total,
        "last_run": {
            "id": run.id, "status": run.status, "started_at": iso(run.started_at),
            "finished_at": iso(run.finished_at), "rows_ingested": run.rows_ingested,
            "error": run.error,
        } if run else None,
        "note": "This build ships demo price fixtures; no live AGMARKNET feed is connected.",
    })
