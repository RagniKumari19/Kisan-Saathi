"""Deterministic crop recommendation (croprec-rules-v1).

This is a transparent agronomic scoring model, not a trained ML model. Each
ranked crop explains which measured factors helped or hurt it. Crops whose
agro-zone does not match the farm's district are suppressed with a visible
reason instead of being silently dropped.
"""
from __future__ import annotations

import math

from app.models import Crop, District, Farm, SoilReport

MODEL_VERSION = "croprec-rules-v1"

SOIL_TYPE_DEFAULTS = {
    "black": {"n": 240.0, "p": 22.0, "k": 320.0, "ph": 7.8, "oc": 0.55},
    "red": {"n": 180.0, "p": 18.0, "k": 200.0, "ph": 6.5, "oc": 0.40},
    "alluvial": {"n": 280.0, "p": 26.0, "k": 240.0, "ph": 7.2, "oc": 0.60},
    "laterite": {"n": 160.0, "p": 16.0, "k": 180.0, "ph": 5.8, "oc": 0.35},
    "sandy": {"n": 120.0, "p": 14.0, "k": 120.0, "ph": 7.0, "oc": 0.25},
}
DEFAULT = {"n": 200.0, "p": 20.0, "k": 200.0, "ph": 7.0, "oc": 0.45}

RAINFED = {"", "rainfed", "none", "monsoon"}


def _features(farm: Farm, report: SoilReport | None) -> tuple[dict, list[str], list[str]]:
    notes: list[str] = []
    missing: list[str] = []
    if report is not None:
        values = {
            "n": report.nitrogen_kg_ha, "p": report.phosphorus_kg_ha,
            "k": report.potassium_kg_ha, "ph": report.ph, "oc": report.organic_carbon_pct,
        }
        source = "soil_report"
        notes.append("Soil values come from your latest soil test report.")
        missing = [k for k, v in values.items() if v is None]
        fallback = SOIL_TYPE_DEFAULTS.get((farm.soil_type or "").lower(), DEFAULT)
        values = {k: (v if v is not None else fallback[k]) for k, v in values.items()}
    else:
        fallback = SOIL_TYPE_DEFAULTS.get((farm.soil_type or "").lower(), DEFAULT)
        values = dict(fallback)
        source = "farm_soil_type_default"
        missing = ["nitrogen", "phosphorus", "potassium", "ph", "organic_carbon"]
        notes.append(
            f"No soil test on file. Using typical values for {farm.soil_type or 'unrecorded'} soil; "
            "add a soil report to make this specific to your field."
        )
    irrigation = (farm.irrigation_source or "").strip().lower()
    values["rainfed"] = irrigation in RAINFED
    values["_source"] = source
    return values, notes, missing


def _ph_score(ph: float, lo: float, hi: float) -> float:
    if lo <= ph <= hi:
        return 1.0
    dist = lo - ph if ph < lo else ph - hi
    return max(0.0, 1.0 - dist / 2.0)


def _nutrient_score(value: float, target: float) -> float:
    ratio = value / target if target else 1.0
    if 0.8 <= ratio <= 1.25:
        return 1.0
    if ratio < 0.8:
        return max(0.0, ratio / 0.8)
    return max(0.0, 1.0 - (ratio - 1.25) / 1.5)


def _water_score(crop: Crop, rainfed: bool, rain_mm: float) -> float:
    need = crop.water_need
    if rainfed:
        if need == "high":
            return 0.15
        if need == "medium":
            return 0.6 if rain_mm >= 10 else 0.45
        return 1.0 if rain_mm >= 4 else 0.8
    if need == "high":
        return 0.9
    if need == "low":
        return 0.85
    return 1.0


def recommend(crops: list[Crop], farm: Farm, district: District, report: SoilReport | None,
              season: str, rain_mm: float) -> dict:
    values, notes, missing = _features(farm, report)
    results = []
    suppressed = []

    for crop in crops:
        if not crop.is_active:
            continue
        if district.agro_zone not in (crop.zones or []):
            suppressed.append({
                "crop_slug": crop.slug, "name_en": crop.name_en, "name_hi": crop.name_hi,
                "reason_en": f"Not recommended for the {district.agro_zone.replace('_', ' ').lower()} agro-zone ({district.name}).",
                "reason_hi": f"{district.name} के कृषि क्षेत्र के लिए अनुशंसित नहीं।",
            })
            continue

        season_match = crop.season == season
        if not season_match and crop.season != "perennial":
            suppressed.append({
                "crop_slug": crop.slug, "name_en": crop.name_en, "name_hi": crop.name_hi,
                "reason_en": f"{crop.season.capitalize()} crop; you selected {season}.",
                "reason_hi": f"यह {crop.season} फसल है; आपने {season} चुना है।",
            })
            continue

        ph_s = _ph_score(values["ph"], crop.ideal_ph_min, crop.ideal_ph_max)
        n_s = _nutrient_score(values["n"], crop.n_target)
        p_s = _nutrient_score(values["p"], crop.p_target)
        k_s = _nutrient_score(values["k"], crop.k_target)
        water_s = _water_score(crop, values["rainfed"], rain_mm)
        score = 0.28 * ph_s + 0.16 * n_s + 0.14 * p_s + 0.12 * k_s + 0.20 * water_s + 0.10
        if crop.season == "perennial":
            score -= 0.06  # long commitment; rank below seasonal crops when close
        score = max(0.0, min(1.0, score))

        reasons = []
        if ph_s >= 0.95:
            reasons.append({
                "en": f"pH {values['ph']:.1f} sits inside its ideal range {crop.ideal_ph_min:.1f}–{crop.ideal_ph_max:.1f}.",
                "hi": f"pH {values['ph']:.1f} इसकी उपयुक्त सीमा {crop.ideal_ph_min:.1f}–{crop.ideal_ph_max:.1f} में है।",
            })
        elif ph_s < 0.6:
            reasons.append({
                "en": f"pH {values['ph']:.1f} is outside its preferred {crop.ideal_ph_min:.1f}–{crop.ideal_ph_max:.1f} range.",
                "hi": f"pH {values['ph']:.1f} इसकी पसंदीदा सीमा {crop.ideal_ph_min:.1f}–{crop.ideal_ph_max:.1f} से बाहर है।",
            })
        low = [name for name, s in (("nitrogen", n_s), ("phosphorus", p_s), ("potassium", k_s)) if s < 0.7]
        if low:
            reasons.append({
                "en": "Needs extra " + ", ".join(low) + " to reach its target yield.",
                "hi": "लक्ष्य उपज के लिए " + ", ".join(low) + " अधिक चाहिए।",
            })
        else:
            reasons.append({
                "en": "Your nitrogen, phosphorus and potassium levels match its requirement.",
                "hi": "आपके नाइट्रोजन, फॉस्फोरस और पोटाश स्तर इसकी ज़रूरत से मेल खाते हैं।",
            })
        if values["rainfed"] and crop.water_need != "low":
            reasons.append({
                "en": f"{crop.water_need.capitalize()} water need with no irrigation source recorded — risky if rain fails.",
                "hi": f"{crop.water_need.capitalize()} पानी की ज़रूरत, पर सिंचाई स्रोत दर्ज नहीं — बारिश कम होने पर जोखिम।",
            })
        elif crop.water_need == "low":
            reasons.append({
                "en": "Low water requirement suits your recorded irrigation setup.",
                "hi": "कम पानी की ज़रूरत आपकी सिंचाई व्यवस्था के अनुकूल है।",
            })
        else:
            reasons.append({
                "en": f"Irrigation from your {farm.irrigation_source} can support its {crop.water_need} water need.",
                "hi": f"आपका {farm.irrigation_source} स्रोत इसकी {crop.water_need} पानी की ज़रूरत पूरी कर सकता है।",
            })

        band = "low" if score < 0.45 else "medium" if score < 0.65 else "high"
        results.append({
            "crop_slug": crop.slug, "name_en": crop.name_en, "name_hi": crop.name_hi,
            "category": crop.category, "season": crop.season,
            "duration_days": crop.duration_days, "water_need": crop.water_need,
            "score": round(score * 100, 1),
            "confidence": round(score, 3),
            "confidence_band": band,
            "agro_zone_ok": True,
            "yield_range": None,
            "yield_note": "Yield estimate not available: no validated yield model for this crop and district.",
            "reasons": [r["en"] for r in reasons[:3]],
            "reasons_i18n": reasons[:3],
            "description_en": crop.description_en, "description_hi": crop.description_hi,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    top = results[:6]
    # Probabilities are relative rankings, not field-outcome probabilities.
    if top:
        exps = [math.exp(r["confidence"] * 3.2) for r in top]
        total = sum(exps)
        for r, e in zip(top, exps):
            r["relative_fit_pct"] = round(e / total * 100, 1)
            r["probability"] = r["confidence"]

    return {
        "season": season,
        "results": top,
        "suppressed": suppressed,
        "model": {
            "name": "croprec",
            "version": MODEL_VERSION,
            "training_data": None,
            "is_mock": False,
            "method": "Deterministic agronomic scoring over soil test values, agro-zone, season and irrigation source.",
        },
        "input_provenance": {
            "soil_source": values["_source"],
            "missing_fields": missing,
            "notes_en": notes,
            "rainfall_used_mm": rain_mm,
            "rainfall_basis": "sum of the next 6 forecast days" if rain_mm else "no forecast rain",
        },
    }
