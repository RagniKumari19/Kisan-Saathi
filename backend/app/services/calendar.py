"""Deterministic crop calendar generation (cropcalendar-rules-v1).

Generates a crop-specific farming calendar from a crop's duration and water need,
the sowing date, irrigation source and farming method. Dates are estimates derived
from published crop duration; they are never presented as guaranteed dates.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.models import Crop, Farm, SoilReport

MODEL_VERSION = "cropcalendar-rules-v1"

STAGES = [
    ("land_preparation", "Land preparation"),
    ("sowing", "Seed selection & sowing"),
    ("initial_growth", "Initial growth"),
    ("vegetative", "Vegetative growth"),
    ("flowering", "Flowering & fruiting"),
    ("harvesting", "Harvesting"),
]


def _add(acts, plan_id, user_id, stage, typ, title_en, title_hi, detail_en, detail_hi,
         d, materials=None, importance="medium", weather_sensitive=False):
    acts.append({
        "plan_id": plan_id, "user_id": user_id, "stage": stage, "activity_type": typ,
        "title_en": title_en, "title_hi": title_hi, "detail_en": detail_en, "detail_hi": detail_hi,
        "materials": materials or [], "importance": importance,
        "scheduled_date": d, "weather_sensitive": weather_sensitive,
        "status": "pending", "is_custom": False,
    })


def generate_activities(plan_id: str, user_id: str, crop: Crop, farm: Farm,
                       sowing: date, method: str) -> list[dict]:
    acts: list[dict] = []
    dur = crop.duration_days or 120
    organic = method in ("organic", "mixed")
    irrigated = (farm.irrigation_source or "").lower() not in ("", "rainfed", "none", "monsoon")
    water = crop.water_need

    # Stage 1: land preparation (sowing - 14 .. -3)
    _add(acts, plan_id, user_id, "land_preparation", "land_preparation",
         "Clear and clean the field",
         "खेत साफ़ करें",
         "Remove weeds, crop residue and stones. Mark bunds and drainage channels.",
         "खरपतवार, फसल अवशेष और पत्थर हटाएं। मेड़ और जल निकासी नाली बनाएं।",
         sowing - timedelta(days=14), importance="high")
    _add(acts, plan_id, user_id, "land_preparation", "land_preparation",
         "Plough and level the soil",
         "जुताई और समतलीकरण",
         "Deep plough once, then level. Break clods so seeds get good soil contact.",
         "एक बार गहरी जुताई, फिर समतलीकरण। गांठें तोड़ें ताकि बीज को अच्छा मिट्टी संपर्क मिले।",
         sowing - timedelta(days=10), importance="high")
    _add(acts, plan_id, user_id, "land_preparation", "fertilizer",
         "Apply organic manure / basal dose",
         "जैविक खाद / बेसल खुराक",
         ("Apply well-decomposed FYM/compost 5-10 t/ha and mix into soil."
          if organic else "Apply basal fertilizer as per soil test before final ploughing."),
         ("अच्छी तरह सड़ी हुई गोबर/कम्पोस्ट 5-10 टन/हेक्टेयर मिट्टी में मिलाएं।"
          if organic else "अंतिम जुताई से पहले मिट्टी जांच के अनुसार बेसल खाद डालें।"),
         sowing - timedelta(days=7), importance="high",
         materials=["FYM/compost" if organic else "Basal fertilizer", "Soil test report"],
         weather_sensitive=True)

    # Stage 2: sowing
    _add(acts, plan_id, user_id, "sowing", "sowing",
         "Seed treatment",
         "बीज उपचार",
         "Treat seeds with recommended fungicide/bio-agent before sowing. Dry in shade.",
         "बुवाई से पहले बीज का फफूंदनाशक/जैविक उपचार करें। छाया में सुखाएं।",
         sowing - timedelta(days=1), importance="high",
         materials=["Seed", "Fungicide/bio-agent"], weather_sensitive=True)
    _add(acts, plan_id, user_id, "sowing", "sowing",
         "Sowing / transplanting",
         "बुवाई / रोपाई",
         f"Sow {crop.name_en} at recommended spacing and depth. Season: {crop.season}.",
         f"{crop.name_en} की अनुशंसित दूरी और गहराई पर बुवाई करें। सीज़न: {crop.season}।",
         sowing, importance="high", weather_sensitive=True)
    _add(acts, plan_id, user_id, "sowing", "irrigation",
         "Light irrigation after sowing",
         "बुवाई के बाद हल्की सिंचाई",
         "Give a light irrigation to settle soil around seeds. Avoid waterlogging.",
         "बीज के चारों ओर मिट्टी बैठाने के लिए हल्की सिंचाई दें। जलभराव से बचें।",
         sowing + timedelta(days=1), importance="medium", weather_sensitive=True)

    # Stage 3: initial growth
    _add(acts, plan_id, user_id, "initial_growth", "monitoring",
         "Check germination",
         "अंकुरण जांच",
         "Inspect field 5-7 days after sowing. Re-sow gaps if germination is poor.",
         "बुवाई के 5-7 दिन बाद खेत देखें। अंकुरण कम हो तो खाली जगह फिर से बोएं।",
         sowing + timedelta(days=7), importance="medium")
    _add(acts, plan_id, user_id, "initial_growth", "weed_management",
         "First weeding",
         "पहली निराई-गुड़ाई",
         "Remove early weeds by hand or hoe. Do before weeds compete with crop.",
         "हाथ या खुरपी से शुरुआती खरपतवार हटाएं। फसल को प्रतिस्पर्धा से पहले।",
         sowing + timedelta(days=15), importance="medium")
    _add(acts, plan_id, user_id, "initial_growth", "irrigation",
         "Establishment irrigation",
         "स्थापना सिंचाई",
         "Irrigate as per soil moisture; crop has " + water + " water need.",
         "मिट्टी की नमी के अनुसार सिंचाई; फसल को " + water + " पानी की ज़रूरत है।",
         sowing + timedelta(days=10), importance="medium", weather_sensitive=True)

    # Stage 4: vegetative growth
    veg_start = sowing + timedelta(days=20)
    _add(acts, plan_id, user_id, "vegetative", "fertilizer",
         "First top-dressing (nitrogen)",
         "पहली टॉप ड्रेसिंग (नाइट्रोजन)",
         "Apply nitrogen-rich fertilizer/manure. Split dose if heavy rain forecast.",
         "नाइट्रोजन युक्त खाद/गोबर डालें। भारी बारिश का पूर्वानुमान हो तो खुराक बांटें।",
         sowing + timedelta(days=21), importance="high",
         materials=["Urea/organic nitrogen source"], weather_sensitive=True)
    _add(acts, plan_id, user_id, "vegetative", "pest_management",
         "Pest and disease scouting",
         "कीट और रोग निगरानी",
         "Inspect leaves (especially undersides) weekly. Use Protect module if symptoms appear.",
         "हर हफ्ते पत्तियां (खासकर नीचे) देखें। लक्षण हों तो Protect मॉड्यूल इस्तेमाल करें।",
         sowing + timedelta(days=25), importance="medium")
    _add(acts, plan_id, user_id, "vegetative", "fertilizer",
         "Second top-dressing",
         "दूसरी टॉप ड्रेसिंग",
         "Apply remaining nutrient dose based on crop stage and soil moisture.",
         "फसल की अवस्था और मिट्टी की नमी के अनुसार बाकी पोषक खुराक डालें।",
         sowing + timedelta(days=40), importance="medium", weather_sensitive=True)
    # irrigation cadence
    irr_days = [14, 28, 42, 56]
    for i, dd in enumerate(irr_days):
        if dd < dur - 10:
            _add(acts, plan_id, user_id, "vegetative", "irrigation",
                 f"Irrigation round {i+1}",
                 f"सिंचाई चक्र {i+1}",
                 "Check soil moisture before irrigating. Skip if rain is forecast.",
                 "सिंचाई से पहले मिट्टी की नमी जांचें। बारिश का पूर्वानुमान हो तो छोड़ें।",
                 sowing + timedelta(days=dd), importance="medium", weather_sensitive=True)

    # Stage 5: flowering & fruiting
    flower_day = max(45, int(dur * 0.6))
    _add(acts, plan_id, user_id, "flowering", "monitoring",
         "Flowering stage monitoring",
         "फूल आने की अवस्था निगरानी",
         "Monitor flowering/fruit set. Avoid water stress and excess nitrogen now.",
         "फूल और फल लगने पर नज़र रखें। अब पानी का तनाव और अधिक नाइट्रोजन से बचें।",
         sowing + timedelta(days=flower_day), importance="high")
    _add(acts, plan_id, user_id, "flowering", "irrigation",
         "Critical irrigation at flowering",
         "फूल आने पर महत्वपूर्ण सिंचाई",
         "Maintain adequate moisture during flowering/fruiting. Do not let soil dry out.",
         "फूल और फल अवस्था में मिट्टी में पर्याप्त नमी रखें। मिट्टी सूखने न दें।",
         sowing + timedelta(days=flower_day + 3), importance="high", weather_sensitive=True)
    _add(acts, plan_id, user_id, "flowering", "pest_management",
         "Disease watch at humid weather",
         "नम मौसम में रोग निगरानी",
         "High humidity can trigger fungal disease. Check leaves and use Protect module.",
         "अधिक नमी फंगस रोग बढ़ा सकती है। पत्तियां जांचें और Protect मॉड्यूल इस्तेमाल करें।",
         sowing + timedelta(days=flower_day + 7), importance="medium")

    # Stage 6: harvesting
    harvest_day = dur
    _add(acts, plan_id, user_id, "harvesting", "monitoring",
         "Check maturity signs",
         "परिपक्वता के लक्षण जांचें",
         "Look for crop-specific maturity signs (grain hardness, colour, moisture).",
         "फसल-विशिष्ट परिपक्वता लक्षण देखें (दाना कठोरता, रंग, नमी)।",
         sowing + timedelta(days=harvest_day - 7), importance="high")
    _add(acts, plan_id, user_id, "harvesting", "harvest",
         "Harvesting",
         "कटाई",
         "Harvest at optimal maturity. Avoid harvesting in rain; dry grains before storage.",
         "उचित परिपक्वता पर कटाई करें। बारिश में कटाई से बचें; भंडारण से पहले अनाज सुखाएं।",
         sowing + timedelta(days=harvest_day), importance="high", weather_sensitive=True)
    _add(acts, plan_id, user_id, "harvesting", "harvest",
         "Post-harvest handling & storage",
         "कटाई के बाद प्रबंधन और भंडारण",
         "Clean, dry and store in ventilated, pest-free conditions. Check market prices before selling.",
         "साफ़, सुखाकर वेंटिलेटेड और कीट-मुक्त जगह में भंडारण करें। बेचने से पहले मंडी भाव देखें।",
         sowing + timedelta(days=harvest_day + 3), importance="medium")

    # sort by date
    acts.sort(key=lambda a: a["scheduled_date"])
    return acts


def estimate_harvest(sowing: date, crop: Crop) -> date:
    return sowing + timedelta(days=crop.duration_days or 120)


def stage_for_day(crop: Crop, days: int) -> str:
    dur = crop.duration_days or 120
    if days < 0:
        return "land_preparation"
    if days <= 2:
        return "sowing"
    if days <= 20:
        return "initial_growth"
    if days <= int(dur * 0.6):
        return "vegetative"
    if days <= dur - 7:
        return "flowering"
    return "harvesting"


def assistant_answer(plan: dict, question: str, weather: dict | None) -> str:
    q = question.lower()
    today = date.today()
    started = plan.get("started") or plan.get("sowing_date") or today.isoformat()
    # tasks dated before the plan existed are history, not open work
    acts = [a for a in plan.get("activities", []) if a["scheduled_date"] >= started]
    pending = [a for a in acts if a["status"] == "pending"]
    overdue = [a for a in pending if a["scheduled_date"] <= today.isoformat()]
    soon = [a for a in pending if today.isoformat() <= a["scheduled_date"] <= (today + timedelta(days=7)).isoformat()]
    harvest = plan.get("expected_harvest_date")
    sowing = plan.get("sowing_date")
    days_since = (today - date.fromisoformat(sowing)).days if sowing else None

    if "today" in q or "क्या कर" in q:
        if overdue:
            return "Overdue: " + "; ".join(a["title_en"] for a in overdue[:5]) + ". Do these first."
        if soon:
            return "Today/this week: " + "; ".join(a["title_en"] for a in soon[:5]) + "."
        return "No pending tasks right now. Keep monitoring the crop."
    if "fertil" in q:
        fert = [a for a in pending if a["activity_type"] == "fertilizer"]
        if fert:
            return "Next fertilizer: " + fert[0]["title_en"] + " on " + fert[0]["scheduled_date"] + "."
        return "No fertilizer task is pending in this plan."
    if "harvest" in q:
        if harvest:
            days_left = (date.fromisoformat(harvest) - today).days
            return f"Estimated harvest date is {harvest} ({days_left} days from today). These are estimated dates."
        return "Harvest date not available."
    if "rain" in q or "weather" in q:
        if weather:
            daily = weather.get("daily", [])
            rain = sum(d.get("rain_mm", 0) for d in daily[:3])
            return f"Rain expected in next 3 days: about {rain:.0f} mm. Delay spraying/irrigation if heavy rain is forecast; check drainage."
        return "Weather data not available right now."
    if "pending" in q and "week" in q:
        if soon:
            return "Pending this week: " + "; ".join(a["title_en"] + " (" + a["scheduled_date"] + ")" for a in soon[:8]) + "."
        return "No pending tasks this week."
    if "slow" in q or "growth" in q:
        return ("Slower growth can be due to water stress, nutrient shortage, pests or weather. "
                "Check soil moisture, recent fertilizer, and leaves (Protect module). You can reschedule tasks or update progress manually.")
    if "days" in q and "sowing" in q:
        if days_since is not None:
            return f"Days since sowing: {days_since}. Current stage: {plan.get('current_stage')}."
        return "Sowing date not available."
    return ("I can help with today's tasks, fertilizer timing, harvest countdown, weather, pending tasks this week, "
            "or slow growth. Ask one of those.")
