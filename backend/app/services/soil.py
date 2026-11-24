"""Deterministic soil interpretation (ruleset soil-rules-v1).

No ML and no LLM: every status and recommendation follows a documented
threshold, and every recommendation names its source. Thresholds are agronomic
reference ranges for Indian soils (ICAR / TNAU soil-test interpretation).
"""
from __future__ import annotations

from app.models import Crop, SoilReport

RULESET_VERSION = "soil-rules-v1"

SOURCE_SOIL_HEALTH = "https://soilhealth.dac.gov.in/"
SOURCE_TNAU = "https://agritech.tnau.ac.in/agriculture/agri_soil_fertility.html"

GENERIC_TARGETS = {"n": 280.0, "p": 25.0, "k": 140.0}


def _ratio_status(value: float, target: float) -> str:
    ratio = value / target if target else 1.0
    if ratio < 0.5:
        return "very_low"
    if ratio < 0.75:
        return "low"
    if ratio <= 1.15:
        return "medium"
    if ratio <= 1.6:
        return "high"
    return "very_high"


def ph_status(ph: float) -> str:
    if ph < 5.5:
        return "strongly_acidic"
    if ph < 6.5:
        return "slightly_acidic"
    if ph <= 7.5:
        return "neutral"
    if ph <= 8.5:
        return "slightly_alkaline"
    return "strongly_alkaline"


def organic_carbon_status(oc: float) -> str:
    if oc < 0.5:
        return "low"
    if oc < 0.75:
        return "medium"
    return "high"


def ec_status(ec: float) -> str:
    return "saline" if ec > 1.0 else "normal"


def analyze_soil(report: SoilReport, crop: Crop | None) -> dict:
    targets = {
        "n": crop.n_target if crop else GENERIC_TARGETS["n"],
        "p": crop.p_target if crop else GENERIC_TARGETS["p"],
        "k": crop.k_target if crop else GENERIC_TARGETS["k"],
    }
    statuses: dict[str, str | None] = {
        "nitrogen": _ratio_status(report.nitrogen_kg_ha, targets["n"]) if report.nitrogen_kg_ha is not None else None,
        "phosphorus": _ratio_status(report.phosphorus_kg_ha, targets["p"]) if report.phosphorus_kg_ha is not None else None,
        "potassium": _ratio_status(report.potassium_kg_ha, targets["k"]) if report.potassium_kg_ha is not None else None,
        "ph": ph_status(report.ph) if report.ph is not None else None,
        "organic_carbon": organic_carbon_status(report.organic_carbon_pct) if report.organic_carbon_pct is not None else None,
        "ec": ec_status(report.ec_ds_m) if report.ec_ds_m is not None else None,
    }
    missing = [k for k, v in statuses.items() if v is None]

    recs: list[dict] = []

    def add(priority: int, key: str, action: str, detail: str, action_hi: str, detail_hi: str,
            source: str = SOURCE_TNAU):
        recs.append({
            "priority": priority, "key": key, "action": action, "detail": detail,
            "action_hi": action_hi, "detail_hi": detail_hi, "source_url": source,
        })

    n_status = statuses["nitrogen"]
    if n_status in {"very_low", "low"}:
        deficit = max(0.0, targets["n"] - (report.nitrogen_kg_ha or 0))
        add(1, "nitrogen", "Correct low nitrogen",
            f"Available nitrogen is {n_status.replace('_', ' ')}. Split about {deficit:.0f} kg N/ha across basal and top-dressings; do not apply it all at sowing.",
            "नाइट्रोजन सुधारें",
            f"उपलब्ध नाइट्रोजन {n_status.replace('_', ' ')} है। लगभग {deficit:.0f} किग्रा N/हेक्टेयर बुवाई और बाद की खुराक में बांटें।")
    p_status = statuses["phosphorus"]
    if p_status in {"very_low", "low"}:
        add(1, "phosphorus", "Correct low phosphorus",
            "Apply the full phosphorus dose as basal at sowing, placed near the root zone rather than broadcast.",
            "फॉस्फोरस सुधारें",
            "पूरी मात्रा बुवाई के समय जड़ों के पास डालें, खेत में छिड़कें नहीं।")
    k_status = statuses["potassium"]
    if k_status in {"very_low", "low"}:
        add(1, "potassium", "Correct low potassium",
            "Apply muriate of potash as a basal dose; for fruit crops split it across the season.",
            "पोटाश सुधारें",
            "बुवाई के समय डालें; फल वाली फसलों में सीज़न में बांटें।")
    ph = statuses["ph"]
    if ph == "strongly_acidic":
        add(2, "ph_low", "Correct strongly acidic soil",
            "Apply agricultural lime (based on a lime requirement test) before the next crop and re-test after harvest.",
            "अम्लीय मिट्टी सुधारें",
            "अगली फसल से पहले चूना डालें (लाइम रिक्वायरमेंट टेस्ट के अनुसार) और कटाई के बाद दोबारा जांच कराएं।")
    elif ph == "slightly_acidic":
        add(3, "ph_low", "Monitor slightly acidic soil",
            "Most crops tolerate this pH. Monitor pH each season rather than liming routinely.",
            "हल्की अम्लीयता पर नज़र रखें",
            "ज़्यादातर फसलें इसे सह लेती हैं। हर सीज़न pH देखें, बिना जांच चूना न डालें।")
    elif ph in {"strongly_alkaline", "slightly_alkaline"}:
        add(2, "ph_high", "Manage alkaline soil",
            "Prefer tolerant crops, add organic matter, and apply gypsum only after a soil test advises it.",
            "क्षारीय मिट्टी संभालें",
            "सहनशील फसलें चुनें, जैविक खाद बढ़ाएं और जिप्सम सिर्फ जांच की सलाह पर डालें।")
    if statuses["organic_carbon"] == "low":
        add(2, "organic_carbon", "Add organic matter",
            "Incorporate 5–10 t/acre of well-rotted farmyard manure and keep crop residue on the field.",
            "जैविक खाद बढ़ाएं",
            "5–10 टन/एकड़ सड़ी गोबर खाद मिलाएं और फसल अवशेष खेत में ही रहने दें।")
    if statuses["ec"] == "saline":
        add(1, "ec_high", "Check salinity before cropping",
            "Electrical conductivity suggests salinity. Avoid further saline irrigation, ensure drainage, and get a lab confirmation before choosing crops.",
            "लवणता की जांच कराएं",
            "खारा पानी न दें, जल निकासी सुधारें और फसल चुनने से पहले लैब जांच कराएं।")
    if not recs:
        add(4, "balanced", "Maintain current practice",
            "All measured parameters are in a workable range. Re-test after harvest.",
            "मौजूदा तरीका जारी रखें",
            "सभी मापे गए पैरामीटर ठीक सीमा में हैं। कटाई के बाद दोबारा जांच कराएं।")

    recs.sort(key=lambda r: r["priority"])

    issues_en, issues_hi = [], []
    if n_status in {"very_low", "low"}:
        issues_en.append("low nitrogen"); issues_hi.append("कम नाइट्रोजन")
    if p_status in {"very_low", "low"}:
        issues_en.append("low phosphorus"); issues_hi.append("कम फॉस्फोरस")
    if k_status in {"very_low", "low"}:
        issues_en.append("low potassium"); issues_hi.append("कम पोटाश")
    if ph in {"strongly_acidic", "slightly_acidic"}:
        issues_en.append("acidic pH"); issues_hi.append("अम्लीय pH")
    if ph in {"strongly_alkaline", "slightly_alkaline"}:
        issues_en.append("alkaline pH"); issues_hi.append("क्षारीय pH")
    if statuses["organic_carbon"] == "low":
        issues_en.append("low organic carbon"); issues_hi.append("कम जैविक कार्बन")

    crop_name = crop.name_en if crop else "your crop"
    crop_name_hi = crop.name_hi if crop else "आपकी फसल"
    if issues_en:
        summary_en = f"For {crop_name}: {', '.join(issues_en)}. Fix the first priority item before the next sowing."
        summary_hi = f"{crop_name_hi} के लिए: {', '.join(issues_hi)}। अगली बुवाई से पहले पहली प्राथमिकता ठीक करें।"
    else:
        summary_en = f"Measured soil parameters are in a workable range for {crop_name}."
        summary_hi = f"{crop_name_hi} के लिए मापे गए मिट्टी के पैरामीटर ठीक सीमा में हैं।"

    if missing:
        summary_en += " Not enough data for: " + ", ".join(missing).replace("_", " ") + "."
        summary_hi += " इनका डेटा नहीं है: " + ", ".join(missing).replace("_", " ") + "।"

    return {
        "statuses": statuses,
        "summary_en": summary_en,
        "summary_hi": summary_hi,
        "recommendations": recs,
        "ruleset_version": RULESET_VERSION,
        "missing_fields": missing,
    }
