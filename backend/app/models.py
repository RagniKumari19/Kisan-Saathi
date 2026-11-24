"""SQLAlchemy models for the farmer assistance platform.

Portable by design: the development environment runs SQLite, production runs
PostgreSQL. UUIDs are stored as 36-char strings and JSON columns use the
portable ``JSON`` type, so the same models work on both.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, utcnow


def _uuid() -> str:
    import uuid

    return str(uuid.uuid4())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Null for accounts created through phone verification, which have no password.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="farmer")
    language: Mapped[str] = mapped_column(String(4), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class OtpChallenge(Base):
    """A single-use phone verification challenge. Only a keyed hash of the code is stored."""

    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)  # signup | login | recovery
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    request_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_otp_challenges_phone_created", "phone", "created_at"),
        Index("ix_otp_challenges_ip_created", "request_ip", "created_at"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replaced_by_id: Mapped[str | None] = mapped_column(String(36))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class District(Base):
    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    agro_zone: Mapped[str] = mapped_column(String(40), nullable=False)


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=False)
    village: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    area_acres: Mapped[float | None] = mapped_column(Float)
    soil_type: Mapped[str | None] = mapped_column(String(24))
    irrigation_source: Mapped[str | None] = mapped_column(String(24))
    primary_crop_slug: Mapped[str | None] = mapped_column(String(40))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(60), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(60), nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    season: Mapped[str] = mapped_column(String(12), nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    water_need: Mapped[str] = mapped_column(String(12), nullable=False, default="medium")
    ideal_ph_min: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    ideal_ph_max: Mapped[float] = mapped_column(Float, nullable=False, default=7.5)
    n_target: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    p_target: Mapped[float] = mapped_column(Float, nullable=False, default=50)
    k_target: Mapped[float] = mapped_column(Float, nullable=False, default=50)
    zones: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SoilReport(Base):
    __tablename__ = "soil_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    tested_on: Mapped[date | None] = mapped_column(Date)
    nitrogen_kg_ha: Mapped[float | None] = mapped_column(Float)
    phosphorus_kg_ha: Mapped[float | None] = mapped_column(Float)
    potassium_kg_ha: Mapped[float | None] = mapped_column(Float)
    ph: Mapped[float | None] = mapped_column(Float)
    organic_carbon_pct: Mapped[float | None] = mapped_column(Float)
    ec_ds_m: Mapped[float | None] = mapped_column(Float)
    lab_name: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class SoilAnalysis(Base):
    __tablename__ = "soil_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    soil_report_id: Mapped[str] = mapped_column(
        ForeignKey("soil_reports.id", ondelete="CASCADE"), nullable=False
    )
    crop_slug: Mapped[str | None] = mapped_column(String(40))
    statuses: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False, default="soil-rules-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class CropRecommendation(Base):
    __tablename__ = "crop_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    season: Mapped[str] = mapped_column(String(12), nullable=False)
    input_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suppressed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    location_key: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("location_key", "kind", name="uq_weather_snapshots_key"),)


class Disease(Base):
    __tablename__ = "crop_diseases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    crop_slug: Mapped[str] = mapped_column(String(40), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(100), nullable=False)
    pathogen_type: Mapped[str] = mapped_column(String(24), nullable=False)
    symptoms_en: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms_hi: Mapped[str] = mapped_column(Text, nullable=False)
    spread_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity_default: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    risk_humidity_min: Mapped[int | None] = mapped_column(Integer)
    risk_temp_min: Mapped[int | None] = mapped_column(Integer)
    risk_temp_max: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Treatment(Base):
    __tablename__ = "disease_treatments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    disease_slug: Mapped[str] = mapped_column(String(60), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(160))
    safety_notes: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    last_verified: Mapped[date] = mapped_column(Date, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Detection(Base):
    __tablename__ = "disease_detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[str | None] = mapped_column(String(36))
    crop_slug: Mapped[str | None] = mapped_column(String(40))
    image_key: Mapped[str] = mapped_column(Text, nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_slug: Mapped[str | None] = mapped_column(String(60))
    confidence: Mapped[float | None] = mapped_column(Float)
    top_k: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    model_name: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    expert_id: Mapped[str | None] = mapped_column(String(36))
    expert_slug: Mapped[str | None] = mapped_column(String(60))
    expert_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_detections_user_created", "user_id", "created_at"),
        Index("ix_detections_review", "review_status"),
    )


class Commodity(Base):
    __tablename__ = "commodities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(80), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MandiPrice(Base):
    __tablename__ = "mandi_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), nullable=False)
    commodity: Mapped[str] = mapped_column(String(60), nullable=False)
    variety: Mapped[str] = mapped_column(String(80), nullable=False, default="Other")
    grade: Mapped[str] = mapped_column(String(20), nullable=False, default="FAQ")
    arrival_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(12), nullable=False, default="quintal")
    source: Mapped[str] = mapped_column(String(24), nullable=False, default="demo_seed")
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "market_id", "commodity", "variety", "grade", "arrival_date",
            name="uq_mandi_prices_key",
        ),
        Index("ix_mandi_prices_commodity_date", "commodity", "arrival_date"),
        Index("ix_mandi_prices_market_date", "market_id", "arrival_date"),
    )


class MspRate(Base):
    __tablename__ = "msp_rates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    commodity: Mapped[str] = mapped_column(String(60), nullable=False)
    season: Mapped[str] = mapped_column(String(12), nullable=False)
    marketing_year: Mapped[str] = mapped_column(String(9), nullable=False)
    price_per_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date] = mapped_column(Date, nullable=False)
    last_verified: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("commodity", "season", "marketing_year", name="uq_msp_key"),
    )


class IngestionRun(Base):
    __tablename__ = "price_ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    target_date: Mapped[date | None] = mapped_column(Date)
    rows_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class CropPlan(Base, TimestampMixin):
    __tablename__ = "crop_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    crop_slug: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    sowing_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date)
    farming_method: Mapped[str] = mapped_column(String(16), nullable=False, default="conventional")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    current_stage: Mapped[str] = mapped_column(String(24), nullable=False, default="land_preparation")
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_crop_plans_user_created", "user_id", "created_at"),)


class PlanActivity(Base, TimestampMixin):
    __tablename__ = "plan_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(ForeignKey("crop_plans.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(24), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title_en: Mapped[str] = mapped_column(String(160), nullable=False)
    title_hi: Mapped[str] = mapped_column(String(160), nullable=False)
    detail_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail_hi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    materials: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    importance: Mapped[str] = mapped_column(String(12), nullable=False, default="medium")
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    rescheduled_from: Mapped[date | None] = mapped_column(Date)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    # Reminders: None means "use the farmer's default lead time".
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remind_days_before: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_plan_activities_plan_date", "plan_id", "scheduled_date"),)


class ReminderPreference(Base, TimestampMixin):
    """Per-farmer defaults for task reminders. Created on first read."""

    __tablename__ = "reminder_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    entity: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
