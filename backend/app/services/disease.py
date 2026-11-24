"""Image intake and the demo leaf-disease classifier.

Safety rules implemented here (see ADR-009):
* Only a validated, readable image is stored, and EXIF (including GPS) is stripped.
* A green-pixel gate rejects photos that are probably not a leaf.
* The classifier is a deterministic demo heuristic keyed on the image hash. It is
  labelled ``is_mock`` everywhere and never claims to be a trained model.
* Below ``DISEASE_CONFIDENCE_THRESHOLD`` the result is ``uncertain`` and carries
  **no treatments** and no disease name.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ImageUnreadable, NoLeafDetected, PayloadTooLarge, UnsupportedMediaType
from app.core.utils import iso
from app.models import Crop, Detection, Disease, Treatment

MODEL_NAME = "demo-heuristic"
MODEL_VERSION = "heuristic-v0"
MAX_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1280
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

DISCLAIMER = (
    "This is a demonstration classifier, not a laboratory diagnosis. "
    "Confirm any treatment with your local agriculture officer or KVK before spraying."
)


def _green_share(img: Image.Image) -> float:
    small = img.convert("RGB").resize((96, 96))
    pixels = list(small.getdata())
    green = 0
    total = 0
    for r, g, b in pixels:
        total += 1
        if g > 45 and g > r * 1.08 and g > b * 1.08:
            green += 1
    return green / max(1, total)


def process_image(raw: bytes) -> tuple[bytes, str, str, int, int, float]:
    if len(raw) > MAX_BYTES:
        raise PayloadTooLarge("Image is larger than 8 MB. Please retake or compress it.")
    try:
        probe = Image.open(io.BytesIO(raw))
        fmt = (probe.format or "").upper()
        probe.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageUnreadable("We could not read this file. Use a JPG, PNG or WEBP photo.") from exc
    if fmt not in ALLOWED_FORMATS:
        raise UnsupportedMediaType(f"{fmt or 'That'} files are not supported. Use JPG, PNG or WEBP.")

    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    if min(img.size) < 120:
        raise ImageUnreadable("Image is too small to inspect. Please upload a larger photo.")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    share = _green_share(img)
    if share < 0.12:
        raise NoLeafDetected(
            "We could not find a leaf in this photo. Fill the frame with the affected leaf in daylight and try again."
        )

    clean = io.BytesIO()
    img.save(clean, format="JPEG", quality=85, optimize=True)
    data = clean.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    return data, sha, fmt.lower(), img.width, img.height, share


async def _save(data: bytes, user_id: str) -> tuple[str, Path]:
    rel = Path("detections") / user_id / f"{uuid.uuid4().hex}.jpg"
    dest = Path(settings.storage_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return "/media/" + rel.as_posix(), dest


async def classify(db: AsyncSession, user_id: str, raw: bytes, crop_slug: str | None) -> tuple[Detection, dict]:
    data, sha, fmt, width, height, share = process_image(raw)
    image_url, _path = await _save(data, user_id)

    stmt = select(Disease).where(Disease.is_active.is_(True))
    if crop_slug:
        stmt = stmt.where(Disease.crop_slug == crop_slug)
    candidates = (await db.execute(stmt.order_by(Disease.slug))).scalars().all()
    if not candidates:
        candidates = (await db.execute(select(Disease).where(Disease.is_active.is_(True)).order_by(Disease.slug))).scalars().all()

    h = int(sha[:12], 16)
    picked = candidates[h % len(candidates)]
    confidence = round(0.40 + ((h >> 8) % 56) / 100.0, 2)
    threshold = settings.disease_confidence_threshold
    uncertain = confidence < threshold or not candidates

    detection = Detection(
        user_id=user_id, farm_id=None, crop_slug=picked.crop_slug if not uncertain else crop_slug,
        image_key=image_url, image_sha256=sha,
        predicted_slug=None if uncertain else picked.slug,
        confidence=confidence,
        top_k=[] if uncertain else [{"disease_slug": picked.slug, "name_en": picked.name_en, "confidence": confidence}],
        model_name=MODEL_NAME, model_version=MODEL_VERSION,
        status="uncertain" if uncertain else "completed",
        review_status="none", is_mock=True, latency_ms=0,
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    payload = await serialize_detection(db, detection, include_treatments=True)
    payload["image_meta"] = {
        "format": fmt, "width": width, "height": height,
        "leaf_pixel_share": round(share, 2), "exif_stripped": True,
    }
    return detection, payload


async def serialize_detection(db: AsyncSession, det: Detection, include_treatments: bool = True) -> dict:
    crop = None
    if det.crop_slug:
        crop = (await db.execute(select(Crop).where(Crop.slug == det.crop_slug))).scalar_one_or_none()
    disease = None
    treatments = []
    if det.predicted_slug:
        disease = (await db.execute(select(Disease).where(Disease.slug == det.predicted_slug))).scalar_one_or_none()
        if disease and include_treatments:
            rows = (await db.execute(
                select(Treatment).where(Treatment.disease_slug == disease.slug).order_by(Treatment.display_order)
            )).scalars().all()
            treatments = [
                {
                    "kind": t.kind, "title": t.title, "detail": t.detail,
                    "dosage": t.dosage, "safety_notes": t.safety_notes,
                    "source_url": t.source_url,
                    "last_verified": t.last_verified.isoformat() if t.last_verified else None,
                }
                for t in rows
            ]

    uncertain = det.status == "uncertain"
    next_steps = (
        [
            {"en": "Take another photo in daylight with the affected leaf filling the frame.", "hi": "दिन की रोशनी में प्रभावित पत्ती को फ्रेम में भरकर दोबारा फोटो लें।"},
            {"en": "Ask an expert to review this photo — the request button is below.", "hi": "नीचे बटन से विशेषज्ञ से इस फोटो की जांच कराएं।"},
            {"en": "Do not spray on the basis of this result.", "hi": "इस परिणाम के आधार पर छिड़काव न करें।"},
        ] if uncertain else
        [
            {"en": "Start with the cultural step first; it is usually cheapest and safest.", "hi": "पहले सांस्कृतिक उपाय करें; यह सबसे सस्ता और सुरक्षित है।"},
            {"en": "Confirm the diagnosis with your local agriculture officer before any chemical spray.", "hi": "किसी भी रासायनिक छिड़काव से पहले कृषि अधिकारी से पुष्टि करें।"},
        ]
    )

    next_actions = ["retake", "escalate_to_expert"] if uncertain else ["view_library", "escalate_to_expert"]

    return {
        "id": det.id,
        "status": det.status,
        "predicted": (
            {
                "slug": disease.slug, "name_en": disease.name_en, "name_hi": disease.name_hi,
                "confidence": det.confidence, "pathogen_type": disease.pathogen_type,
                "severity_default": disease.severity_default,
            } if disease and not uncertain else None
        ),
        "confidence": det.confidence,
        "threshold": settings.disease_confidence_threshold,
        "severity": disease.severity_default if disease and not uncertain else None,
        "symptoms_en": disease.symptoms_en if disease and not uncertain else None,
        "symptoms_hi": disease.symptoms_hi if disease and not uncertain else None,
        "spread_en": disease.spread_en if disease and not uncertain else None,
        "crop": (
            {"slug": crop.slug, "name_en": crop.name_en, "name_hi": crop.name_hi} if crop else None
        ),
        "top_k": det.top_k or [],
        "treatments": [] if uncertain else treatments,
        "image_key": det.image_key,
        "image_url": det.image_key,
        "is_mock": det.is_mock,
        "model": {
            "name": det.model_name, "version": det.model_version,
            "training_data": None, "is_mock": det.is_mock,
            "method": "Demo heuristic keyed on an image hash. Not a trained plant-disease classifier.",
        },
        "message_en": (
            "We could not identify this confidently, so we are not showing any treatment. "
            "Take another photo in daylight or send it to an expert."
            if uncertain else f"Possible {disease.name_en.lower()} with {det.confidence:.0%} confidence."
        ),
        "message_hi": (
            "हम इसे भरोसे से नहीं पहचान सके, इसलिए कोई उपचार नहीं दिखा रहे। दिन की रोशनी में दोबारा फोटो लें या विशेषज्ञ को भेजें।"
            if uncertain else f"संभवतः {disease.name_hi} ({det.confidence:.0%} विश्वास)।"
        ),
        "disclaimer": DISCLAIMER,
        "next_actions": next_actions,
        "next_steps": next_steps,
        "review_status": det.review_status,
        "expert_note": det.expert_note,
        "expert_agreed_slug": det.expert_slug,
        "created_at": iso(det.created_at),
        "reviewed_at": iso(det.reviewed_at),
        "provenance": {
            "source": "demo_heuristic", "is_mock": det.is_mock, "stale": False,
            "model_version": det.model_version,
        },
    }


async def risk_alerts(db: AsyncSession, crop_slug: str, humidity: int, temp_max: float) -> list[dict]:
    rows = (await db.execute(
        select(Disease).where(Disease.crop_slug == crop_slug, Disease.is_active.is_(True))
    )).scalars().all()
    alerts = []
    for d in rows:
        if d.risk_humidity_min and humidity < d.risk_humidity_min:
            continue
        if d.risk_temp_min is not None and temp_max < d.risk_temp_min:
            continue
        if d.risk_temp_max is not None and temp_max > d.risk_temp_max:
            continue
        alerts.append({
            "disease_slug": d.slug, "name_en": d.name_en, "name_hi": d.name_hi,
            "severity": d.severity_default,
            "reason_en": f"Forecast humidity {humidity}% and max {temp_max:.0f} °C match this disease's risk window.",
            "reason_hi": f"पूर्वानुमान में {humidity}% नमी और {temp_max:.0f} °C इस रोग के जोखिम क्षेत्र में हैं।",
        })
    alerts.sort(key=lambda a: a["severity"], reverse=True)
    return alerts
