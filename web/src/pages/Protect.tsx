import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, mediaUrl, ApiError } from "../api";
import { useAuth, useFarms } from "../session";
import { useI18n } from "../i18n";
import {
  Empty, ErrorNote, FarmGate, Field, Icon, Loading, MockBadge, PageHead,
} from "../ui";

export function ProtectHub() {
  const { t, pick } = useI18n();
  const { farm } = useFarms();
  const [alerts, setAlerts] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!farm) return;
    api.get(`/disease/risk-alerts?farm_id=${farm.id}`)
      .then((r) => setAlerts(r.data))
      .catch(setError);
  }, [farm?.id]);

  return (
    <>
      <PageHead title={t("protect_title")} lead={t("protect_sub")} />
      <Link className="btn btn-primary btn-block" to="/app/protect/capture" style={{ marginBottom: "0.9rem" }}>
        <Icon name="camera" /> {t("check_leaf")}
      </Link>

      <h2>{pick("Risk this week", "इस हफ्ते का खतरा")}</h2>
      {error !== null && <ErrorNote error={error} />}
      {!alerts && !error && <Loading />}
      {alerts && alerts.alerts?.length === 0 && (
        <div className="card"><Empty body={alerts.note ?? pick("No elevated disease risk from the forecast.", "पूर्वानुमान से कोई अधिक रोग जोखिम नहीं।")} /></div>
      )}
      {alerts?.alerts?.map((a: any) => (
        <div className={`alert ${a.severity >= 4 ? "danger" : "warning"}`} key={a.disease_slug}>
          <span className="dot" />
          <div>
            <strong>{pick(a.name_en, a.name_hi)}</strong>
            <div className="small">{pick(a.reason_en, a.reason_hi)}</div>
            <Link className="small" to={`/app/protect/library/${a.disease_slug}`}>{t("view_library")}</Link>
          </div>
        </div>
      ))}
      {alerts?.provenance && <MockBadge isMock={Boolean(alerts.provenance.is_mock)} />}

      <h2 style={{ marginTop: "1.2rem" }}>{pick("More", "और")}</h2>
      <div className="stack">
        <Link className="tile" to="/app/protect/history">
          <span className="icon"><Icon name="history" /></span>
          <span><strong>{t("history")}</strong><span>{pick("Every past leaf check and its result.", "पिछली सभी पत्ती जांच और उनका नतीजा।")}</span></span>
        </Link>
        <Link className="tile" to="/app/protect/library">
          <span className="icon"><Icon name="book" /></span>
          <span><strong>{t("library")}</strong><span>{pick("Symptoms and sourced treatments, no AI involved.", "लक्षण और स्रोत के साथ उपचार।")}</span></span>
        </Link>
      </div>
      <p className="footer-note">
        {pick(
          "The leaf checker in this build is a demonstration model. It never shows a chemical dose below the confidence threshold.",
          "इस बिल्ड में पत्ती जांच डेमो मॉडल है। भरोसे की सीमा से नीचे कोई दवा की मात्रा नहीं दिखाई जाती।",
        )}
      </p>
    </>
  );
}

export function CapturePage() {
  const { t, pick } = useI18n();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [crop, setCrop] = useState("");
  const [crops, setCrops] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get("/crops").then((r) => setCrops(r.data)).catch(() => {});
  }, []);

  function choose(f: File | null) {
    setFile(f);
    setError(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  return (
    <>
      <PageHead title={t("check_leaf")} lead={t("upload_leaf")} back="/app/protect" />
      <FarmGate>
        {(farm) => (
          <>
            {error !== null && <ErrorNote error={error} />}
            <div className="card">
              {preview ? (
                <img src={preview} alt="Selected leaf" style={{ width: "100%", borderRadius: 12, marginBottom: "0.8rem" }} />
              ) : (
                <div className="center" style={{ background: "var(--sage)", borderRadius: 12, marginBottom: "0.8rem", padding: "2rem 1rem" }}>
                  <Icon name="camera" size={40} />
                  <span className="muted small">{pick("One leaf, filling the frame, in daylight.", "एक पत्ती, फ्रेम में भरकर, दिन की रोशनी में।")}</span>
                </div>
              )}
              <label className="btn btn-secondary btn-block" style={{ cursor: "pointer" }}>
                <Icon name="camera" /> {t("choose_photo")}
                <input
                  type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
                  style={{ display: "none" }}
                  onChange={(e) => choose(e.target.files?.[0] ?? null)}
                />
              </label>

              <Field label={`Crop (optional)`}>
                <select className="select" value={crop} onChange={(e) => setCrop(e.target.value)}>
                  <option value="">{pick("Let the app decide from the farm", "ऐप खेत से तय करे")}</option>
                  {crops.map((c) => <option key={c.slug} value={c.slug}>{c.name_en}</option>)}
                </select>
              </Field>

              <button
                className="btn btn-primary btn-block"
                disabled={!file || busy}
                onClick={async () => {
                  if (!file) return;
                  setBusy(true);
                  setError(null);
                  const form = new FormData();
                  form.append("image", file);
                  form.append("farm_id", farm.id);
                  if (crop) form.append("crop_slug", crop);
                  try {
                    const res = await api.upload("/disease/detect", form);
                    navigate(`/app/protect/${res.data.id}`);
                  } catch (e) {
                    setError(e);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy ? t("checking") : t("check_now")}
              </button>
            </div>
            <p className="footer-note">
              {pick(
                "Photos are stripped of location metadata and stored on this server. Your photo is only used for this check.",
                "फोटो से लोकेशन जानकारी हटा दी जाती है। फोटो सिर्फ इस जांच के लिए उपयोग होती है।",
              )}
            </p>
          </>
        )}
      </FarmGate>
    </>
  );
}

export function HistoryPage() {
  const { t, pick } = useI18n();
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get("/disease/detections?limit=50").then((r) => setItems(r.data)).catch(setError);
  }, []);

  return (
    <>
      <PageHead title={t("history")} lead={pick("Every leaf check you have made.", "आपकी सभी पत्ती जांच।")} back="/app/protect" />
      {error !== null && <ErrorNote error={error} />}
      {!items && !error && <Loading />}
      {items && items.length === 0 && (
        <div className="card"><Empty title={t("no_data")} body={t("upload_leaf")} action={<Link className="btn btn-primary" to="/app/protect/capture">{t("check_leaf")}</Link>} /></div>
      )}
      <div className="stack">
        {items?.map((d) => (
          <Link className="card" to={`/app/protect/${d.id}`} key={d.id} style={{ display: "block", textDecoration: "none", color: "inherit" }}>
            <div className="row between">
              <div>
                <strong>{d.status === "uncertain" ? t("uncertain_title") : (d.predicted_slug ?? "Detected").replace(/__/g, " · ").replace(/_/g, " ")}</strong>
                <div className="small muted">{d.created_at?.slice(0, 16).replace("T", " ")} · {d.crop_slug ?? "unknown crop"}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span className={`pill ${d.status === "uncertain" ? "warn" : "good"}`}>
                  {d.confidence ? `${Math.round(d.confidence * 100)}%` : "—"}
                </span>
                {d.review_status !== "none" && <div className="small muted">{d.review_status}</div>}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

export function DetectionPage() {
  const { id } = useParams();
  const { t, pick } = useI18n();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [expertDisease, setExpertDisease] = useState<any>(null);

  useEffect(() => {
    api.get(`/disease/detections/${id}`).then((r) => setData(r.data)).catch(setError);
  }, [id]);

  useEffect(() => {
    const slug = data?.expert_agreed_slug;
    if (!slug || data?.review_status !== "corrected") return;
    api.get(`/disease/library/${slug}`).then((r) => setExpertDisease(r.data)).catch(() => {});
  }, [data?.expert_agreed_slug, data?.review_status]);

  if (error) return <ErrorNote error={error} />;
  if (!data) return <Loading />;

  const uncertain = data.status === "uncertain";
  const corrected = data.review_status === "corrected" && expertDisease;
  const headline = corrected
    ? pick(expertDisease.name_en, expertDisease.name_hi)
    : pick(data.predicted?.name_en, data.predicted?.name_hi) || "Result";
  const treatments = corrected ? expertDisease.treatments : data.treatments;

  return (
    <>
      <PageHead title={uncertain ? t("uncertain_title") : headline} back="/app/protect" />
      {uncertain ? (
        <div className="alert warning">
          <span className="dot" />
          <div>
            <strong>{pick("No treatment shown", "कोई उपचार नहीं दिखाया")}</strong>
            <div>{pick(data.message_en, data.message_hi)}</div>
            <div className="small" style={{ marginTop: 6 }}>
              {t("confidence")}: {Math.round((data.confidence ?? 0) * 100)}% (needs {Math.round(data.threshold * 100)}%)
            </div>
          </div>
        </div>
      ) : (
        <div className="alert success">
          <span className="dot" />
          <div>
            <strong>
              {corrected
                ? `${pick("Expert diagnosis", "विशेषज्ञ निदान")}: ${headline}`
                : pick(data.message_en, data.message_hi)}
            </strong>
            <div className="small">
              {corrected
                ? `Model had suggested ${pick(data.predicted?.name_en, data.predicted?.name_hi)} at ${Math.round(data.confidence * 100)}%.`
                : `${t("confidence")}: ${Math.round(data.confidence * 100)}% · severity ${data.severity}/5`}
            </div>
          </div>
        </div>
      )}

      {data.image_url && (
        <img src={mediaUrl(data.image_url)} alt="Checked leaf" className="card flush" style={{ width: "100%", padding: 0 }} />
      )}
      <div className="row wrap" style={{ marginBottom: "0.8rem" }}>
        <MockBadge isMock={data.is_mock} />
        <span className="badge badge-neutral">{data.model?.version}</span>
        {data.review_status !== "none" && <span className="badge badge-info">{data.review_status}</span>}
      </div>

      {data.review_status === "corrected" && (
        <div className="alert info">
          <span className="dot" />
          <div>
            <strong>{pick("An expert corrected this diagnosis", "विशेषज्ञ ने यह पहचान सुधारी")}</strong>
            <div>{corrected ? `${pick(expertDisease.name_en, expertDisease.name_hi)} (${expertDisease.crop?.name_en ?? expertDisease.crop_slug})` : (data.expert_agreed_slug ?? "").replace(/__/g, " · ").replace(/_/g, " ")}</div>
            {data.expert_note && <div className="small" style={{ marginTop: 4 }}>“{data.expert_note}”</div>}
          </div>
        </div>
      )}
      {data.review_status === "confirmed" && (
        <div className="alert success">
          <span className="dot" />
          <div>
            <strong>{pick("An expert confirmed this diagnosis", "विशेषज्ञ ने यह पहचान पुष्ट की")}</strong>
            {data.expert_note && <div className="small">{data.expert_note}</div>}
          </div>
        </div>
      )}

      {!uncertain && data.predicted && (
        <section className="card">
          <h2 style={{ marginTop: 0 }}>{pick("Symptoms", "लक्षण")}</h2>
          <p>{corrected ? pick(expertDisease.symptoms_en, expertDisease.symptoms_hi) : pick(data.symptoms_en, data.symptoms_hi)}</p>
          <p className="small muted">{corrected ? expertDisease.spread_en : data.spread_en}</p>
        </section>
      )}

      {!uncertain && treatments?.length > 0 && (
        <>
          <h2>{t("treatments")}</h2>
          {treatments.map((tr: any, i: number) => (
            <article className="card" key={i}>
              <div className="row between">
                <h3 style={{ margin: 0 }}>{tr.title}</h3>
                <span className="badge badge-neutral">{tr.kind}</span>
              </div>
              <p className="small" style={{ marginTop: "0.4rem" }}>{tr.detail}</p>
              {tr.dosage && <p className="small"><strong>Dose:</strong> {tr.dosage}</p>}
              {tr.safety_notes && <p className="alert warning small" style={{ padding: "0.5rem 0.7rem" }}>{tr.safety_notes}</p>}
              <div className="row wrap small">
                <a href={tr.source_url} target="_blank" rel="noreferrer">{t("source")}</a>
                {tr.last_verified && <span className="muted">{t("verified")} {tr.last_verified}</span>}
              </div>
            </article>
          ))}
        </>
      )}

      <h2>{pick("Next steps", "आगे क्या करें")}</h2>
      <ol className="card" style={{ paddingLeft: "2rem" }}>
        {(data.next_steps ?? []).map((s: any, i: number) => (
          <li key={i} style={{ marginBottom: "0.4rem" }}>{pick(s.en, s.hi)}</li>
        ))}
      </ol>

      <div className="card">
        {sent || data.review_status === "pending_expert" ? (
          <div className="row"><span className="pill good">{t("escalate_done")}</span></div>
        ) : (
          <button
            className="btn btn-secondary btn-block"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api.post(`/disease/detections/${id}/escalate`);
                setSent(true);
              } catch (e) {
                setError(e);
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("ask_expert")}
          </button>
        )}
      </div>
      <p className="footer-note">{data.disclaimer}</p>
    </>
  );
}

export function LibraryPage() {
  const { t, name, pick } = useI18n();
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.get("/disease/library").then((r) => setItems(r.data)).catch(setError);
  }, []);

  const filtered = (items ?? []).filter((d) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return d.name_en.toLowerCase().includes(q) || d.name_hi.includes(query) || d.crop_slug.includes(q);
  });

  return (
    <>
      <PageHead title={t("library")} lead={pick("Symptoms, spread and sourced treatments.", "लक्षण, फैलाव और स्रोत के साथ उपचार।")} back="/app/protect" />
      {error !== null && <ErrorNote error={error} />}
      <div className="field">
        <input className="input" placeholder={`${t("search")}…`} value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      {!items && !error && <Loading />}
      <div className="stack">
        {filtered.map((d) => (
          <Link className="tile" key={d.slug} to={`/app/protect/library/${d.slug}`}>
            <span className="icon"><Icon name="shield" /></span>
            <span>
              <strong>{name(d)}</strong>
              <span>{d.crop?.name_en ?? d.crop_slug} · {d.pathogen_type} · {d.treatments.length} steps</span>
            </span>
          </Link>
        ))}
      </div>
      {filtered.length === 0 && items && <Empty body="No disease matches that search." />}
    </>
  );
}

export function LibraryItemPage() {
  const { slug } = useParams();
  const { t, name, pick } = useI18n();
  const [d, setD] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get(`/disease/library/${slug}`).then((r) => setD(r.data)).catch(setError);
  }, [slug]);

  if (error) return <ErrorNote error={error} />;
  if (!d) return <Loading />;

  return (
    <>
      <PageHead title={name(d)} lead={`${d.crop?.name_en ?? d.crop_slug} · ${d.pathogen_type}`} back="/app/protect/library" />
      <section className="card">
        <h3>{pick("Symptoms", "लक्षण")}</h3>
        <p>{pick(d.symptoms_en, d.symptoms_hi)}</p>
        <h3>{pick("How it spreads", "कैसे फैलता है")}</h3>
        <p>{d.spread_en}</p>
        <div className="row wrap small">
          <span className="pill">Severity {d.severity_default}/5</span>
          {d.risk_window?.humidity_min && <span className="pill">Humidity ≥ {d.risk_window.humidity_min}%</span>}
          {d.risk_window?.temp_min != null && <span className="pill">{d.risk_window.temp_min}–{d.risk_window.temp_max} °C</span>}
        </div>
      </section>
      <h2>{t("treatments")}</h2>
      {d.treatments.map((tr: any, i: number) => (
        <article className="card" key={i}>
          <div className="row between">
            <h3 style={{ margin: 0 }}>{tr.title}</h3>
            <span className="badge badge-neutral">{tr.kind}</span>
          </div>
          <p className="small" style={{ marginTop: "0.4rem" }}>{tr.detail}</p>
          {tr.dosage && <p className="small"><strong>Dose:</strong> {tr.dosage}</p>}
          {tr.safety_notes && <p className="alert warning small" style={{ padding: "0.5rem 0.7rem" }}>{tr.safety_notes}</p>}
          <div className="row wrap small">
            <a href={tr.source_url} target="_blank" rel="noreferrer">{t("source")}</a>
            {tr.last_verified && <span className="muted">{t("verified")} {tr.last_verified}</span>}
          </div>
        </article>
      ))}
      <p className="footer-note">{d.disclaimer}</p>
    </>
  );
}

export function ExpertPage() {
  const { user } = useAuth();
  const { t, name } = useI18n();
  const [queue, setQueue] = useState<any[] | null>(null);
  const [diseases, setDiseases] = useState<any[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [decision, setDecision] = useState<"confirmed" | "corrected" | "rejected">("confirmed");
  const [slug, setSlug] = useState("");
  const [note, setNote] = useState("");

  const load = () => {
    api.get("/disease/queue").then((r) => setQueue(r.data)).catch(setError);
  };

  useEffect(() => {
    if (user?.role === "farmer") return;
    load();
    api.get("/disease/library").then((r) => setDiseases(r.data)).catch(() => {});
  }, [user?.role]);

  if (!user || user.role === "farmer") {
    return (
      <div className="card">
        <h1>{t("expert_queue")}</h1>
        <p className="muted">This area is for expert and admin accounts only.</p>
        <Link className="btn btn-secondary" to="/app">{t("home")}</Link>
      </div>
    );
  }

  async function submit(id: string) {
    setError(null);
    try {
      await api.patch(`/disease/detections/${id}/review`, {
        decision, disease_slug: decision === "corrected" ? slug : undefined, note: note || undefined,
      });
      setOpenId(null);
      setNote("");
      setSlug("");
      setDecision("confirmed");
      load();
    } catch (e) {
      setError(e);
    }
  }

  return (
    <>
      <PageHead title={t("expert_queue")} lead="Farmer photos waiting for a human verdict." />
      {error !== null && <ErrorNote error={error} />}
      {!queue && !error && <Loading />}
      {queue && queue.length === 0 && <div className="card"><Empty body="No photos are waiting for review." /></div>}
      <div className="stack">
        {queue?.map((item) => (
          <article className="card" key={item.id}>
            <div className="row between">
              <div>
                <strong>{item.crop_slug ?? "Unknown crop"}</strong>
                <div className="small muted">{item.created_at?.slice(0, 16).replace("T", " ")} · model {item.confidence ? `${Math.round(item.confidence * 100)}%` : "n/a"}</div>
              </div>
              <MockBadge isMock={item.is_mock} />
            </div>
            {item.image_url && (
              <img src={mediaUrl(item.image_url)} alt="" style={{ width: "100%", borderRadius: 10, margin: "0.6rem 0" }} />
            )}
            {openId === item.id ? (
              <div>
                <Field label="Decision">
                  <select className="select" value={decision} onChange={(e) => setDecision(e.target.value as any)}>
                    <option value="confirmed">Confirm the model</option>
                    <option value="corrected">Correct it</option>
                    <option value="rejected">Reject (not a disease)</option>
                  </select>
                </Field>
                {decision === "corrected" && (
                  <Field label="Correct disease">
                    <select className="select" value={slug} onChange={(e) => setSlug(e.target.value)}>
                      <option value="">Choose…</option>
                      {diseases.map((d) => <option key={d.slug} value={d.slug}>{name(d)}</option>)}
                    </select>
                  </Field>
                )}
                <Field label={t("note")}>
                  <textarea className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
                </Field>
                <div className="row">
                  <button className="btn btn-primary" onClick={() => void submit(item.id)} disabled={decision === "corrected" && !slug}>{t("save")}</button>
                  <button className="btn btn-secondary" onClick={() => setOpenId(null)}>{t("cancel")}</button>
                </div>
              </div>
            ) : (
              <button className="btn btn-secondary btn-block" onClick={() => { setOpenId(item.id); setDecision(item.confidence ? "confirmed" : "corrected"); }}>
                {t("review")}
              </button>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
