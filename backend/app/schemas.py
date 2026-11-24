"""Request models. Response shaping is done in routers/services for provenance control."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RegisterIn(BaseModel):
    phone: str = Field(min_length=10, max_length=16)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    language: Literal["en", "hi", "mr"] = "en"

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, v: str) -> str:
        digits = v.replace("+", "").replace(" ", "").replace("-", "")
        if not digits.isdigit() or not 10 <= len(digits) <= 15:
            raise ValueError("Enter a valid phone number.")
        return v


class LoginIn(BaseModel):
    phone: str
    password: str


class OtpRequestIn(BaseModel):
    phone: str = Field(min_length=10, max_length=16)
    purpose: Literal["signup", "login", "recovery"] = "login"
    full_name: str | None = Field(default=None, max_length=120)
    language: Literal["en", "hi", "mr"] = "en"


class OtpVerifyIn(BaseModel):
    request_id: str = Field(min_length=10, max_length=64)
    code: str = Field(min_length=4, max_length=8)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    language: Literal["en", "hi", "mr"] | None = None


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    district_id: str | None = None
    district_slug: str | None = None
    village: str | None = Field(default=None, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    area_acres: float | None = Field(default=None, gt=0, le=10000)
    soil_type: Literal["black", "red", "alluvial", "laterite", "sandy", "unknown"] | None = "unknown"
    irrigation_source: Literal["borewell", "well", "canal", "tank", "river", "rainfed", "other"] | None = "rainfed"
    primary_crop_slug: str | None = None
    is_primary: bool = False


class FarmPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    village: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_acres: float | None = Field(default=None, gt=0, le=10000)
    soil_type: str | None = None
    irrigation_source: str | None = None
    primary_crop_slug: str | None = None


class SoilIn(BaseModel):
    farm_id: str
    crop_slug: str | None = None
    tested_on: date | None = None
    source: Literal["manual", "lab_report", "card"] = "manual"
    nitrogen_kg_ha: float | None = Field(default=None, ge=0, le=2000)
    phosphorus_kg_ha: float | None = Field(default=None, ge=0, le=1000)
    potassium_kg_ha: float | None = Field(default=None, ge=0, le=2000)
    ph: float | None = Field(default=None, ge=0, le=14)
    organic_carbon_pct: float | None = Field(default=None, ge=0, le=20)
    ec_ds_m: float | None = Field(default=None, ge=0, le=50)
    lab_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class RecommendIn(BaseModel):
    farm_id: str
    season: Literal["kharif", "rabi", "zaid"] = "rabi"
    save: bool = True


class ReviewIn(BaseModel):
    decision: Literal["confirmed", "corrected", "rejected"]
    disease_slug: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class RoleIn(BaseModel):
    role: Literal["farmer", "expert", "admin"]


class CropPlanIn(BaseModel):
    farm_id: str
    crop_slug: str
    sowing_date: date
    farming_method: Literal["organic", "conventional", "mixed"] = "conventional"
    name: str | None = Field(default=None, max_length=120)


class CropPlanPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    sowing_date: date | None = None
    farming_method: Literal["organic", "conventional", "mixed"] | None = None
    status: Literal["active", "completed", "archived"] | None = None
    current_stage: str | None = None
    progress_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class PlanActivityIn(BaseModel):
    stage: str = "custom"
    activity_type: str = "custom"
    title_en: str = Field(min_length=1, max_length=160)
    title_hi: str | None = Field(default=None, max_length=160)
    detail_en: str | None = Field(default=None, max_length=2000)
    detail_hi: str | None = Field(default=None, max_length=2000)
    materials: list[str] | None = None
    importance: Literal["low", "medium", "high"] = "medium"
    scheduled_date: date
    weather_sensitive: bool = False


class PlanActivityPatch(BaseModel):
    title_en: str | None = Field(default=None, max_length=160)
    title_hi: str | None = None
    detail_en: str | None = None
    detail_hi: str | None = None
    scheduled_date: date | None = None
    status: Literal["pending", "completed", "skipped", "rescheduled"] | None = None
    notes: str | None = Field(default=None, max_length=1000)
    reminder_enabled: bool | None = None
    remind_days_before: int | None = Field(default=None, ge=0, le=30)


class ReminderPreferenceIn(BaseModel):
    enabled: bool | None = None
    lead_days: int | None = Field(default=None, ge=0, le=14)


class PlanProgressIn(BaseModel):
    current_stage: str | None = None
    progress_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class PlanAssistantIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
