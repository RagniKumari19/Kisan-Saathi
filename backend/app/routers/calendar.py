from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_user
from app.core.errors import NotFound
from app.core.utils import data
from app.models import Crop, CropPlan, District, Farm, PlanActivity, ReminderPreference, SoilReport, User
from app.schemas import (
    CropPlanIn, CropPlanPatch, PlanActivityIn, PlanActivityPatch, PlanAssistantIn, PlanProgressIn,
    ReminderPreferenceIn,
)
from app.services.calendar import MODEL_VERSION, assistant_answer, estimate_harvest, generate_activities, stage_for_day
from app.services.weather import get_weather

router = APIRouter(prefix="/plans", tags=["plans"])

DISCLAIMER = (
    "Dates are estimates based on crop duration and local season. "
    "Adjust for actual crop development and weather. Not a guarantee of yield."
)


async def _get_plan(db: AsyncSession, user: User, plan_id: str) -> CropPlan:
    plan = await db.get(CropPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise NotFound("Crop plan not found.")
    return plan


async def _load_activities(db: AsyncSession, plan_id: str) -> list[PlanActivity]:
    rows = (await db.execute(
        select(PlanActivity).where(PlanActivity.plan_id == plan_id).order_by(PlanActivity.scheduled_date, PlanActivity.created_at)
    )).scalars().all()
    return list(rows)


def _activity_out(a: PlanActivity) -> dict:
    return {
        "id": a.id, "plan_id": a.plan_id, "stage": a.stage, "activity_type": a.activity_type,
        "title_en": a.title_en, "title_hi": a.title_hi, "detail_en": a.detail_en, "detail_hi": a.detail_hi,
        "materials": a.materials or [], "importance": a.importance,
        "scheduled_date": a.scheduled_date.isoformat(),
        "weather_sensitive": a.weather_sensitive, "status": a.status,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "rescheduled_from": a.rescheduled_from.isoformat() if a.rescheduled_from else None,
        "is_custom": a.is_custom, "notes": a.notes,
        "reminder_enabled": a.reminder_enabled, "remind_days_before": a.remind_days_before,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


async def _plan_out(db: AsyncSession, plan: CropPlan, include_activities: bool = True) -> dict:
    farm = await db.get(Farm, plan.farm_id)
    crop = (await db.execute(select(Crop).where(Crop.slug == plan.crop_slug))).scalar_one_or_none()
    district = await db.get(District, farm.district_id) if farm else None
    acts = await _load_activities(db, plan.id) if include_activities else []
    today = date.today()
    days_since = (today - plan.sowing_date).days
    current_stage = plan.current_stage or (stage_for_day(crop, days_since) if crop else plan.current_stage)
    pending = [a for a in acts if a.status == "pending"]
    plan_started = plan.created_at.date() if plan.created_at else today
    overdue = [a for a in pending if plan_started <= a.scheduled_date < today]
    due_today = [a for a in pending if a.scheduled_date == today]
    upcoming = [a for a in pending if today < a.scheduled_date <= today + timedelta(days=7)]
    ahead = [a for a in pending if a.scheduled_date >= today] or pending
    return {
        "id": plan.id, "farm_id": plan.farm_id, "crop_slug": plan.crop_slug,
        "crop": {"slug": crop.slug, "name_en": crop.name_en, "name_hi": crop.name_hi,
                 "duration_days": crop.duration_days, "water_need": crop.water_need,
                 "season": crop.season} if crop else {"slug": plan.crop_slug},
        "farm": {"id": farm.id, "name": farm.name, "district": district.name if district else None,
                 "agro_zone": district.agro_zone if district else None} if farm else None,
        "name": plan.name or (crop.name_en if crop else plan.crop_slug),
        "sowing_date": plan.sowing_date.isoformat(),
        "expected_harvest_date": plan.expected_harvest_date.isoformat() if plan.expected_harvest_date else None,
        "farming_method": plan.farming_method, "status": plan.status,
        "current_stage": current_stage, "progress_pct": plan.progress_pct,
        "days_since_sowing": days_since, "notes": plan.notes,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "activities": [_activity_out(a) for a in acts] if include_activities else None,
        "summary": {
            "total_activities": len(acts),
            "completed": sum(1 for a in acts if a.status == "completed"),
            "pending": len(pending),
            "overdue": len(overdue),
            "due_today": len(due_today),
            "upcoming_7d": len(upcoming),
            "next_task": _activity_out(ahead[0]) if ahead else None,
        },
        "model_version": MODEL_VERSION,
        "disclaimer": DISCLAIMER,
    }


@router.get("")
async def list_plans(farm_id: str | None = None, user: User = Depends(current_user),
                     db: AsyncSession = Depends(get_db)):
    stmt = select(CropPlan).where(CropPlan.user_id == user.id).order_by(CropPlan.created_at.desc())
    if farm_id:
        stmt = stmt.where(CropPlan.farm_id == farm_id)
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for p in rows:
        # the list card shows pending/overdue counts and the next task, so load them
        payload = await _plan_out(db, p, include_activities=True)
        payload.pop("activities", None)
        out.append(payload)
    return data(out)


@router.get("/overview")
async def plans_overview(farm_id: str | None = None, user: User = Depends(current_user),
                        db: AsyncSession = Depends(get_db)):
    """One aggregated payload for the Home page section."""
    stmt = select(CropPlan).where(CropPlan.user_id == user.id, CropPlan.status == "active")
    if farm_id:
        stmt = stmt.where(CropPlan.farm_id == farm_id)
    rows = (await db.execute(stmt.order_by(CropPlan.created_at.desc()))).scalars().all()
    today = date.today()
    plans = []
    upcoming: list[dict] = []
    next_task = None
    harvest = None
    for p in rows:
        payload = await _plan_out(db, p, include_activities=True)
        plans.append({k: v for k, v in payload.items() if k != "activities"})
        started = p.created_at.date() if p.created_at else today
        for a in payload["activities"]:
            if a["status"] != "pending":
                continue
            scheduled = date.fromisoformat(a["scheduled_date"])
            item = {**a, "plan_name": payload["name"], "crop": payload["crop"]}
            # anything scheduled before the plan existed is history, not a to-do
            if scheduled < started:
                continue
            if scheduled <= today + timedelta(days=14):
                upcoming.append(item)
            if next_task is None or a["scheduled_date"] < next_task["scheduled_date"]:
                next_task = item
        if payload["expected_harvest_date"] and payload["expected_harvest_date"] >= today.isoformat():
            days_left = (date.fromisoformat(payload["expected_harvest_date"]) - today).days
            if harvest is None or days_left < harvest["days_left"]:
                harvest = {
                    "plan_id": p.id, "plan_name": payload["name"],
                    "crop": payload["crop"], "date": payload["expected_harvest_date"],
                    "days_left": days_left,
                }
    upcoming.sort(key=lambda a: (a["scheduled_date"], a["plan_name"]))
    return data({
        "plans": plans,
        "upcoming": upcoming[:10],
        "next_task": next_task,
        "harvest": harvest,
        "model_version": MODEL_VERSION,
        "disclaimer": DISCLAIMER,
    })


async def _reminder_prefs(db: AsyncSession, user: User) -> ReminderPreference:
    prefs = await db.get(ReminderPreference, user.id)
    if prefs is None:
        prefs = ReminderPreference(user_id=user.id, enabled=True, lead_days=2)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


def _prefs_out(prefs: ReminderPreference) -> dict:
    return {"enabled": prefs.enabled, "lead_days": prefs.lead_days}


@router.get("/reminders")
async def get_reminders(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return data(_prefs_out(await _reminder_prefs(db, user)))


@router.patch("/reminders")
async def patch_reminders(body: ReminderPreferenceIn, user: User = Depends(current_user),
                          db: AsyncSession = Depends(get_db)):
    prefs = await _reminder_prefs(db, user)
    if body.enabled is not None:
        prefs.enabled = body.enabled
    if body.lead_days is not None:
        prefs.lead_days = body.lead_days
    await db.commit()
    await db.refresh(prefs)
    return data(_prefs_out(prefs))


@router.get("/notifications")
async def list_notifications(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Upcoming and overdue task reminders, computed from the farmer's own plans.
n
    Reminders are generated on read, so no background scheduler is needed and a
    rescheduled or completed task disappears immediately.
    """
    prefs = await _reminder_prefs(db, user)
    if not prefs.enabled:
        return data({"preferences": _prefs_out(prefs), "items": [], "count": 0, "overdue": 0})
    rows = (await db.execute(
        select(CropPlan).where(CropPlan.user_id == user.id, CropPlan.status == "active")
    )).scalars().all()
    today = date.today()
    items: list[dict] = []
    for p in rows:
        payload = await _plan_out(db, p, include_activities=True)
        started = p.created_at.date() if p.created_at else today
        for a in payload["activities"]:
            if a["status"] != "pending" or not a["reminder_enabled"]:
                continue
            scheduled = date.fromisoformat(a["scheduled_date"])
            if scheduled < started:
                continue
            days_left = (scheduled - today).days
            lead = a["remind_days_before"] if a["remind_days_before"] is not None else prefs.lead_days
            if days_left > lead or days_left < -7:
                continue
            items.append({
                "activity_id": a["id"], "plan_id": p.id, "plan_name": payload["name"],
                "crop": payload["crop"], "farm": payload["farm"],
                "title_en": a["title_en"], "title_hi": a["title_hi"],
                "activity_type": a["activity_type"], "importance": a["importance"],
                "scheduled_date": a["scheduled_date"], "days_left": days_left,
                "kind": "overdue" if days_left < 0 else "today" if days_left == 0 else "upcoming",
            })
    items.sort(key=lambda i: (i["scheduled_date"], i["plan_name"]))
    return data({
        "preferences": _prefs_out(prefs),
        "items": items[:20],
        "count": sum(1 for i in items if i["days_left"] >= 0),
        "overdue": sum(1 for i in items if i["days_left"] < 0),
    })


@router.post("", status_code=201)
async def create_plan(body: CropPlanIn, user: User = Depends(current_user),
                      db: AsyncSession = Depends(get_db)):
    farm = await db.get(Farm, body.farm_id)
    if farm is None or farm.user_id != user.id:
        raise NotFound("Farm not found.")
    crop = (await db.execute(select(Crop).where(Crop.slug == body.crop_slug))).scalar_one_or_none()
    if crop is None:
        raise NotFound("Crop not found.")
    plan = CropPlan(
        user_id=user.id, farm_id=farm.id, crop_slug=body.crop_slug,
        name=body.name, sowing_date=body.sowing_date,
        farming_method=body.farming_method,
        expected_harvest_date=estimate_harvest(body.sowing_date, crop),
        current_stage=stage_for_day(crop, (date.today() - body.sowing_date).days),
        progress_pct=0.0,
    )
    db.add(plan)
    await db.flush()
    for a in generate_activities(plan.id, user.id, crop, farm, body.sowing_date, body.farming_method):
        db.add(PlanActivity(**a))
    await db.commit()
    await db.refresh(plan)
    return data(await _plan_out(db, plan, include_activities=True))


@router.get("/{plan_id}")
async def get_plan(plan_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    # weather alerts
    farm = await db.get(Farm, plan.farm_id)
    district = await db.get(District, farm.district_id) if farm else None
    weather = None
    alerts = []
    if farm and district:
        try:
            weather = await get_weather(db, farm, district)
        except Exception:
            weather = None
    if weather:
        daily = weather.get("daily", [])
        rain3 = sum(d.get("rain_mm", 0) for d in daily[:3])
        dry_day = next((d for d in daily[:5] if (d.get("rain_mm") or 0) < 2), None)
        suggested = dry_day.get("date") if dry_day else None
        acts = await _load_activities(db, plan.id)
        today = date.today()
        for a in acts:
            if a.status != "pending":
                continue
            if not (today <= a.scheduled_date <= today + timedelta(days=7)):
                continue
            if not a.weather_sensitive:
                continue
            if a.activity_type in ("irrigation", "sowing", "fertilizer") and rain3 >= 25:
                alerts.append({
                    "activity_id": a.id, "title": a.title_en, "date": a.scheduled_date.isoformat(),
                    "severity": "warning", "suggested_date": suggested,
                    "message": f"Heavy rain (~{rain3:.0f} mm) expected. Consider delaying {a.title_en.lower()} and checking drainage."
                               + (f" A drier day is forecast on {suggested}, if the forecast holds." if suggested else ""),
                })
            if a.activity_type == "harvest" and rain3 >= 10:
                alerts.append({
                    "activity_id": a.id, "title": a.title_en, "date": a.scheduled_date.isoformat(),
                    "severity": "warning", "suggested_date": suggested,
                    "message": "Rain expected near harvest. Plan to harvest in a dry window and dry produce well."
                               + (f" A drier day is forecast on {suggested}." if suggested else ""),
                })
    payload = await _plan_out(db, plan, include_activities=True)
    payload["weather"] = {
        "current": weather.get("current") if weather else None,
        "daily": (weather.get("daily") or [])[:5] if weather else [],
        "provenance": weather.get("provenance") if weather else None,
        "alerts": alerts,
    }
    return data(payload)


@router.patch("/{plan_id}")
async def patch_plan(plan_id: str, body: CropPlanPatch, user: User = Depends(current_user),
                     db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    if body.name is not None:
        plan.name = body.name
    if body.sowing_date is not None:
        plan.sowing_date = body.sowing_date
        crop = (await db.execute(select(Crop).where(Crop.slug == plan.crop_slug))).scalar_one_or_none()
        if crop:
            plan.expected_harvest_date = estimate_harvest(body.sowing_date, crop)
    if body.farming_method is not None:
        plan.farming_method = body.farming_method
    if body.status is not None:
        plan.status = body.status
    if body.current_stage is not None:
        plan.current_stage = body.current_stage
    if body.progress_pct is not None:
        plan.progress_pct = body.progress_pct
    if body.notes is not None:
        plan.notes = body.notes
    await db.commit()
    await db.refresh(plan)
    return data(await _plan_out(db, plan, include_activities=True))


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    # explicit delete: SQLite does not enforce ON DELETE CASCADE by default
    for act in await _load_activities(db, plan.id):
        await db.delete(act)
    await db.delete(plan)
    await db.commit()
    return None


@router.post("/{plan_id}/activities", status_code=201)
async def add_activity(plan_id: str, body: PlanActivityIn, user: User = Depends(current_user),
                      db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    act = PlanActivity(
        plan_id=plan.id, user_id=user.id,
        stage=body.stage, activity_type=body.activity_type,
        title_en=body.title_en, title_hi=body.title_hi or body.title_en,
        detail_en=body.detail_en or "", detail_hi=body.detail_hi or body.detail_en or "",
        materials=body.materials or [], importance=body.importance,
        scheduled_date=body.scheduled_date, weather_sensitive=body.weather_sensitive,
        status="pending", is_custom=True,
    )
    db.add(act)
    await db.commit()
    await db.refresh(act)
    return data(_activity_out(act))


@router.patch("/{plan_id}/activities/{activity_id}")
async def patch_activity(plan_id: str, activity_id: str, body: PlanActivityPatch,
                        user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    act = await db.get(PlanActivity, activity_id)
    if act is None or act.plan_id != plan.id:
        raise NotFound("Activity not found.")
    if body.title_en is not None:
        act.title_en = body.title_en
    if body.title_hi is not None:
        act.title_hi = body.title_hi
    if body.detail_en is not None:
        act.detail_en = body.detail_en
    if body.detail_hi is not None:
        act.detail_hi = body.detail_hi
    if body.scheduled_date is not None:
        if body.scheduled_date != act.scheduled_date:
            act.rescheduled_from = act.scheduled_date
        act.scheduled_date = body.scheduled_date
    if body.status is not None:
        act.status = body.status
        if body.status == "completed":
            from datetime import datetime
            act.completed_at = datetime.utcnow()
        else:
            act.completed_at = None
    if body.notes is not None:
        act.notes = body.notes
    if body.reminder_enabled is not None:
        act.reminder_enabled = body.reminder_enabled
    # explicit null means "go back to the farmer's default lead time"
    if "remind_days_before" in body.model_fields_set:
        act.remind_days_before = body.remind_days_before
    await db.commit()
    await db.refresh(act)
    return data(_activity_out(act))


@router.post("/{plan_id}/progress")
async def update_progress(plan_id: str, body: PlanProgressIn, user: User = Depends(current_user),
                         db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    if body.current_stage is not None:
        plan.current_stage = body.current_stage
    if body.progress_pct is not None:
        plan.progress_pct = body.progress_pct
    if body.notes is not None:
        plan.notes = body.notes
    await db.commit()
    await db.refresh(plan)
    return data(await _plan_out(db, plan, include_activities=True))


@router.post("/{plan_id}/assistant")
async def ask_assistant(plan_id: str, body: PlanAssistantIn, user: User = Depends(current_user),
                       db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(db, user, plan_id)
    acts = await _load_activities(db, plan.id)
    plan_dict = {
        "activities": [_activity_out(a) for a in acts],
        "sowing_date": plan.sowing_date.isoformat(),
        "expected_harvest_date": plan.expected_harvest_date.isoformat() if plan.expected_harvest_date else None,
        "current_stage": plan.current_stage,
        "started": (plan.created_at.date() if plan.created_at else date.today()).isoformat(),
    }
    farm = await db.get(Farm, plan.farm_id)
    district = await db.get(District, farm.district_id) if farm else None
    weather = None
    if farm and district:
        try:
            weather = await get_weather(db, farm, district)
        except Exception:
            weather = None
    answer = assistant_answer(plan_dict, body.question, weather)
    return data({"question": body.question, "answer": answer, "model_version": MODEL_VERSION})
