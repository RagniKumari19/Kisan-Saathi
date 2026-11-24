import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useFarms } from "../session";
import { useI18n } from "../i18n";
import { Empty, ErrorNote, FarmGate, Field, Loading, MockBadge, PageHead } from "../ui";

const STAGES = [
  "land_preparation", "sowing", "initial_growth", "vegetative", "flowering", "harvesting",
] as const;

const ACTIVITY_TYPES = [
  "land_preparation", "sowing", "irrigation", "fertilizer",
  "pest_management", "monitoring", "weed_management", "harvest", "custom",
];

export function seasonForToday(): "kharif" | "rabi" | "zaid" {
  const m = new Date().getMonth() + 1;
  if (m >= 6 && m <= 10) return "kharif";
  if (m === 11 || m <= 3) return "rabi";
  return "zaid";
}

function ymd(d: Date): string {
  const m = `${d.getMonth() + 1}`.padStart(2, "0");
  const day = `${d.getDate()}`.padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function parseDay(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function fmtDay(s: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }) {
  return parseDay(s).toLocaleDateString(undefined, opts);
}

function typeTone(type: string): string {
  return `type-${ACTIVITY_TYPES.includes(type) ? type : "custom"}`;
}

function typeKey(type: string): string {
  return `type_${ACTIVITY_TYPES.includes(type) ? type : "custom"}`;
}

export function ActivityBadge({ type }: { type: string }) {
  const { t } = useI18n();
  return <span className={`cal-type ${typeTone(type)}`}>{t(typeKey(type))}</span>;
}

/* ---------------------------------------------------------------- hub ---- */

export function CalendarHub() {
  const { t, pick } = useI18n();
  const { farms } = useFarms();
  const [plans, setPlans] = useState<any[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [notif, setNotif] = useState<any>(null);
  const [prefBusy, setPrefBusy] = useState(false);

  const load = () => {
    setLoading(true);
    api.get("/plans")
      .then((r) => setPlans(r.data))
      .catch(setError)
      .finally(() => setLoading(false));
  };

  const loadNotifs = () => {
    api.get("/plans/notifications").then((r) => setNotif(r.data)).catch(() => setNotif(null));
  };

  useEffect(() => { load(); loadNotifs(); }, []);

  async function savePrefs(body: Record<string, unknown>) {
    setPrefBusy(true);
    try {
      await api.patch("/plans/reminders", body);
      loadNotifs();
    } finally {
      setPrefBusy(false);
    }
  }

  const season = seasonForToday();
  const farmName = (id: string) => farms.find((f) => f.id === id)?.name;

  return (
    <>
      <PageHead title={t("calendar_title")} lead={t("calendar_lead")} back="/app/plan" />
      <div className="card tinted">
        <div className="row between wrap" style={{ gap: "0.75rem" }}>
          <div>
            <span className="eyebrow">{t("current_season")}</span>
            <h2 style={{ margin: 0 }}>{t(season)}</h2>
          </div>
          <Link className="btn btn-primary" to="/app/plan/calendar/new">{t("create_crop_plan")}</Link>
        </div>
      </div>

      <section className="card">
        <div className="row between wrap">
          <div>
            <span className="eyebrow">{t("notifications")}</span>
            <h2 style={{ margin: 0 }}>{t("reminders")}</h2>
          </div>
          {notif?.count > 0 && <span className="pill warn">{notif.count}</span>}
        </div>
        <p className="small muted" style={{ marginTop: "0.4rem" }}>{t("reminders_sub")}</p>

        <div className="row wrap" style={{ gap: "0.8rem", marginTop: "0.5rem", alignItems: "center" }}>
          <label className="row" style={{ gap: "0.4rem", minHeight: 44 }}>
            <input
              type="checkbox"
              checked={notif?.preferences?.enabled ?? true}
              disabled={prefBusy || !notif}
              onChange={(e) => void savePrefs({ enabled: e.target.checked })}
            />
            <span className="small">{t("reminder_on")}</span>
          </label>
          <label className="row" style={{ gap: "0.4rem", minHeight: 44 }}>
            <span className="small muted">{t("reminder_lead")}</span>
            <select
              className="select"
              style={{ maxWidth: 190 }}
              value={notif?.preferences?.lead_days ?? 2}
              disabled={prefBusy || !notif || notif.preferences?.enabled === false}
              onChange={(e) => void savePrefs({ lead_days: Number(e.target.value) })}
            >
              {[[0, "remind_same_day"], [1, "remind_one_day"], [2, "remind_two_days"], [3, "remind_three_days"], [7, "remind_week"]].map(([v, k]) => (
                <option key={v} value={v}>{t(k as string)}</option>
              ))}
            </select>
          </label>
        </div>

        {notif && notif.preferences?.enabled === false && <p className="small muted" style={{ marginTop: "0.5rem" }}>{t("notifications_off")}</p>}
        {notif?.items?.length > 0 && (
          <ul className="list cal-list" style={{ marginTop: "0.5rem" }}>
            {notif.items.map((n: any) => (
              <li key={n.activity_id}>
                <Link className="cal-row" to={`/app/plan/calendar/${n.plan_id}`}>
                  <i className={`dot ${typeTone(n.activity_type)}`} />
                  <span className="cal-row-main">
                    <strong>{pick(n.title_en, n.title_hi)}</strong>
                    <span className="small muted">{fmtDay(n.scheduled_date, { weekday: "short", day: "numeric", month: "short" })} · {n.plan_name}</span>
                  </span>
                  <span className={`pill ${n.kind === "overdue" ? "bad" : n.kind === "today" ? "warn" : "good"}`}>
                    {n.kind === "overdue" ? t("overdue") : n.kind === "today" ? t("due_today") : `${n.days_left} ${t("days_short")}`}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        {notif && notif.preferences?.enabled !== false && notif.items?.length === 0 && (
          <p className="small muted" style={{ marginTop: "0.5rem" }}>{t("no_notifications")}</p>
        )}
      </section>

      {loading && <Loading />}
      {error !== null && <ErrorNote error={error} onRetry={load} />}

      {!loading && plans && plans.length === 0 && (
        <div className="card">
          <Empty title={t("no_plans_title")} body={t("no_plans_body")} action={
            <Link className="btn btn-primary" to="/app/plan/calendar/new">{t("create_crop_plan")}</Link>
          } />
        </div>
      )}

      {plans && plans.length > 0 && <h2>{t("active_plans")}</h2>}
      {plans?.map((p) => (
        <Link key={p.id} className="card link" to={`/app/plan/calendar/${p.id}`}>
          <div className="row between wrap">
            <div>
              <h3 style={{ margin: 0 }}>{p.name}</h3>
              <span className="small muted">
                {p.farm?.name ?? farmName(p.farm_id)} · {t(`stage_${p.current_stage}`)} · {t(`method_${p.farming_method}`)}
              </span>
            </div>
            <span className={`pill ${p.summary?.overdue ? "bad" : "good"}`}>
              {p.summary?.overdue ? `${p.summary.overdue} ${t("overdue")}` : t("pending_tasks") + " " + p.summary?.pending}
            </span>
          </div>
          <div className="meter" style={{ marginTop: "0.7rem" }}>
            <span style={{ width: `${Math.min(100, Math.max(0, p.progress_pct || 0))}%` }} />
          </div>
          <p className="small muted" style={{ margin: "0.5rem 0 0" }}>
            {t("sowing_date")} {fmtDay(p.sowing_date)} · {t("estimated_harvest")} {p.expected_harvest_date ? fmtDay(p.expected_harvest_date) : "—"}
          </p>
          {p.summary?.next_task && (
            <p className="small" style={{ margin: "0.35rem 0 0" }}>
              {t("next_task")}: <strong>{pick(p.summary.next_task.title_en, p.summary.next_task.title_hi)}</strong>{" "}
              <span className="muted">({fmtDay(p.summary.next_task.scheduled_date)})</span>
            </p>
          )}
        </Link>
      ))}
    </>
  );
}

/* --------------------------------------------------------- create plan ---- */

export function NewPlanPage() {
  const { t, name, pick } = useI18n();
  const { farms, farm: selectedFarm } = useFarms();
  const navigate = useNavigate();
  const [crops, setCrops] = useState<any[]>([]);
  const [farmId, setFarmId] = useState(selectedFarm?.id ?? "");
  const [cropSlug, setCropSlug] = useState(selectedFarm?.primary_crop_slug ?? "");
  const [sowingDate, setSowingDate] = useState(ymd(new Date()));
  const [method, setMethod] = useState<"organic" | "conventional" | "mixed">("conventional");
  const [soil, setSoil] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const season = seasonForToday();

  const farm = farms.find((f) => f.id === farmId) ?? null;

  useEffect(() => {
    api.get("/crops").then((r) => setCrops(r.data)).catch(() => setCrops([]));
  }, []);

  // Auto-select the first crop in the current season so we don't re-ask for what we can infer.
  useEffect(() => {
    if (cropSlug || crops.length === 0) return;
    const first = crops.find((c) => c.season === season) ?? crops.find((c) => c.season === "perennial") ?? crops[0];
    if (first) setCropSlug(first.slug);
  }, [crops, cropSlug, season]);

  useEffect(() => {
    if (!selectedFarm && !farmId && farms[0]) {
      setFarmId(farms[0].id);
      setCropSlug(farms[0].primary_crop_slug ?? "");
    }
  }, [farms, selectedFarm, farmId]);

  useEffect(() => {
    if (!farmId) return;
    let alive = true;
    api.get(`/soil/reports?farm_id=${farmId}`)
      .then((r) => alive && setSoil(r.data?.[0] ?? null))
      .catch(() => alive && setSoil(null));
    return () => { alive = false; };
  }, [farmId]);

  async function submit() {
    if (!farmId || !cropSlug) {
      setError(new Error(t("select_crop")));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.post("/plans", {
        farm_id: farmId,
        crop_slug: cropSlug,
        sowing_date: sowingDate,
        farming_method: method,
      });
      navigate(`/app/plan/calendar/${res.data.id}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead title={t("new_plan_title")} lead={t("new_plan_lead")} back="/app/plan/calendar" />
      <FarmGate>
        {() => (
          <form className="card" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
            {farms.length > 1 && (
              <Field label={t("choose_farm")}>
                <select className="select" value={farmId} onChange={(e) => {
                  const next = farms.find((f) => f.id === e.target.value);
                  setFarmId(e.target.value);
                  if (next?.primary_crop_slug) setCropSlug(next.primary_crop_slug);
                }}>
                  {farms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </Field>
            )}

            <Field label={t("select_crop")} hint={farm?.district ? `${farm.district.name} · ${farm.district.agro_zone.replace(/_/g, " ")}` : undefined}>
              <select className="select" value={cropSlug} onChange={(e) => setCropSlug(e.target.value)}>
                <option value="">—</option>
                {crops
                  .filter((c) => c.season === season || c.season === "perennial")
                  .map((c) => <option key={c.slug} value={c.slug}>{name(c)} · {c.duration_days ?? "?"} days</option>)}
                {crops.filter((c) => c.season !== season && c.season !== "perennial").length > 0 && (
                  <optgroup label={pick("Other seasons", "अन्य सीज़न")}>
                    {crops
                      .filter((c) => c.season !== season && c.season !== "perennial")
                      .map((c) => <option key={c.slug} value={c.slug}>{name(c)} · {c.season}</option>)}
                  </optgroup>
                )}
              </select>
            </Field>

            <Field label={t("sowing_date")} hint={pick("Use the date you actually sowed, or plan ahead.", "जिस दिन वास्तव में बुवाई की उस तारीख को डालें, या आगे की योजना बनाएं।")}>
              <input className="input" type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} />
            </Field>

            <Field label={t("farming_method")}>
              <select className="select" value={method} onChange={(e) => setMethod(e.target.value as any)}>
                <option value="conventional">{t("method_conventional")}</option>
                <option value="organic">{t("method_organic")}</option>
                <option value="mixed">{t("method_mixed")}</option>
              </select>
            </Field>

            <div className="cal-profile">
              <span className="eyebrow">{t("from_profile")}</span>
              <dl style={{ margin: 0 }}>
                <div className="kv"><dt>{t("area_acres")}</dt><dd>{farm?.area_acres ?? "—"}</dd></div>
                <div className="kv"><dt>{t("soil_type")}</dt><dd>{farm?.soil_type ?? "—"}</dd></div>
                <div className="kv"><dt>{t("irrigation")}</dt><dd>{farm?.irrigation_source ?? "—"}</dd></div>
                <div className="kv"><dt>{t("ph")}</dt><dd>{soil?.ph ?? "—"}</dd></div>
              </dl>
              {!soil && <p className="small muted" style={{ margin: "0.4rem 0 0" }}>{t("no_soil_test_hint")}</p>}
            </div>

            {error !== null && <ErrorNote error={error} />}

            <button className="btn btn-primary btn-block" type="submit" disabled={busy} aria-busy={busy}>
              {busy ? <><span className="spinner" aria-hidden="true" />{t("saving")}</> : t("create_plan")}
            </button>
            <p className="footer-note">{t("estimated_dates_note")}</p>
          </form>
        )}
      </FarmGate>
    </>
  );
}

/* ------------------------------------------------------- activity sheet ---- */

function ActivitySheet({
  activity, onClose, onPatch,
}: {
  activity: any;
  onClose: () => void;
  onPatch: (body: Record<string, unknown>) => Promise<void>;
}) {
  const { t, pick } = useI18n();
  const [date, setDate] = useState(activity.scheduled_date);
  const [busy, setBusy] = useState(false);
  const [reminder, setReminder] = useState<string>(
    activity.reminder_enabled === false ? "off" : activity.remind_days_before == null ? "default" : String(activity.remind_days_before),
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function run(body: Record<string, unknown>) {
    setBusy(true);
    try {
      await onPatch(body);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sheet-overlay" onClick={onClose} role="presentation">
      <div className="sheet cal-sheet" role="dialog" aria-modal="true" aria-label={t("activity_details")} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-grip" />
        <div className="row between wrap" style={{ gap: "0.5rem" }}>
          <div>
            <span className="eyebrow">{t(`stage_${activity.stage}`)}</span>
            <h2 style={{ margin: 0 }}>{pick(activity.title_en, activity.title_hi)}</h2>
          </div>
          <span className={`pill ${activity.status === "completed" ? "good" : "warn"}`}>
            {activity.status === "completed" ? t("completed_tasks") : t("pending_tasks")}
          </span>
        </div>
        <div style={{ marginTop: "0.6rem" }}><ActivityBadge type={activity.activity_type} /></div>

        <dl style={{ marginTop: "0.7rem" }}>
          <div className="kv"><dt>{t("scheduled_date")}</dt><dd>{fmtDay(activity.scheduled_date, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}</dd></div>
          {activity.rescheduled_from && (
            <div className="kv"><dt>{t("reschedule")}</dt><dd className="muted">{fmtDay(activity.rescheduled_from)} → {fmtDay(activity.scheduled_date)}</dd></div>
          )}
          <div className="kv"><dt>{t("importance")}</dt><dd>{t(`importance_${activity.importance}`)}</dd></div>
        </dl>

        {activity.detail_en && (
          <>
            <h3 style={{ marginTop: "0.5rem" }}>{t("instructions")}</h3>
            <p className="small" style={{ margin: 0 }}>{pick(activity.detail_en, activity.detail_hi)}</p>
          </>
        )}

        {activity.materials?.length > 0 && (
          <>
            <h3 style={{ marginTop: "0.7rem" }}>{t("materials")}</h3>
            <ul className="small" style={{ margin: 0, paddingLeft: "1.1rem" }}>
              {activity.materials.map((m: string) => <li key={m}>{m}</li>)}
            </ul>
          </>
        )}

        {activity.weather_sensitive && (
          <p className="footer-note">{pick("Weather-sensitive activity: check the forecast before starting.", "मौसम पर निर्भर काम: शुरू करने से पहले पूर्वानुमान देखें।")}</p>
        )}

        <div className="row wrap" style={{ gap: "0.5rem", marginTop: "0.8rem" }}>
          <button
            className="btn btn-primary btn-sm"
            disabled={busy}
            onClick={() => void run({ status: activity.status === "completed" ? "pending" : "completed" })}
          >
            {activity.status === "completed" ? t("mark_pending") : t("mark_complete")}
          </button>
          <Link className="btn btn-secondary btn-sm" to="/app/protect/capture">{t("check_leaf")}</Link>
        </div>

        <Field label={t("remind_me")}>
          <select
            className="select"
            value={reminder}
            disabled={busy}
            onChange={(e) => {
              const v = e.target.value;
              setReminder(v);
              void run(
                v === "off"
                  ? { reminder_enabled: false }
                  : v === "default"
                    ? { reminder_enabled: true, remind_days_before: null }
                    : { reminder_enabled: true, remind_days_before: Number(v) },
              );
            }}
          >
            <option value="default">{t("use_default_reminder")}</option>
            <option value="off">{t("no_reminder")}</option>
            <option value="0">{t("remind_same_day")}</option>
            <option value="1">{t("remind_one_day")}</option>
            <option value="2">{t("remind_two_days")}</option>
            <option value="3">{t("remind_three_days")}</option>
            <option value="7">{t("remind_week")}</option>
          </select>
        </Field>

        <div className="cal-reschedule">
          <Field label={t("reschedule")}>
            <div className="row" style={{ gap: "0.5rem" }}>
              <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              <button
                className="btn btn-secondary btn-sm"
                disabled={busy || date === activity.scheduled_date}
                onClick={() => void run({ scheduled_date: date })}
              >
                {t("save")}
              </button>
            </div>
          </Field>
        </div>

        <button className="btn btn-ghost btn-block" onClick={onClose}>{t("cancel")}</button>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- detail ---- */

export function PlanDetailPage() {
  const { id } = useParams();
  const { t, name, pick } = useI18n();
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [view, setView] = useState<"month" | "week" | "timeline">("month");
  const [cursor, setCursor] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [selected, setSelected] = useState<any>(null);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [task, setTask] = useState({ title: "", date: ymd(new Date()) });
  const [progress, setProgress] = useState({ pct: "0", stage: "land_preparation" });
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState<unknown>(null);

  const load = () => {
    if (!id) return;
    setLoading(true);
    api.get(`/plans/${id}`)
      .then((r) => {
        setPlan(r.data);
        setProgress({ pct: String(r.data.progress_pct ?? 0), stage: r.data.current_stage });
      })
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const activities: any[] = plan?.activities ?? [];

  const byDay = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const a of activities) (map[a.scheduled_date] ??= []).push(a);
    return map;
  }, [activities]);

  async function patchActivity(activityId: string, body: Record<string, unknown>) {
    const res = await api.patch(`/plans/${id}/activities/${activityId}`, body);
    const updated = res.data;
    setPlan((p: any) => (p ? { ...p, activities: p.activities.map((x: any) => (x.id === activityId ? updated : x)) } : p));
    setSelected((cur: any) => (cur && cur.id === activityId ? updated : cur));
  }

  async function addTask() {
    if (!task.title.trim()) return;
    await api.post(`/plans/${id}/activities`, {
      title_en: task.title.trim(),
      title_hi: task.title.trim(),
      scheduled_date: task.date,
      activity_type: "custom",
      stage: "custom",
    });
    setTask({ title: "", date: ymd(new Date()) });
    setAdding(false);
    load();
  }

  async function saveProgress() {
    await api.post(`/plans/${id}/progress`, {
      progress_pct: Number(progress.pct) || 0,
      current_stage: progress.stage,
    });
    load();
  }

  async function ask() {
    if (!question.trim()) return;
    setAskBusy(true);
    setAskError(null);
    try {
      const res = await api.post(`/plans/${id}/assistant`, { question: question.trim() });
      setAnswer(res.data.answer);
    } catch (e) {
      setAskError(e);
    } finally {
      setAskBusy(false);
    }
  }

  if (loading) return <Loading />;
  if (error !== null) return <ErrorNote error={error} onRetry={load} />;
  if (!plan) return null;

  const summary = plan.summary ?? {};
  const daysLeft = plan.expected_harvest_date
    ? Math.round((parseDay(plan.expected_harvest_date).getTime() - new Date(ymd(new Date())).getTime()) / 86400000)
    : null;
  const alerts: any[] = plan.weather?.alerts ?? [];

  const monthLabel = cursor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const firstDow = (new Date(cursor.getFullYear(), cursor.getMonth(), 1).getDay() + 6) % 7;
  const daysInMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
  const monthCells: (string | null)[] = [
    ...Array.from({ length: firstDow }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => ymd(new Date(cursor.getFullYear(), cursor.getMonth(), i + 1))),
  ];

  const weekStart = (() => {
    const d = new Date();
    const shift = (d.getDay() + 6) % 7;
    d.setDate(d.getDate() - shift);
    return d;
  })();
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    return ymd(d);
  });

  const planStart = (plan.created_at ?? "").slice(0, 10) || ymd(new Date());
  // default list is the forward-looking part of the plan; open a day to see that day's history
  const dayList = selectedDay ? (byDay[selectedDay] ?? []) : activities.filter((a) => a.scheduled_date >= planStart);

  return (
    <>
      <PageHead title={plan.name} lead={plan.crop?.name_en ? `${name(plan.crop)} · ${plan.farm?.name ?? ""}` : undefined} back="/app/plan/calendar" />

      <section className="card">
        <div className="row between wrap">
          <div>
            <span className="eyebrow">{t("crop_progress")}</span>
            <h2 style={{ margin: 0 }}>{t(`stage_${plan.current_stage}`)}</h2>
            <span className="small muted">{t(`method_${plan.farming_method}`)} · {t("sowing_date")} {fmtDay(plan.sowing_date)}</span>
          </div>
          <MockBadge isMock={Boolean(plan.weather?.provenance?.is_mock)} />
        </div>
        <div className="meter" style={{ margin: "0.7rem 0 0.4rem" }}>
          <span style={{ width: `${Math.min(100, Math.max(0, plan.progress_pct || 0))}%` }} />
        </div>
        <div className="grid three cal-stats" style={{ gap: "0.5rem", marginTop: "0.6rem" }}>
          <div className="stat">
            <div className="label">{t("days_since_sowing")}</div>
            <div className="value">{plan.days_since_sowing}</div>
          </div>
          <div className="stat">
            <div className="label">{t("days_remaining")}</div>
            <div className="value">{daysLeft !== null ? Math.max(0, daysLeft) : "—"}</div>
          </div>
          <div className="stat">
            <div className="label">{t("completed_tasks")}</div>
            <div className="value">{summary.completed ?? 0}<span className="small muted"> / {summary.total_activities ?? 0}</span></div>
          </div>
        </div>
        <p className="footer-note" style={{ marginTop: "0.5rem" }}>
          {t("estimated_harvest")}: {plan.expected_harvest_date ? fmtDay(plan.expected_harvest_date, { day: "numeric", month: "long", year: "numeric" }) : "—"}
          {summary.overdue > 0 && <> · <strong>{summary.overdue} {t("overdue")}</strong></>}
        </p>

        <details style={{ marginTop: "0.5rem" }}>
          <summary style={{ minHeight: 44, cursor: "pointer", fontWeight: 700 }}>{t("update_progress")}</summary>
          <div className="row wrap" style={{ gap: "0.5rem", marginTop: "0.5rem" }}>
            <select className="select" style={{ flex: 1, minWidth: 160 }} value={progress.stage} onChange={(e) => setProgress((p) => ({ ...p, stage: e.target.value }))}>
              {STAGES.map((s) => <option key={s} value={s}>{t(`stage_${s}`)}</option>)}
            </select>
            <input className="input" style={{ flex: 1, minWidth: 120 }} type="number" min={0} max={100} value={progress.pct}
              onChange={(e) => setProgress((p) => ({ ...p, pct: e.target.value }))} aria-label={t("crop_progress")} />
            <button className="btn btn-secondary btn-sm" onClick={() => void saveProgress()}>{t("save_progress")}</button>
          </div>
          <p className="footer-note">{t("estimated_dates_note")}</p>
        </details>
      </section>

      {alerts.length > 0 && (
        <section className="card warn">
          <h3 style={{ marginTop: 0 }}>{t("weather_alerts")}</h3>
          {alerts.map((a) => (
            <div className="alert warning" key={a.activity_id + a.date} style={{ marginBottom: "0.4rem" }}>
              <span className="dot" />
              <div>
                <strong>{a.title} · {fmtDay(a.date)}</strong>
                <div className="small">{a.message}</div>
                {a.suggested_date && <div className="small muted">{t("suggested_date")}: {fmtDay(a.suggested_date)}</div>}
              </div>
            </div>
          ))}
          <p className="footer-note">{t("forecast_note")}</p>
        </section>
      )}

      <section className="card">
        <div className="row between wrap" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0 }}>{t("calendar_title")}</h2>
          <div className="seg" role="group" aria-label={t("calendar_title")}>
            {(["month", "week", "timeline"] as const).map((v) => (
              <button key={v} aria-pressed={view === v} onClick={() => setView(v)}>{t(`view_${v}`)}</button>
            ))}
          </div>
        </div>

        {view === "month" && (
          <>
            <div className="row between" style={{ margin: "0.7rem 0 0.4rem" }}>
              <button className="icon-only" aria-label={t("back")} onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>‹</button>
              <strong>{monthLabel}</strong>
              <button className="icon-only" aria-label={t("next")} onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>›</button>
            </div>
            <div className="cal-weekdays">
              {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <span key={i}>{d}</span>)}
            </div>
            <div className="cal-month">
              {monthCells.map((day, i) => {
                if (!day) return <span key={`b${i}`} className="cal-day empty" />;
                const items = byDay[day] ?? [];
                const isToday = day === ymd(new Date());
                return (
                  <button
                    key={day}
                    className={`cal-day${isToday ? " today" : ""}${selectedDay === day ? " selected" : ""}`}
                    onClick={() => setSelectedDay(selectedDay === day ? null : day)}
                  >
                    <span className="num">{parseDay(day).getDate()}</span>
                    <span className="dots">
                      {items.slice(0, 3).map((a) => <i key={a.id} className={`dot ${typeTone(a.activity_type)}${a.status === "completed" ? " done" : ""}`} />)}
                    </span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {view === "week" && (
          <div className="cal-week">
            {weekDays.map((day) => (
              <div className="cal-week-col" key={day}>
                <div className={`cal-week-day${day === ymd(new Date()) ? " today" : ""}`}>
                  <span>{parseDay(day).toLocaleDateString(undefined, { weekday: "short" })}</span>
                  <strong>{parseDay(day).getDate()}</strong>
                </div>
                {(byDay[day] ?? []).map((a) => (
                  <button key={a.id} className={`cal-chip ${typeTone(a.activity_type)}${a.status === "completed" ? " done" : ""}`} onClick={() => setSelected(a)}>
                    {pick(a.title_en, a.title_hi)}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}

        {view === "timeline" && (
          <div className="cal-timeline">
            {[...STAGES, "custom" as const].map((stage) => {
              const items = activities.filter((a) => (a.stage === stage || (stage === "custom" && !STAGES.includes(a.stage))));
              if (items.length === 0) return null;
              return (
                <div className="cal-stage" key={stage}>
                  <h3>{t(`stage_${stage}`)}</h3>
                  <ol>
                    {items.map((a) => (
                      <li key={a.id} className={a.status === "completed" ? "done" : undefined}>
                        <button className="cal-tl-row" onClick={() => setSelected(a)}>
                          <i className={`dot ${typeTone(a.activity_type)}${a.status === "completed" ? " done" : ""}`} />
                          <span className="cal-tl-title">{pick(a.title_en, a.title_hi)}</span>
                          <span className="small muted">{fmtDay(a.scheduled_date)}</span>
                        </button>
                      </li>
                    ))}
                  </ol>
                </div>
              );
            })}
          </div>
        )}

        {view === "month" && (
          <>
            <div className="row between" style={{ margin: "0.8rem 0 0.3rem" }}>
              <h3 style={{ margin: 0 }}>
                {selectedDay ? fmtDay(selectedDay, { weekday: "long", day: "numeric", month: "short" }) : t("upcoming_activities")}
              </h3>
              {selectedDay && <button className="btn btn-ghost btn-sm" onClick={() => setSelectedDay(null)}>{t("all")}</button>}
            </div>
            <ActivityList items={dayList} onOpen={setSelected} startDay={planStart} />
          </>
        )}
      </section>

      <section className="card">
        <div className="row between wrap">
          <h2 style={{ margin: 0 }}>{t("add_task")}</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => setAdding((v) => !v)}>{adding ? t("cancel") : t("add_task")}</button>
        </div>
        {adding && (
          <div style={{ marginTop: "0.6rem" }}>
            <Field label={t("task_title")}>
              <input className="input" value={task.title} onChange={(e) => setTask((s) => ({ ...s, title: e.target.value }))} placeholder={t("task_title")} />
            </Field>
            <Field label={t("scheduled_date")}>
              <input className="input" type="date" value={task.date} onChange={(e) => setTask((s) => ({ ...s, date: e.target.value }))} />
            </Field>
            <button className="btn btn-primary btn-sm" disabled={!task.title.trim()} onClick={() => void addTask()}>{t("save_task")}</button>
          </div>
        )}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("ask_assistant")}</h2>
        <div className="row wrap" style={{ gap: "0.4rem", marginBottom: "0.6rem" }}>
          {[
            pick("What should I do today?", "आज मुझे क्या करना चाहिए?"),
            pick("When should I apply fertilizer?", "खाद कब डालें?"),
            pick("Days left until harvesting?", "कटाई में कितने दिन बाकी?"),
            pick("What if heavy rain is expected?", "भारी बारिश हो तो क्या करें?"),
            pick("Pending tasks this week?", "इस हफ्ते क्या बाकी है?"),
          ].map((q) => (
            <button key={q} className="chip" onClick={() => setQuestion(q)}>{q}</button>
          ))}
        </div>
        <div className="row" style={{ gap: "0.5rem" }}>
          <input className="input" value={question} placeholder={t("assistant_placeholder")} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void ask(); }} />
          <button className="btn btn-primary btn-sm" disabled={askBusy || !question.trim()} onClick={() => void ask()}>
            {askBusy ? <span className="spinner" aria-hidden="true" /> : t("search")}
          </button>
        </div>
        {askError !== null && <ErrorNote error={askError} />}
        {answer && <div className="alert info" style={{ marginTop: "0.6rem" }}><span className="dot" /><div>{answer}</div></div>}
        <p className="footer-note">{t("assistant_hint")}</p>
      </section>

      <p className="footer-note">{plan.disclaimer}</p>
      {selected && <ActivitySheet activity={selected} onClose={() => setSelected(null)} onPatch={(body) => patchActivity(selected.id, body)} />}
    </>
  );
}

function ActivityList({ items, onOpen, startDay }: { items: any[]; onOpen: (a: any) => void; startDay?: string }) {
  const { t, pick } = useI18n();
  if (items.length === 0) return <p className="small muted">{t("no_upcoming")}</p>;
  const today = ymd(new Date());
  return (
    <ul className="list cal-list">
      {items.map((a) => {
        // tasks dated before the plan existed are history, not overdue work
        const late = a.status !== "completed" && a.scheduled_date < today && (!startDay || a.scheduled_date >= startDay);
        return (
          <li key={a.id}>
            <button className={`cal-row${a.status === "completed" ? " done" : ""}`} onClick={() => onOpen(a)}>
              <i className={`dot ${typeTone(a.activity_type)}${a.status === "completed" ? " done" : ""}`} />
              <span className="cal-row-main">
                <strong>{pick(a.title_en, a.title_hi)}</strong>
                <span className="small muted">{fmtDay(a.scheduled_date, { weekday: "short", day: "numeric", month: "short" })} · {t(typeKey(a.activity_type))}</span>
              </span>
              <span className={`pill ${a.status === "completed" ? "good" : late ? "bad" : "warn"}`}>
                {a.status === "completed" ? t("completed_tasks") : late ? t("overdue") : t("pending_tasks")}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/* -------------------------------------------------- home page mini view ---- */

export function CalendarStrip({ activities }: { activities: any[] }) {
  const { pick } = useI18n();
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return ymd(d);
  });
  const byDay: Record<string, any[]> = {};
  for (const a of activities) (byDay[a.scheduled_date] ??= []).push(a);

  return (
    <div className="cal-strip">
      {days.map((day) => {
        const items = byDay[day] ?? [];
        return (
          <div className={`cal-strip-day${day === ymd(new Date()) ? " today" : ""}`} key={day} title={items.map((a) => pick(a.title_en, a.title_hi)).join(", ")}>
            <span>{parseDay(day).toLocaleDateString(undefined, { weekday: "narrow" })}</span>
            <strong>{parseDay(day).getDate()}</strong>
            <span className="dots">
              {items.slice(0, 3).map((a) => <i key={a.id} className={`dot ${typeTone(a.activity_type)}`} />)}
            </span>
            {items.length > 0 && <span className="sr-count">{items.length}</span>}
          </div>
        );
      })}
    </div>
  );
}
