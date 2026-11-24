"""Response serializers shared by routers."""
from __future__ import annotations

from app.core.utils import iso
from app.models import Crop, Detection, Disease, District, Farm, User


def user_out(u: User) -> dict:
    return {
        "id": u.id, "phone": u.phone, "email": u.email, "full_name": u.full_name,
        "role": u.role, "language": u.language, "is_active": u.is_active,
        "phone_verified": u.phone_verified_at is not None,
        "has_password": bool(u.password_hash),
        "last_login_at": iso(u.last_login_at), "created_at": iso(u.created_at),
    }


def farm_out(f: Farm, d: District | None = None) -> dict:
    return {
        "id": f.id, "name": f.name, "village": f.village,
        "district_id": f.district_id,
        "district": ({"id": d.id, "name": d.name, "state": d.state, "slug": d.slug,
                      "agro_zone": d.agro_zone} if d else None),
        "latitude": f.latitude, "longitude": f.longitude,
        "area_acres": f.area_acres, "soil_type": f.soil_type,
        "irrigation_source": f.irrigation_source,
        "primary_crop_slug": f.primary_crop_slug,
        "is_primary": f.is_primary,
        "created_at": iso(f.created_at), "updated_at": iso(f.updated_at),
    }


def district_out(d: District) -> dict:
    return {
        "id": d.id, "name": d.name, "state": d.state, "slug": d.slug,
        "latitude": d.latitude, "longitude": d.longitude, "agro_zone": d.agro_zone,
    }


def crop_out(c: Crop) -> dict:
    return {
        "slug": c.slug, "name_en": c.name_en, "name_hi": c.name_hi,
        "scientific_name": c.scientific_name, "category": c.category, "season": c.season,
        "duration_days": c.duration_days, "water_need": c.water_need,
        "ph_range": [c.ideal_ph_min, c.ideal_ph_max],
        "nutrient_targets": {"n": c.n_target, "p": c.p_target, "k": c.k_target},
        "zones": c.zones, "description_en": c.description_en, "description_hi": c.description_hi,
        "calendar": _calendar(c),
    }


def _calendar(c: Crop) -> list[dict]:
    if c.season == "kharif":
        months = [6, 7, 10, 11]
    elif c.season == "rabi":
        months = [10, 11, 3, 4]
    elif c.season == "zaid":
        months = [3, 4, 6, 7]
    else:
        months = [6, 7, 6, 7]
    return [{"sow_from": months[0], "sow_to": months[1], "harvest_from": months[2], "harvest_to": months[3]}]


def disease_out(d: Disease, crop: Crop | None, treatments: list[dict] | None = None) -> dict:
    return {
        "slug": d.slug, "name_en": d.name_en, "name_hi": d.name_hi,
        "crop": {"slug": d.crop_slug, "name_en": crop.name_en, "name_hi": crop.name_hi} if crop else {"slug": d.crop_slug},
        "crop_slug": d.crop_slug,
        "pathogen_type": d.pathogen_type, "severity_default": d.severity_default,
        "symptoms_en": d.symptoms_en, "symptoms_hi": d.symptoms_hi,
        "spread_en": d.spread_en,
        "risk_window": {"humidity_min": d.risk_humidity_min, "temp_min": d.risk_temp_min, "temp_max": d.risk_temp_max},
        "treatments": treatments or [],
    }


def detection_list_out(det: Detection) -> dict:
    return {
        "id": det.id, "status": det.status, "confidence": det.confidence,
        "predicted_slug": det.predicted_slug,
        "crop_slug": det.crop_slug, "image_key": det.image_key,
        "review_status": det.review_status, "is_mock": det.is_mock,
        "created_at": iso(det.created_at),
    }
