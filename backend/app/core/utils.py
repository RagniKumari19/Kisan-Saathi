"""Small shared helpers: envelopes, timestamps, distance, phone normalisation."""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from app.core.db import utcnow


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


def iso_date(d: date | None) -> str | None:
    return d.isoformat() if d else None


def data(payload: Any) -> dict:
    return {"data": payload}


def page(items: list, page_no: int, limit: int, total: int) -> dict:
    return {
        "data": items,
        "meta": {
            "page": page_no,
            "limit": limit,
            "total": total,
            "has_next": page_no * limit < total,
        },
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def normalise_phone(raw: str) -> str:
    digits = "".join(c for c in raw.strip() if c.isdigit() or c == "+")
    if digits.startswith("+"):
        cc = digits[1:]
    else:
        cc = digits
    if cc.startswith("91") and len(cc) == 12:
        return "+" + cc
    if len(cc) == 10:
        return "+91" + cc
    if len(cc) == 11 and cc.startswith("0"):
        return "+91" + cc[1:]
    return "+" + cc


def mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return phone
    return phone[:3] + "•" * (len(phone) - 6) + phone[-3:]


def utc_iso_now() -> str:
    return iso(utcnow()) or ""


def inr(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:,.2f}"
