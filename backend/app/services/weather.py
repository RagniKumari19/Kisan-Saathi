"""Weather provider, cache and the deterministic advisory rule engine.

If ``OPENWEATHER_API_KEY`` is configured we read the real forecast. Otherwise a
clearly-labelled deterministic demo forecast is generated so the whole PLAN
module is usable without credentials. Advisories are always computed by our own
rules — never by an upstream "alerts" product and never by an LLM.
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import utcnow
from app.core.utils import iso
from app.models import District, Farm, WeatherSnapshot

CONDITION_ICON = {
    "clear": "01d",
    "partly_cloudy": "02d",
    "cloudy": "03d",
    "overcast": "04d",
    "rain": "10d",
    "heavy_rain": "09d",
    "thunderstorm": "11d",
}


def _h(key: str, mod: int = 1000) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % mod


def _mock_forecast(lat: float, lon: float, district: District) -> dict:
    today = date.today()
    daily = []
    slots = []
    for i in range(6):
        d = today + timedelta(days=i)
        seed = f"{lat:.2f},{lon:.2f},{d.isoformat()}"
        hmin = 13 + _h(seed + "min", 9)
        hmax = hmin + 9 + _h(seed + "max", 7)
        humidity = 52 + _h(seed + "hum", 40)
        rain_roll = _h(seed + "rain", 100)
        rain = 0.0
        condition = "clear"
        if rain_roll < 12:
            rain = round(4 + _h(seed + "mm", 70), 1)
            condition = "heavy_rain" if rain > 40 else "rain"
        elif rain_roll < 40:
            condition = "partly_cloudy"
        elif rain_roll < 60:
            condition = "cloudy"
        wind = 5 + _h(seed + "wind", 22)
        daily.append({
            "date": d.isoformat(),
            "temp_min_c": hmin,
            "temp_max_c": hmax,
            "humidity_pct": humidity,
            "rain_mm": rain,
            "wind_kmph": wind,
            "condition": condition,
            "icon": CONDITION_ICON[condition],
        })
        for slot in range(0, 24, 3):
            slot_seed = seed + f"slot{slot}"
            t = hmin + (hmax - hmin) * (0.5 + 0.5 * math.sin((slot - 6) / 24 * 2 * math.pi))
            slots.append({
                "at": f"{d.isoformat()}T{slot:02d}:00:00Z",
                "temp_c": round(t + (_h(slot_seed, 20) - 10) / 10, 1),
                "rain_mm": round(rain / 8, 1) if rain else 0.0,
                "humidity_pct": min(96, humidity + _h(slot_seed + "h", 12) - 6),
                "wind_kmph": wind + _h(slot_seed + "w", 8) - 4,
            })
    first = daily[0]
    now_hour = datetime.now().hour
    frac = 0.5 + 0.5 * math.sin((now_hour - 6) / 24 * 2 * math.pi)
    return {
        "current": {
            "temp_c": round(first["temp_min_c"] + (first["temp_max_c"] - first["temp_min_c"]) * frac, 1),
            "humidity_pct": first["humidity_pct"],
            "wind_kmph": first["wind_kmph"],
            "rain_mm": first["rain_mm"],
            "condition": first["condition"],
            "icon": first["icon"],
            "observed_at": iso(utcnow()),
        },
        "daily": daily,
        "slots": slots,
        "provenance": {
            "source": "demo_forecast",
            "source_url": None,
            "retrieved_at": iso(utcnow()),
            "data_date": date.today().isoformat(),
            "is_mock": True,
            "stale": False,
            "note": "Demo forecast generated locally. Set OPENWEATHER_API_KEY for live data.",
        },
    }


async def _fetch_openweather(lat: float, lon: float) -> dict:
    params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key, "units": "metric"}
    async with httpx.AsyncClient(timeout=12) as client:
        cur_r = await client.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        cur_r.raise_for_status()
        fc_r = await client.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
        fc_r.raise_for_status()
    cur = cur_r.json()
    fc = fc_r.json()

    days: dict[str, dict] = {}
    slots = []
    for entry in fc.get("list", []):
        dt = datetime.fromtimestamp(entry["dt"], tz=None)
        day = dt.date().isoformat()
        temp = entry["main"]["temp"]
        rain = float(entry.get("rain", {}).get("3h", 0) or 0)
        entry_cond = (entry.get("weather") or [{"main": "Clear"}])[0]["main"].lower()
        condition = (
            "heavy_rain" if rain >= 20 else
            "rain" if rain > 0.2 else
            "thunderstorm" if "thunder" in entry_cond else
            "overcast" if "overcast" in entry_cond else
            "cloudy" if "cloud" in entry_cond else
            "clear"
        )
        slots.append({
            "at": dt.replace(minute=0).isoformat() + "Z",
            "temp_c": round(temp, 1),
            "rain_mm": rain,
            "humidity_pct": entry["main"]["humidity"],
            "wind_kmph": round(entry["wind"]["speed"] * 3.6, 1),
        })
        row = days.setdefault(day, {
            "date": day, "temp_min_c": temp, "temp_max_c": temp,
            "humidity_pct": 0, "rain_mm": 0.0, "wind_kmph": 0,
            "condition": condition, "icon": CONDITION_ICON.get(condition, "01d"),
            "_n": 0,
        })
        row["temp_min_c"] = min(row["temp_min_c"], temp)
        row["temp_max_c"] = max(row["temp_max_c"], temp)
        row["humidity_pct"] += entry["main"]["humidity"]
        row["rain_mm"] += rain
        row["wind_kmph"] += entry["wind"]["speed"] * 3.6
        row["_n"] += 1

    daily = []
    for row in list(days.values())[:6]:
        n = max(1, row.pop("_n"))
        row["humidity_pct"] = round(row["humidity_pct"] / n)
        row["wind_kmph"] = round(row["wind_kmph"] / n)
        row["rain_mm"] = round(row["rain_mm"], 1)
        row["temp_min_c"] = round(row["temp_min_c"], 1)
        row["temp_max_c"] = round(row["temp_max_c"], 1)
        daily.append(row)

    cur_weather = (cur.get("weather") or [{"main": "Clear"}])[0]["main"].lower()
    condition = "rain" if "rain" in cur_weather else "cloudy" if "cloud" in cur_weather else "clear"
    return {
        "current": {
            "temp_c": round(cur["main"]["temp"], 1),
            "humidity_pct": cur["main"]["humidity"],
            "wind_kmph": round(cur["wind"]["speed"] * 3.6, 1),
            "rain_mm": float(cur.get("rain", {}).get("1h", 0) or 0),
            "condition": condition,
            "icon": CONDITION_ICON[condition],
            "observed_at": iso(utcnow()),
        },
        "daily": daily,
        "slots": slots,
        "provenance": {
            "source": "openweathermap",
            "source_url": "https://openweathermap.org",
            "retrieved_at": iso(utcnow()),
            "data_date": date.today().isoformat(),
            "is_mock": False,
            "stale": False,
        },
    }


async def get_weather(db: AsyncSession, farm: Farm, district: District) -> dict:
    location_key = f"lat:{round(farm.latitude, 2)},lon:{round(farm.longitude, 2)}"
    snap = (
        await db.execute(
            select(WeatherSnapshot)
            .where(WeatherSnapshot.location_key == location_key)
            .order_by(WeatherSnapshot.fetched_at.desc())
        )
    ).scalars().first()
    now = utcnow()
    if snap and snap.expires_at > now:
        payload = dict(snap.payload)
        payload["provenance"] = {**payload.get("provenance", {}), "stale": False}
        return payload

    if settings.openweather_api_key:
        try:
            payload = await _fetch_openweather(farm.latitude, farm.longitude)
        except (httpx.HTTPError, KeyError, ValueError):
            payload = _mock_forecast(farm.latitude, farm.longitude, district)
            payload["provenance"]["note"] = "Live weather unavailable; showing demo forecast."
    else:
        payload = _mock_forecast(farm.latitude, farm.longitude, district)

    payload["location"] = {
        "latitude": farm.latitude, "longitude": farm.longitude,
        "district": district.name, "state": district.state,
    }
    if snap:
        snap.payload = payload
        snap.provider = payload["provenance"]["source"]
        snap.is_mock = payload["provenance"]["is_mock"]
        snap.fetched_at = now
        snap.expires_at = now + timedelta(minutes=30)
    else:
        db.add(WeatherSnapshot(
            location_key=location_key, kind="bundle",
            provider=payload["provenance"]["source"], payload=payload,
            is_mock=payload["provenance"]["is_mock"],
            fetched_at=now, expires_at=now + timedelta(minutes=30),
        ))
    await db.commit()
    return payload


def advisories(daily: list[dict]) -> list[dict]:
    """Deterministic, unit-testable advisories. Every rule has a stable id."""
    out: list[dict] = []
    if not daily:
        return out
    today = daily[0]
    next24 = daily[:2]
    rain24 = sum(d["rain_mm"] for d in next24)
    min_temp = min(d["temp_min_c"] for d in daily[:3])
    max_temp = max(d["temp_max_c"] for d in daily[:3])
    max_wind = max(d["wind_kmph"] for d in daily[:2])
    humid_days = sum(1 for d in daily[:3] if d["humidity_pct"] >= 85 and 20 <= d["temp_max_c"] <= 30)
    dry_days = sum(1 for d in daily[:4] if d["rain_mm"] < 1)

    def add(rule_id: str, severity: str, title_en: str, title_hi: str, detail_en: str, detail_hi: str, valid_days: int = 1):
        out.append({
            "rule_id": rule_id, "severity": severity,
            "title_en": title_en, "title_hi": title_hi,
            "detail_en": detail_en, "detail_hi": detail_hi,
            "valid_until": (utcnow() + timedelta(days=valid_days)).replace(microsecond=0).isoformat() + "Z",
        })

    if rain24 >= 25:
        add("heavy_rain_24h", "warning", "Heavy rain expected",
            "भारी बारिश की संभावना",
            f"About {rain24:.0f} mm rain is expected in the next 24 hours. Delay spraying and check field drainage.",
            f"अगले 24 घंटे में लगभग {rain24:.0f} मिमी बारिश हो सकती है। छिड़काव टालें और खेत में जल निकासी देखें।")
    if min_temp <= 4:
        add("frost_warning", "danger", "Frost risk", "पाला पड़ने का खतरा",
            f"Minimum temperature may fall to {min_temp:.0f} °C. Cover sensitive nurseries and young plants.",
            f"न्यूनतम तापमान {min_temp:.0f} °C तक गिर सकता है। नर्सरी और छोटे पौधे ढकें।")
    if max_temp >= 38:
        add("heat_stress", "warning", "Heat stress", "गर्मी का तनाव",
            f"Maximum temperature may reach {max_temp:.0f} °C. Irrigate in the early morning or evening; avoid midday spraying.",
            f"अधिकतम तापमान {max_temp:.0f} °C तक जा सकता है। सुबह या शाम सिंचाई करें; दोपहर में छिड़काव न करें।")
    if max_wind >= 25:
        add("windy_no_spray", "warning", "Too windy to spray", "तेज़ हवा — छिड़काव न करें",
            f"Wind may reach {max_wind:.0f} km/h. Spray drift will waste the chemical and can damage nearby crops.",
            f"हवा {max_wind:.0f} किमी/घंटा तक हो सकती है। छिड़काव करने से दवा उड़ जाएगी।")
    elif rain24 < 2:
        add("spray_window_ok", "info", "Good spraying window", "छिड़काव के लिए अच्छा समय",
            "Low wind and no significant rain expected for 24 hours. Spray in the early morning or evening.",
            "अगले 24 घंटे हवा कम और बारिश नहीं। सुबह या शाम छिड़काव करें।")
    else:
        add("spray_window_bad", "warning", "Spraying may be wasted", "छिड़काव बेकार जा सकता है",
            f"Rain of about {rain24:.0f} mm is expected within 24 hours; a spray now may wash off.",
            f"24 घंटे में लगभग {rain24:.0f} मिमी बारिश संभव है; अभी छिड़काव धुल सकता है।")
    if humid_days >= 2:
        add("fungal_risk_high", "warning", "High fungal disease risk", "फंगस रोग का अधिक खतरा",
            "Humidity above 85% with 20–30 °C for two or more days. Check the undersides of leaves for spots.",
            "दो या अधिक दिन 85% से अधिक नमी और 20–30 °C तापमान। पत्तियों के नीचे धब्बे देखें।", valid_days=2)
    if dry_days >= 3 and max_temp >= 32:
        add("irrigation_deficit_hint", "info", "Plan irrigation", "सिंचाई की योजना बनाएं",
            "No meaningful rain for three days and warm afternoons. Check soil moisture before the next irrigation.",
            "तीन दिन बारिश नहीं और दोपहर गर्म। अगली सिंचाई से पहले मिट्टी की नमी देखें।", valid_days=2)
    order = {"danger": 0, "warning": 1, "info": 2}
    out.sort(key=lambda a: order.get(a["severity"], 3))
    return out
