import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth, useFarms } from "../session";
import { useI18n } from "../i18n";
import { Empty, ErrorNote, Icon, Loading, MockBadge, PageHead } from "../ui";
import { CalendarStrip, seasonForToday } from "./Calendar";

export function Dashboard() {
  const { user } = useAuth();
  const { farm, loading } = useFarms();
  const { t, pick, name } = useI18n();
  const [weather, setWeather] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [advice, setAdvice] = useState<any>(null);
  const [latest, setLatest] = useState<{ soil: any; detection: any }>({ soil: null, detection: null });
  const [rec, setRec] = useState<any>(null);
  const [recBusy, setRecBusy] = useState(false);
  const [recError, setRecError] = useState<unknown>(null);
  const [planner, setPlanner] = useState<any>(null);
  const [season, setSeason] = useState<"kharif" | "rabi" | "zaid">(() => {
    const m = new Date().getMonth() + 1;
    if (m >= 6 && m <= 10) return "kharif";
    if (m >= 11 || m <= 3) return "rabi";
    return "zaid";
  });

  useEffect(() => {
    api.get("/plans/overview").then((r) => setPlanner(r.data)).catch(() => setPlanner(null));
  }, []);

  useEffect(() => {
    if (!farm) return;
    let alive = true;
    api.get(`/weather/current?farm_id=${farm.id}`).then((r) => alive && setWeather(r.data)).catch(() => {});
    api.get(`/weather/forecast?farm_id=${farm.id}&days=5`).then((r) => alive && setForecast(r.data)).catch(() => {});
    api.get(`/weather/advisories?farm_id=${farm.id}`)
      .then((r) => alive && setAdvice(r.data?.advisories?.[0] ?? null))
      .catch(() => {});
    Promise.all([
      api.get(`/soil/reports?farm_id=${farm.id}&limit=1`).catch(() => null),
      api.get(`/disease/detections?farm_id=${farm.id}&limit=1`).catch(() => null),
    ]).then(([s, d]) => {
      if (alive) setLatest({ soil: s?.data?.[0] ?? null, detection: d?.data?.[0] ?? null });
    });
    return () => { alive = false; };
  }, [farm?.id]);

  if (loading) return <Loading />;
  if (!farm) {
    return (
      <>
        <PageHead title={t("no_farm_title")} lead={t("no_farm_body")} />
        <Link className="btn btn-primary btn-block" to="/app/farms/new">{t("add_farm")}</Link>
      </>
    );
  }

  const current = weather?.current;
  const prov = weather?.provenance;

  async function findBestCrops() {
    if (!farm) return;
    setRecBusy(true);
    setRecError(null);
    try {
      const res = await api.post("/crops/recommend", { farm_id: farm.id, season });
      setRec(res.data);
    } catch (e) {
      setRecError(e);
    } finally {
      setRecBusy(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h1>{t("dashboard_greeting")}, {user?.full_name?.split(" ")[0] ?? "farmer"}</h1>
        <p>{farm.name} · {farm.village ? `${farm.village}, ` : ""}{farm.district?.name}</p>
        <div className="meta">
          {farm.area_acres && <span>{farm.area_acres} acres</span>}
          {farm.soil_type && <span>{farm.soil_type} soil</span>}
          {farm.irrigation_source && <span>{farm.irrigation_source}</span>}
        </div>
      </section>

      <section className="section-head">
        <div>
          <span className="eyebrow">{t("todays_advice")}</span>
          <h2>{advice ? pick(advice.title_en, advice.title_hi) : t("no_advisory")}</h2>
        </div>
        <Link className="head-link" to="/app/plan/weather">{t("all_advisories")}</Link>
      </section>
      <div className={`card advice ${advice?.severity ?? "info"}`}>
        <span className="glyph">
          <Icon name={advice ? "alert" : "check"} size={22} />
        </span>
        <div>
          <p>
            {advice
              ? pick(advice.detail_en, advice.detail_hi)
              : pick(
                  "Weather looks normal for your district today. Keep monitoring soil moisture.",
                  "आज आपके जिले में मौसम सामान्य है। मिट्टी की नमी पर नज़र रखें।",
                )}
          </p>
        </div>
      </div>

      {current && (
        <Link to="/app/plan/weather" className="card link">
          <div className="row between">
            <div>
              <div className="row" style={{ gap: "0.6rem" }}>
                <span style={{ color: "var(--teal-700)" }}><Icon name="cloud" size={30} /></span>
                <span className="big-number">{Math.round(current.temp_c)}°</span>
                <span className="muted">{String(current.condition).replace(/_/g, " ")}</span>
              </div>
              <div className="small muted">
                {t("humidity")} {current.humidity_pct}% · {t("wind")} {current.wind_kmph} km/h
                {current.rain_mm > 0 ? ` · ${t("rain")} ${current.rain_mm} mm` : ""}
              </div>
            </div>
            <MockBadge isMock={Boolean(prov?.is_mock)} />
          </div>
        </Link>
      )}

      <div className="grid two" style={{ marginTop: "0.3rem" }}>
        <Link to="/app/plan" className="tile">
          <span className="icon"><Icon name="leaf" /></span>
          <span><strong>{t("plan")}</strong><span>{t("plan_sub")}</span></span>
        </Link>
        <Link to="/app/protect" className="tile">
          <span className="icon"><Icon name="shield" /></span>
          <span><strong>{t("protect")}</strong><span>{t("protect_sub")}</span></span>
        </Link>
        <Link to="/app/sell" className="tile">
          <span className="icon"><Icon name="rupee" /></span>
          <span><strong>{t("sell")}</strong><span>{t("sell_sub")}</span></span>
        </Link>
        <Link to="/app/profile" className="tile">
          <span className="icon"><Icon name="user" /></span>
          <span><strong>{t("profile")}</strong><span>{farm.district?.name} · {t("choose_farm")}</span></span>
        </Link>
      </div>

      <section className="card" style={{ marginTop: "0.5rem" }}>
        <div className="row between">
          <div>
            <span className="eyebrow">{t("smart_crop_title")}</span>
            <h2 style={{ margin: "0.2rem 0 0" }}>{t("smart_crop_title")}</h2>
          </div>
          <MockBadge isMock={Boolean(weather?.provenance?.is_mock)} />
        </div>
        <p className="small muted" style={{ marginTop: "0.4rem" }}>{t("smart_crop_sub")}</p>

        {current && (
          <div className="grid three" style={{ gap: "0.5rem", marginTop: "0.7rem" }}>
            <div className="stat">
              <div className="label">{t("temperature")}</div>
              <div className="value">{Math.round(current.temp_c)}°</div>
              <div className="small muted">{String(current.condition).replace(/_/g, " ")}</div>
            </div>
            <div className="stat">
              <div className="label">{t("humidity")}</div>
              <div className="value">{current.humidity_pct}%</div>
              <div className="small muted">{t("wind")} {current.wind_kmph} km/h</div>
            </div>
            <div className="stat">
              <div className="label">{t("rainfall")}</div>
              <div className="value">{current.rain_mm} mm</div>
              <div className="small muted">
                {forecast?.daily ? `${forecast.daily.reduce((a: number, d: any) => a + (d.rain_mm || 0), 0).toFixed(0)} mm / 5d` : "—"}
              </div>
            </div>
          </div>
        )}

        {forecast?.daily && (
          <div className="grid" style={{ gridTemplateColumns: "repeat(5, 1fr)", gap: "0.4rem", marginTop: "0.7rem" }}>
            {forecast.daily.slice(0, 5).map((d: any) => (
              <div className="stat" key={d.date}>
                <div className="label">{new Date(d.date).toLocaleDateString(undefined, { weekday: "short" })}</div>
                <div className="value" style={{ fontSize: "1rem" }}>{Math.round(d.temp_max_c)}°</div>
                <div className="small muted">{d.rain_mm > 0 ? `${d.rain_mm} mm` : "—"}</div>
              </div>
            ))}
          </div>
        )}

        <div className="card" style={{ marginTop: "0.8rem" }}>
          <strong className="small">{t("soil_summary")}</strong>
          <div className="small muted" style={{ marginTop: 4 }}>
            {latest.soil
              ? `${t("tested_on")} ${latest.soil.tested_on ?? latest.soil.created_at?.slice(0, 10)} · ${farm.soil_type ?? "—"} soil`
              : (farm.soil_type ? `No soil test on file. Using typical values for ${farm.soil_type} soil.` : "No soil test on file.")}
          </div>
          {rec?.input_provenance?.missing_fields?.length > 0 && (
            <div className="small muted" style={{ marginTop: 4 }}>
              Missing soil fields: {rec.input_provenance.missing_fields.join(", ").replace(/_/g, " ")}
            </div>
          )}
          <Link className="btn btn-secondary btn-sm" to="/app/plan/soil" style={{ marginTop: "0.6rem" }}>
            {t("soil_card")}
          </Link>
        </div>

        {advice && (
          <div className={`alert ${advice.severity === "danger" ? "danger" : advice.severity === "warning" ? "warning" : "info"}`} style={{ marginTop: "0.8rem" }}>
            <span className="dot" />
            <div>
              <strong>{t("advisory")}: {pick(advice.title_en, advice.title_hi)}</strong>
              <div className="small">{pick(advice.detail_en, advice.detail_hi)}</div>
            </div>
          </div>
        )}

        <div className="row" style={{ gap: "0.6rem", marginTop: "0.8rem", alignItems: "center" }}>
          <select className="select" value={season} onChange={(e) => setSeason(e.target.value as any)} style={{ flex: 1 }}>
            <option value="kharif">{t("kharif")}</option>
            <option value="rabi">{t("rabi")}</option>
            <option value="zaid">{t("zaid")}</option>
          </select>
          <button className="btn btn-primary" disabled={recBusy} aria-busy={recBusy} onClick={() => void findBestCrops()} style={{ flex: 1 }}>
            {recBusy
              ? <><span className="spinner" aria-hidden="true" />{t("recommending")}</>
              : t("find_best_crops")}
          </button>
        </div>

        {recError !== null && <ErrorNote error={recError} />}

        {rec && (
          <div style={{ marginTop: "0.8rem" }}>
            {rec.input_provenance?.soil_source === "farm_soil_type_default" && (
              <div className="alert warning" style={{ marginBottom: "0.7rem" }}>
                <span className="dot" />
                <div>
                  <strong>No soil test on file</strong>
                  <div className="small">Ranking uses typical values for {farm.soil_type ?? "unrecorded"} soil. Add a soil test to make this specific.</div>
                  <Link to="/app/plan/soil">{t("soil_card")}</Link>
                </div>
              </div>
            )}
            {rec.results.length === 0 && (
              <div className="card"><Empty title={pick("No crop matched", "कोई फसल नहीं मिली")} body={rec.explanation} /></div>
            )}
            {rec.results.map((r: any) => (
              <article className="card" key={r.crop_slug} style={{ marginTop: "0.6rem" }}>
                <div className="row between">
                  <div>
                    <h3 style={{ margin: 0 }}>{name(r)}</h3>
                    <span className="small muted">
                      {r.category} · {r.duration_days ? `${r.duration_days} days` : r.season} · {r.water_need} water
                    </span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="big-number" style={{ fontSize: "1.5rem" }}>{r.score}</div>
                    <span className={`pill ${r.confidence_band === "high" ? "good" : r.confidence_band === "medium" ? "warn" : ""}`}>
                      {r.confidence_band}
                    </span>
                  </div>
                </div>
                <div className="meter" style={{ margin: "0.6rem 0" }}>
                  <span style={{ width: `${Math.min(100, r.score)}%` }} />
                </div>
                <strong className="small">{t("why_crop")}</strong>
                <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                  {r.reasons_i18n
                    ? r.reasons_i18n.map((reason: any, i: number) => <li className="small" key={i}>{pick(reason.en, reason.hi)}</li>)
                    : r.reasons.map((reason: string, i: number) => <li className="small" key={i}>{reason}</li>)}
                </ul>
                <div className="row" style={{ marginTop: "0.7rem", justifyContent: "flex-end" }}>
                  <Link className="btn btn-secondary btn-sm" to={`/app/plan/crops/${r.crop_slug}`}>
                    {t("view_crop_details")}
                  </Link>
                </div>
              </article>
            ))}

            {rec.suppressed?.length > 0 && (
              <details className="card" style={{ marginTop: "0.6rem" }}>
                <summary style={{ minHeight: 44, fontWeight: 700, cursor: "pointer" }}>
                  {t("suppressed")} ({rec.suppressed.length})
                </summary>
                <ul className="list" style={{ marginTop: "0.5rem" }}>
                  {rec.suppressed.map((s: any) => (
                    <li key={s.crop_slug}>
                      <strong>{name(s)}</strong>
                      <div className="small muted">{pick(s.reason_en, s.reason_hi)}</div>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            <div className="card" style={{ marginTop: "0.6rem" }}>
              <strong className="small">{t("why_suitable_farm")}</strong>
              <p className="small" style={{ marginTop: 4 }}>
                {rec.results.length > 0
                  ? `Based on your ${rec.input_provenance?.soil_source === "soil_report" ? "soil test" : "soil type"}, ` +
                    `${current ? `current temperature of ${Math.round(current.temp_c)}°C, ` : ""}` +
                    `and ${rec.input_provenance?.rainfall_used_mm ?? 0} mm of expected rain over the next 6 days, ` +
                    `${name(rec.results[0])} is the best fit. ${rec.results.length > 1 ? `Other suitable options include ${rec.results.slice(1).map((r: any) => name(r)).join(", ")}.` : ""} ` +
                    "Irrigation availability and your local planting calendar should also be considered."
                  : "No crop passed the agro-zone and season rules for this farm. Try another season."}
              </p>
              <p className="footer-note">{t("smart_explanation_note")}</p>
            </div>

            <p className="footer-note" style={{ marginTop: "0.5rem" }}>
              {t("weather_updated")}: {weather?.provenance?.retrieved_at?.slice(0, 16).replace("T", " ") ?? "—"} · Model {rec.model_version ?? "croprec-rules-v1"}
            </p>
          </div>
        )}
      </section>

      <section className="card" style={{ marginTop: "0.6rem" }}>
        <div className="row between wrap" style={{ gap: "0.5rem" }}>
          <div>
            <span className="eyebrow">{t("calendar_title")}</span>
            <h2 style={{ margin: "0.2rem 0 0" }}>{t("calendar_title")}</h2>
          </div>
          <Link className="btn btn-primary btn-sm" to="/app/plan/calendar/new">{t("create_crop_plan")}</Link>
        </div>
        <p className="small muted" style={{ marginTop: "0.4rem" }}>{t("calendar_sub")}</p>

        <div className="row wrap" style={{ gap: "0.4rem", marginTop: "0.6rem", alignItems: "center" }}>
          <span className="cal-type type-sowing">{t("current_season")}: {t(seasonForToday())}</span>
          <Link className="head-link" to="/app/plan/calendar">{t("calendar_overview")} →</Link>
        </div>

        {planner?.plans?.length > 0 ? (
          <>
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.5rem", marginTop: "0.7rem" }}>
              <div className="stat">
                <div className="label">{t("next_task")}</div>
                {planner.next_task ? (
                  <>
                    <div className="value" style={{ fontSize: "0.95rem" }}>{pick(planner.next_task.title_en, planner.next_task.title_hi)}</div>
                    <div className="small muted">
                      {new Date(planner.next_task.scheduled_date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
                      {" · "}{planner.next_task.plan_name}
                    </div>
                  </>
                ) : <div className="small muted">{t("no_upcoming")}</div>}
              </div>
              <div className="stat">
                <div className="label">{t("harvest_countdown")}</div>
                {planner.harvest ? (
                  <>
                    <div className="value">{planner.harvest.days_left}</div>
                    <div className="small muted">
                      {pick(planner.harvest.crop.name_en, planner.harvest.crop.name_hi)}
                      {" · "}{new Date(planner.harvest.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
                    </div>
                  </>
                ) : <div className="small muted">—</div>}
              </div>
            </div>

            <div style={{ marginTop: "0.8rem" }}>
              <strong className="small">{t("active_plans")}</strong>
              <div className="row wrap" style={{ gap: "0.4rem", marginTop: "0.4rem" }}>
                {planner.plans.map((p: any) => (
                  <Link className="chip" key={p.id} to={`/app/plan/calendar/${p.id}`}>
                    {pick(p.crop.name_en, p.crop.name_hi)} · {p.farm?.name} · {p.progress_pct}%
                  </Link>
                ))}
              </div>
            </div>

            <div style={{ marginTop: "0.8rem" }}>
              <strong className="small">{t("upcoming_activities")}</strong>
              <ul className="list cal-list" style={{ marginTop: "0.3rem" }}>
                {planner.upcoming.slice(0, 4).map((a: any) => (
                  <li key={a.id}>
                    <Link className="cal-row" to={`/app/plan/calendar/${a.plan_id}`}>
                      <span className="cal-row-main">
                        <strong>{pick(a.title_en, a.title_hi)}</strong>
                        <span className="small muted">
                          {new Date(a.scheduled_date).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
                          {" · "}{a.plan_name}
                        </span>
                      </span>
                      <span className="pill warn">{t("pending_tasks")}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ marginTop: "0.8rem" }}>
              <strong className="small">{t("calendar_overview")}</strong>
              <div style={{ marginTop: "0.4rem" }}>
                <CalendarStrip activities={planner.upcoming} />
              </div>
            </div>
          </>
        ) : (
          <div className="card" style={{ marginTop: "0.7rem", background: "var(--surface-2)" }}>
            <strong>{t("no_plans_title")}</strong>
            <p className="small muted" style={{ marginTop: 4 }}>{t("no_plans_body")}</p>
          </div>
        )}
        <p className="footer-note" style={{ marginTop: "0.6rem" }}>{t("estimated_dates_note")}</p>
      </section>

      <section className="section-head">
        <div>
          <span className="eyebrow">{t("recent_activity")}</span>
          <h2>{t("history")}</h2>
        </div>
      </section>
      <div className="card">
        <ul className="list">
          <li>
            <div className="row between">
              <div>
                <strong>{t("soil_card")}</strong>
                <div className="small muted">
                  {latest.soil
                    ? `${t("tested_on")} ${latest.soil.tested_on ?? latest.soil.created_at?.slice(0, 10)}`
                    : t("no_data")}
                </div>
              </div>
              <Link className="btn btn-secondary btn-sm" to="/app/plan/soil">{t("next")}</Link>
            </div>
          </li>
          <li>
            <div className="row between">
              <div>
                <strong>{t("history")}</strong>
                <div className="small muted">
                  {latest.detection
                    ? `${latest.detection.status === "uncertain" ? t("uncertain_title") : pick("Detected", "पहचाना")} · ${latest.detection.created_at?.slice(0, 10)}`
                    : t("no_data")}
                </div>
              </div>
              <Link className="btn btn-secondary btn-sm" to="/app/protect/history">{t("next")}</Link>
            </div>
          </li>
        </ul>
      </div>

      <p className="footer-note">{t("demo_note")}</p>
    </>
  );
}
