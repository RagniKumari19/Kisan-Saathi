import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useFarms } from "../session";
import { useI18n } from "../i18n";
import {
  Empty, ErrorNote, FarmGate, Field, Icon, Loading, MockBadge, PageHead, Provenance,
} from "../ui";

function statusTone(status: string | null | undefined): string {
  if (!status) return "";
  if (["very_low", "low", "strongly_acidic", "strongly_alkaline", "saline", "low"].includes(status)) return "bad";
  if (["medium", "neutral", "normal", "slightly_acidic", "slightly_alkaline"].includes(status)) return "good";
  return "warn";
}

function pretty(s: string | null | undefined): string {
  if (!s) return "—";
  return s.replace(/_/g, " ");
}

export function PlanHub() {
  const { farm } = useFarms();
  const { t } = useI18n();
  return (
    <>
      <PageHead title={t("plan_title")} lead={t("plan_sub")} />
      {farm && (
        <p className="small muted" style={{ marginTop: "-0.6rem" }}>
          {farm.name} · {farm.district?.name} · {pretty(farm.district?.agro_zone)}
        </p>
      )}
      <div className="stack">
        <Link className="tile" to="/app/plan/soil">
          <span className="icon"><Icon name="soil" /></span>
          <span><strong>{t("soil_card")}</strong><span>{t("soil_card_sub")}</span></span>
        </Link>
        <Link className="tile" to="/app/plan/weather">
          <span className="icon"><Icon name="cloud" /></span>
          <span><strong>{t("weather_card")}</strong><span>{t("weather_card_sub")}</span></span>
        </Link>
        <Link className="tile" to="/app/plan/recommend">
          <span className="icon"><Icon name="sprout" /></span>
          <span><strong>{t("crop_card")}</strong><span>{t("crop_card_sub")}</span></span>
        </Link>
        <Link className="tile" to="/app/plan/calendar">
          <span className="icon"><Icon name="history" /></span>
          <span><strong>{t("calendar_title")}</strong><span>{t("calendar_sub")}</span></span>
        </Link>
        <Link className="tile" to="/app/plan/crops">
          <span className="icon"><Icon name="book" /></span>
          <span><strong>{t("library")}</strong><span>Crop requirements, seasons and common diseases.</span></span>
        </Link>
      </div>
    </>
  );
}

export function SoilPage() {
  const { t, lang } = useI18n();
  const [form, setForm] = useState({
    tested_on: new Date().toISOString().slice(0, 10),
    nitrogen_kg_ha: "", phosphorus_kg_ha: "", potassium_kg_ha: "",
    ph: "", organic_carbon_pct: "", ec_ds_m: "",
  });
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const resultRef = useRef<HTMLElement | null>(null);
  const errorRef = useRef<HTMLDivElement | null>(null);

  const MEASUREMENTS: { key: keyof typeof form; label: string }[] = [
    { key: "nitrogen_kg_ha", label: t("nitrogen") },
    { key: "phosphorus_kg_ha", label: t("phosphorus") },
    { key: "potassium_kg_ha", label: t("potassium") },
    { key: "ph", label: t("ph") },
    { key: "organic_carbon_pct", label: t("organic_carbon") },
    { key: "ec_ds_m", label: t("ec") },
  ];

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  useEffect(() => {
    if (error !== null) errorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [error]);

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit(farmId: string, cropSlug: string | null) {
    setError(null);
    const filled = MEASUREMENTS.map((m) => ({ ...m, value: form[m.key].trim() }))
      .filter((m) => m.value !== "");
    if (filled.length === 0) {
      setError(new ApiError(0, "NO_MEASUREMENTS", t("soil_need_value")));
      document.getElementById("nitrogen_kg_ha")?.focus();
      return;
    }
    const invalid = filled.find((m) => !Number.isFinite(Number(m.value)) || Number(m.value) < 0);
    if (invalid) {
      setError(new ApiError(
        0, "INVALID_NUMBER", `${invalid.label}: ${t("soil_invalid_number")}`,
        [{ field: invalid.label, issue: t("soil_invalid_number") }],
      ));
      document.getElementById(invalid.key)?.focus();
      return;
    }
    setBusy(true);
    try {
      const number = (v: string) => (v.trim() === "" ? null : Number(v));
      const res = await api.post("/soil/analyze", {
        farm_id: farmId,
        crop_slug: cropSlug,
        tested_on: form.tested_on || null,
        source: "manual",
        nitrogen_kg_ha: number(form.nitrogen_kg_ha),
        phosphorus_kg_ha: number(form.phosphorus_kg_ha),
        potassium_kg_ha: number(form.potassium_kg_ha),
        ph: number(form.ph),
        organic_carbon_pct: number(form.organic_carbon_pct),
        ec_ds_m: number(form.ec_ds_m),
      });
      setResult(res.data.analysis);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead title={t("soil_test_title")} lead={t("soil_card_sub")} back="/app/plan" />
      <FarmGate>
        {(farm) => (
          <>
            {result && (
              <section className="card tinted scroll-target" aria-live="polite" ref={resultRef}>
                <div className="alert success" role="status" style={{ marginBottom: "0.8rem" }}>
                  <span className="dot" />
                  <div>
                    <strong>{t("soil_ready")}</strong>
                    <div className="small">{t("soil_ready_body")}</div>
                  </div>
                </div>
                <div className="row between">
                  <h2 style={{ margin: 0 }}>{t("soil_result")}</h2>
                  <span className="badge badge-neutral">{result.ruleset_version}</span>
                </div>
                <p style={{ marginTop: "0.5rem" }}>{lang === "hi" ? result.summary_hi : result.summary_en}</p>
                <div className="grid three" style={{ gap: "0.5rem" }}>
                  {Object.entries(result.statuses).map(([key, status]) => (
                    <div className="stat" key={key}>
                      <div className="label">{pretty(key)}</div>
                      <span className={`pill ${statusTone(status as string)}`}>{pretty(status as string)}</span>
                    </div>
                  ))}
                </div>
                <h3 style={{ marginTop: "1rem" }}>{t("treatments")}</h3>
                <ol style={{ margin: 0, paddingLeft: "1.1rem" }}>
                  {result.recommendations.map((r: any, i: number) => (
                    <li key={i} style={{ marginBottom: "0.7rem" }}>
                      <strong>{lang === "hi" ? r.action_hi : r.action}</strong>
                      <div className="small">{lang === "hi" ? r.detail_hi : r.detail}</div>
                      <a className="small" href={r.source_url} target="_blank" rel="noreferrer">{t("source")}</a>
                    </li>
                  ))}
                </ol>
                {result.missing_fields?.length > 0 && (
                  <p className="footer-note">
                    Not enough data for: {result.missing_fields.join(", ").replace(/_/g, " ")}. These are left blank rather than guessed.
                  </p>
                )}
                <p className="footer-note">{result.disclaimer}</p>
              </section>
            )}

            <form
              className="card"
              onSubmit={(e) => {
                e.preventDefault();
                const primary = farm.primary_crop_slug;
                void submit(farm.id, primary);
              }}
            >
              <div className="field">
                <label htmlFor="tested_on">{t("tested_on")}</label>
                <input id="tested_on" className="input" type="date" value={form.tested_on}
                  onChange={(e) => set("tested_on", e.target.value)} />
              </div>
              <p className="small muted">
                Enter the values printed on your soil health card. Leave any value blank if it was not tested.
              </p>
              <div className="grid two">
                <Field label={t("nitrogen")}><input id="nitrogen_kg_ha" className="input" inputMode="decimal" placeholder="210" value={form.nitrogen_kg_ha} onChange={(e) => set("nitrogen_kg_ha", e.target.value)} /></Field>
                <Field label={t("phosphorus")}><input id="phosphorus_kg_ha" className="input" inputMode="decimal" placeholder="18" value={form.phosphorus_kg_ha} onChange={(e) => set("phosphorus_kg_ha", e.target.value)} /></Field>
                <Field label={t("potassium")}><input id="potassium_kg_ha" className="input" inputMode="decimal" placeholder="320" value={form.potassium_kg_ha} onChange={(e) => set("potassium_kg_ha", e.target.value)} /></Field>
                <Field label={t("ph")}><input id="ph" className="input" inputMode="decimal" placeholder="8.1" value={form.ph} onChange={(e) => set("ph", e.target.value)} /></Field>
                <Field label={t("organic_carbon")}><input id="organic_carbon_pct" className="input" inputMode="decimal" placeholder="0.42" value={form.organic_carbon_pct} onChange={(e) => set("organic_carbon_pct", e.target.value)} /></Field>
                <Field label={t("ec")}><input id="ec_ds_m" className="input" inputMode="decimal" placeholder="0.31" value={form.ec_ds_m} onChange={(e) => set("ec_ds_m", e.target.value)} /></Field>
              </div>
              <p className="small muted">
                Interpreted for {farm.primary_crop_slug ?? "your main crop"}. Change the main crop in your farm settings to compare another crop.
              </p>
              <div ref={errorRef}>
                {error !== null && <ErrorNote error={error} />}
              </div>
              <button className="btn btn-primary btn-block" disabled={busy} type="submit" aria-busy={busy}>
                {busy
                  ? <><span className="spinner" aria-hidden="true" />{t("saving")}</>
                  : t("analyse_soil")}
              </button>
            </form>
          </>
        )}
      </FarmGate>
    </>
  );
}

export function WeatherPage() {
  const { t, pick } = useI18n();
  const { farm, loading: farmLoading } = useFarms();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const load = (farmId: string) => {
    setLoading(true);
    setError(null);
    api.get(`/weather/forecast?farm_id=${farmId}&days=5`)
      .then((r) => setData(r.data))
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (farm) load(farm.id);
  }, [farm?.id]);

  return (
    <>
      <PageHead title={t("weather_card")} lead={t("weather_card_sub")} back="/app/plan" />
      {farmLoading && <Loading />}
      {!farmLoading && !farm && <FarmGate>{() => null}</FarmGate>}
      {farm && (() => {
          if (error) return <ErrorNote error={error} onRetry={() => load(farm.id)} />;
          if (loading || !data) return <Loading />;
          return (
            <>
              <div className="card">
                <div className="row between">
                  <div>
                    <h2 style={{ margin: 0 }}>{data.location.district}</h2>
                    <span className="small muted">{data.location.latitude.toFixed(2)}, {data.location.longitude.toFixed(2)}</span>
                  </div>
                  <MockBadge isMock={Boolean(data.provenance?.is_mock)} />
                </div>
                <div className="grid three" style={{ marginTop: "0.8rem", gap: "0.5rem" }}>
                  {data.daily.slice(0, 3).map((d: any) => (
                    <div className="stat" key={d.date}>
                      <div className="label">{new Date(d.date).toLocaleDateString(undefined, { weekday: "short" })}</div>
                      <div className="value">{Math.round(d.temp_max_c)}° <span className="small muted">{Math.round(d.temp_min_c)}°</span></div>
                      <div className="small muted">{d.rain_mm > 0 ? `${d.rain_mm} mm` : pick("no rain", "बारिश नहीं")}</div>
                    </div>
                  ))}
                </div>
              </div>

              <h2>{t("advisory")}</h2>
              {data.advisories.length === 0 && <div className="card"><Empty body={pick("No weather rules triggered today.", "आज मौसम की कोई चेतावनी नहीं।")} /></div>}
              {data.advisories.map((a: any) => (
                <div className={`alert ${a.severity === "danger" ? "danger" : a.severity === "warning" ? "warning" : "info"}`} key={a.rule_id}>
                  <span className="dot" />
                  <div>
                    <strong>{t("advisory")}: {pick(a.title_en, a.title_hi)}</strong>
                    <div>{pick(a.detail_en, a.detail_hi)}</div>
                    <div className="small muted" style={{ marginTop: 4 }}>{a.rule_id}</div>
                  </div>
                </div>
              ))}

              <h2>5-day forecast</h2>
              <div className="card">
                <table className="table">
                  <thead>
                    <tr><th>Day</th><th className="num">Max/Min</th><th className="num">Rain</th><th className="num">Humidity</th></tr>
                  </thead>
                  <tbody>
                    {data.daily.map((d: any) => (
                      <tr key={d.date}>
                        <td>{new Date(d.date).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}</td>
                        <td className="num">{Math.round(d.temp_max_c)}° / {Math.round(d.temp_min_c)}°</td>
                        <td className="num">{d.rain_mm} mm</td>
                        <td className="num">{d.humidity_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Provenance prov={data.provenance} />
              <p className="footer-note">{data.disclaimer}</p>
            </>
          );
        })()}
    </>
  );
}

export function RecommendPage() {
  const { t, name, pick } = useI18n();
  const [season, setSeason] = useState<"kharif" | "rabi" | "zaid">("rabi");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (data) resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [data]);

  async function run(farmId: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post("/crops/recommend", { farm_id: farmId, season });
      setData(res.data);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead title={t("crop_card")} lead={t("crop_card_sub")} back="/app/plan" />
      <FarmGate>
        {(farm) => (
          <>
            <div className="card">
              <Field label={t("season")}>
                <select className="select" value={season} onChange={(e) => setSeason(e.target.value as any)}>
                  <option value="kharif">{t("kharif")}</option>
                  <option value="rabi">{t("rabi")}</option>
                  <option value="zaid">{t("zaid")}</option>
                </select>
              </Field>
              <button className="btn btn-primary btn-block" disabled={busy} aria-busy={busy} onClick={() => void run(farm.id)}>
                {busy
                  ? <><span className="spinner" aria-hidden="true" />{t("recommending")}</>
                  : t("get_recommendation")}
              </button>
            </div>

            {error !== null && <ErrorNote error={error} />}

            {data && (
              <div ref={resultsRef} className="scroll-target">
                {data.input_provenance?.soil_source === "farm_soil_type_default" && (
                  <div className="alert warning">
                    <span className="dot" />
                    <div>
                      <strong>No soil test on file</strong>
                      <div>Ranking uses typical values for {farm.soil_type ?? "unrecorded"} soil. Add a soil test to make this specific.</div>
                      <Link to="/app/plan/soil">{t("soil_card")}</Link>
                    </div>
                  </div>
                )}
                {data.results.length === 0 && (
                  <div className="card"><Empty title={pick("No crop matched", "कोई फसल नहीं मिली")} body={data.explanation} /></div>
                )}
                {data.results.map((r: any) => (
                  <article className="card" key={r.crop_slug}>
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
                    <p className="footer-note">{r.yield_note}</p>
                  </article>
                ))}

                {data.suppressed.length > 0 && (
                  <details className="card">
                    <summary style={{ minHeight: 44, fontWeight: 700, cursor: "pointer" }}>
                      {t("suppressed")} ({data.suppressed.length})
                    </summary>
                    <ul className="list" style={{ marginTop: "0.5rem" }}>
                      {data.suppressed.map((s: any) => (
                        <li key={s.crop_slug}>
                          <strong>{name(s)}</strong>
                          <div className="small muted">{pick(s.reason_en, s.reason_hi)}</div>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}

                <p className="footer-note">
                  Model {data.model_version} · {data.provenance?.method}
                </p>
                <p className="footer-note">{data.disclaimer}</p>
              </div>
            )}
          </>
        )}
      </FarmGate>
    </>
  );
}

export function CropInfoPage() {
  const { t, name } = useI18n();
  const { slug: routeSlug } = useParams();
  const [crops, setCrops] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [slug, setSlug] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get("/crops").then((r) => setCrops(r.data)).catch(setError);
  }, []);

  useEffect(() => {
    if (routeSlug) setSlug(routeSlug);
  }, [routeSlug]);

  useEffect(() => {
    if (!slug) return;
    setDetail(null);
    api.get(`/crops/${slug}`).then((r) => setDetail(r.data)).catch(setError);
  }, [slug]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return crops;
    return crops.filter((c) => c.name_en.toLowerCase().includes(q) || c.name_hi.includes(query) || c.category.includes(q));
  }, [crops, query]);

  if (error) return <ErrorNote error={error} />;

  if (slug) {
    return (
      <>
        <PageHead title={detail ? name(detail) : t("loading")} back="/app/plan/crops" />
        {!detail ? <Loading /> : (
          <>
            <div className="card">
              <p style={{ fontStyle: "italic" }} className="muted small">{detail.scientific_name}</p>
              <p>{detail.description_en}</p>
              <dl>
                <div className="kv"><dt>Season</dt><dd>{detail.season}</dd></div>
                <div className="kv"><dt>Duration</dt><dd>{detail.duration_days ?? "—"} days</dd></div>
                <div className="kv"><dt>Water need</dt><dd>{detail.water_need}</dd></div>
                <div className="kv"><dt>Ideal pH</dt><dd>{detail.ph_range[0]}–{detail.ph_range[1]}</dd></div>
                <div className="kv"><dt>N / P / K target</dt><dd>{detail.nutrient_targets.n} / {detail.nutrient_targets.p} / {detail.nutrient_targets.k} kg/ha</dd></div>
              </dl>
            </div>
            <h2>Common problems</h2>
            {detail.diseases.length === 0 && <div className="card"><Empty body="No disease reference for this crop yet." /></div>}
            {detail.diseases.map((d: any) => (
              <Link className="tile" key={d.slug} to={`/app/protect/library/${d.slug}`}>
                <span className="icon"><Icon name="shield" /></span>
                <span><strong>{name(d)}</strong><span>{d.pathogen_type} · severity {d.severity_default}/5</span></span>
              </Link>
            ))}
          </>
        )}
      </>
    );
  }

  return (
    <>
      <PageHead title={t("library")} lead="Crop requirements and common diseases." back="/app/plan" />
      <div className="field">
        <input className="input" placeholder={`${t("search")}…`} value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      {crops.length === 0 && !error ? <Loading /> : (
        <div className="stack">
          {filtered.map((c) => (
            <button key={c.slug} className="tile" style={{ textAlign: "left", width: "100%" }} onClick={() => setSlug(c.slug)}>
              <span className="icon"><Icon name="sprout" /></span>
              <span>
                <strong>{name(c)}</strong>
                <span>{c.category} · {c.season} · {c.water_need} water</span>
              </span>
            </button>
          ))}
          {filtered.length === 0 && <Empty body="No crop matches that search." />}
        </div>
      )}
    </>
  );
}
