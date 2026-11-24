"""Mandi price queries, comparison, trends and selling suggestions.

All rows come from the ``mandi_prices`` table. In this build those rows are
generated demo fixtures (``source="demo_seed"``, ``is_mock=True``); the API never
invents a price at request time and always exposes ``arrival_date`` so a stale
or missing report is visible rather than hidden.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import haversine_km, iso_date
from app.models import District, Farm, MandiPrice, Market, MspRate

MAX_AGE_DAYS = 10


def _row(p: MandiPrice, m: Market, d: District, lat: float | None, lon: float | None) -> dict:
    distance = None
    if lat is not None and lon is not None:
        distance = haversine_km(lat, lon, m.latitude, m.longitude)
    return {
        "market_id": m.id,
        "market_name": m.name,
        "district": d.name,
        "state": d.state,
        "distance_km": distance,
        "commodity": p.commodity,
        "variety": p.variety,
        "grade": p.grade,
        "arrival_date": iso_date(p.arrival_date),
        "min_price": round(p.min_price, 2),
        "max_price": round(p.max_price, 2),
        "modal_price": round(p.modal_price, 2),
        "unit": p.unit,
        "source": p.source,
        "is_mock": p.is_mock,
    }


async def _latest_rows(db: AsyncSession, commodity: str, district_id: str | None = None,
                       market_id: str | None = None, days: int = MAX_AGE_DAYS) -> list[tuple]:
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(MandiPrice, Market, District)
        .join(Market, Market.id == MandiPrice.market_id)
        .join(District, District.id == Market.district_id)
        .where(MandiPrice.commodity == commodity, MandiPrice.arrival_date >= cutoff)
        .order_by(MandiPrice.arrival_date.desc())
    )
    if district_id:
        stmt = stmt.where(Market.district_id == district_id)
    if market_id:
        stmt = stmt.where(Market.id == market_id)
    rows = (await db.execute(stmt)).all()
    latest: dict[str, tuple] = {}
    for p, m, d in rows:  # already newest first
        if m.id not in latest:
            latest[m.id] = (p, m, d)
    return list(latest.values())


async def list_prices(db: AsyncSession, commodity: str, district_id: str | None,
                      farm: Farm | None, limit: int) -> dict:
    rows = await _latest_rows(db, commodity, district_id)
    if not rows:
        return {"prices": [], "data_date": None, "note": "No mandi report found for this commodity in the last 10 days."}
    payload = [
        _row(p, m, d, farm.latitude if farm else None, farm.longitude if farm else None)
        for p, m, d in rows
    ]
    payload.sort(key=lambda r: (r["distance_km"] is None, r["distance_km"] or 0))
    newest = max(p.arrival_date for p, _, _ in rows)
    stale = (date.today() - newest).days > 1
    return {
        "prices": payload[:limit],
        "data_date": iso_date(newest),
        "stale": stale,
        "note": "Latest report for each mandi; mandis do not all report every day." if not stale
        else f"The newest report is from {newest.isoformat()}; prices may have moved since.",
    }


async def compare(db: AsyncSession, commodity: str, district_id: str | None,
                  farm: Farm | None, limit: int) -> dict:
    rows = await _latest_rows(db, commodity, district_id)
    items = [_row(p, m, d, farm.latitude if farm else None, farm.longitude if farm else None) for p, m, d in rows]
    if not items:
        return {"commodity": commodity, "items": [], "best": None, "note": "No recent reports to compare."}
    items.sort(key=lambda r: r["modal_price"], reverse=True)
    best = items[0]
    worst = items[-1]
    spread = round(best["modal_price"] - worst["modal_price"], 2)
    for item in items:
        item["gap_vs_best"] = round(item["modal_price"] - best["modal_price"], 2)
    dates = sorted({i["arrival_date"] for i in items})
    return {
        "commodity": commodity,
        "items": items[:limit],
        "best": best,
        "spread": spread,
        "spread_pct": round(spread / worst["modal_price"] * 100, 1) if worst["modal_price"] else None,
        "data_date": dates[-1],
        "date_range": {"from": dates[0], "to": dates[-1]} if dates else None,
        "note": "Comparing modal prices from different arrival dates; check each date before deciding.",
    }


async def trends(db: AsyncSession, commodity: str, market_id: str | None,
                 district_id: str | None, days: int) -> dict:
    cutoff = date.today() - timedelta(days=days - 1)
    stmt = (
        select(MandiPrice, Market)
        .join(Market, Market.id == MandiPrice.market_id)
        .where(MandiPrice.commodity == commodity, MandiPrice.arrival_date >= cutoff)
        .order_by(MandiPrice.arrival_date)
    )
    if market_id:
        stmt = stmt.where(Market.id == market_id)
    if district_id:
        stmt = stmt.where(Market.district_id == district_id)
    rows = (await db.execute(stmt)).all()

    by_date: dict[date, list[float]] = {}
    for p, _m in rows:
        by_date.setdefault(p.arrival_date, []).append(p.modal_price)
    points = []
    d = cutoff
    while d <= date.today():
        vals = by_date.get(d)
        if vals:
            points.append({"date": iso_date(d), "modal_price": round(median(vals), 2), "markets_reporting": len(vals)})
        else:
            points.append({"date": iso_date(d), "modal_price": None, "markets_reporting": 0})
        d += timedelta(days=1)

    reported = [p for p in points if p["modal_price"] is not None]
    if len(reported) < 2:
        return {
            "commodity": commodity, "points": points, "summary": None, "days": days,
            "missing_days": sum(1 for p in points if p["modal_price"] is None),
            "note": "Not enough reported days to describe a trend.",
        }
    first, last = reported[0], reported[-1]
    change = last["modal_price"] - first["modal_price"]
    change_pct = round(change / first["modal_price"] * 100, 1) if first["modal_price"] else None
    avg = sum(p["modal_price"] for p in reported) / len(reported)
    variance = sum((p["modal_price"] - avg) ** 2 for p in reported) / len(reported)
    volatility = round((variance ** 0.5) / avg * 100, 1) if avg else None
    direction = "up" if change > 0.02 * avg else "down" if change < -0.02 * avg else "flat"
    return {
        "commodity": commodity,
        "points": points,
        "days": days,
        "missing_days": sum(1 for p in points if p["modal_price"] is None),
        "summary": {
            "first_price": first["modal_price"],
            "last_price": last["modal_price"],
            "change": round(change, 2),
            "change_pct": change_pct,
            "direction": direction,
            "volatility_pct": volatility,
            "median_price": round(median(p["modal_price"] for p in reported), 2),
            "reported_days": len(reported),
        },
        "note": "Median modal price across mandis reporting on each day. Gaps are days with no report.",
    }


async def suggestions(db: AsyncSession, farm: Farm, commodity: str, district: District) -> dict:
    near = await _latest_rows(db, commodity, district.id)
    wider = await _latest_rows(db, commodity)
    rows = near or wider
    if not rows:
        return {"commodity": commodity, "options": [], "advice": None,
                "note": "No recent price report for this commodity near your farm."}

    items = [_row(p, m, d, farm.latitude, farm.longitude) for p, m, d in rows]
    items.sort(key=lambda r: (-r["modal_price"], r["distance_km"] or 999))
    best = items[0]
    nearest = min(items, key=lambda r: r["distance_km"] or 999)
    newest = max(i["arrival_date"] for i in items)

    trend = await trends(db, commodity, None, district.id, 14)
    advice_en, advice_hi, basis_en = "", "", ""
    summary = trend.get("summary")
    if summary:
        direction = summary["direction"]
        change = abs(summary["change_pct"] or 0)
        basis_en = f"Median modal price moved {summary['change_pct']}% over {trend['days']} days ({summary['reported_days']} reporting days)."
        if direction == "up" and change >= 4:
            advice_en = "Prices are rising. If your produce stores safely and you can wait a few days, check again before selling."
            advice_hi = "भाव बढ़ रहे हैं। अगर उपज सुरक्षित रख सकते हैं, तो कुछ दिन बाद फिर जांच करें।"
        elif direction == "down" and change >= 4:
            advice_en = "Prices are falling. Selling sooner at the best nearby mandi limits further loss."
            advice_hi = "भाव गिर रहे हैं। सबसे अच्छे पास के मंडी में जल्दी बेचने से नुकसान कम होगा।"
        else:
            advice_en = "Prices are broadly stable. Choose the mandi with the best price net of distance."
            advice_hi = "भाव लगभग स्थिर हैं। दूरी देखते हुए अच्छे दाम वाली मंडी चुनें।"
    else:
        advice_en = "Not enough recent reports for a price trend. Compare today's modal prices below."
        advice_hi = "भाव का रुझान देखने के लिए पर्याप्त हालिया रिपोर्ट नहीं। नीचे आज के भाव देखें।"

    return {
        "commodity": commodity,
        "options": items[:6],
        "best": best,
        "nearest": nearest,
        "data_date": newest,
        "advice_en": advice_en,
        "advice_hi": advice_hi,
        "basis_en": basis_en or None,
        "note": "Suggestions compare reported prices and recent trend only. They are not a price forecast.",
    }


async def msp_list(db: AsyncSession, commodity: str | None) -> list[dict]:
    stmt = select(MspRate).order_by(MspRate.commodity)
    if commodity:
        stmt = stmt.where(MspRate.commodity == commodity)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "commodity": r.commodity, "season": r.season,
            "marketing_year": r.marketing_year,
            "price_per_quintal": r.price_per_quintal,
            "source_url": r.source_url,
            "published_on": iso_date(r.published_on),
            "last_verified": iso_date(r.last_verified),
        }
        for r in rows
    ]
