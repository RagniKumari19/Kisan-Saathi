import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth, useFarms, type District } from "../session";
import { useI18n } from "../i18n";
import { Empty, ErrorNote, Field, Icon, Loading, PageHead } from "../ui";

export function ProfilePage() {
  const { user, refreshUser, logout } = useAuth();
  const { farms, farm, reload, loading } = useFarms();
  const { t, pick, lang, setLang } = useI18n();
  const [name, setName] = useState(user?.full_name ?? "");
  const [profileMsg, setProfileMsg] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwMsg, setPwMsg] = useState("");
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    setName(user?.full_name ?? "");
  }, [user?.id]);

  useEffect(() => {
    api.get("/meta").then((r) => setMeta(r.data)).catch(() => {});
  }, []);

  if (!user) return <Loading />;

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setProfileMsg("");
    try {
      await api.patch("/users/me", { full_name: name, language: lang });
      await refreshUser();
      setProfileMsg("Saved.");
    } catch (err) {
      setError(err);
    }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPwMsg("");
    try {
      await api.patch("/auth/password", { current_password: pw.current, new_password: pw.next });
      setPwMsg("Password changed. Other devices were signed out.");
      setPw({ current: "", next: "" });
    } catch (err) {
      setError(err);
    }
  }

  return (
    <>
      <PageHead title={t("profile")} lead={`${user.phone} · ${user.role}`} />
      {error !== null && <ErrorNote error={error} />}

      <section className="card">
        <h2>{pick("Your details", "आपकी जानकारी")}</h2>
        <form onSubmit={saveProfile}>
          <Field label={t("full_name")}>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          </Field>
          <Field label={t("language")}>
            <select className="select" value={lang} onChange={(e) => setLang(e.target.value as any)}>
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
            </select>
          </Field>
          <button className="btn btn-primary" type="submit">{t("update_profile")}</button>
          {profileMsg && <p className="small" style={{ color: "var(--teal-700)" }}>{profileMsg}</p>}
        </form>
      </section>

      <section className="card">
        <div className="row between">
          <h2 style={{ margin: 0 }}>{pick("Your farms", "आपके खेत")}</h2>
          <Link className="btn btn-secondary btn-sm" to="/app/farms/new">{t("add_farm")}</Link>
        </div>
        {loading && <Loading />}
        {!loading && farms.length === 0 && <Empty body={t("no_farm_body")} />}
        <ul className="list">
          {farms.map((f) => (
            <li key={f.id}>
              <div className="row between">
                <div>
                  <strong>{f.name}</strong> {f.is_primary && <span className="tag">primary</span>}
                  <div className="small muted">
                    {f.village ? `${f.village}, ` : ""}{f.district?.name} · {f.area_acres ?? "—"} acres · {f.primary_crop_slug ?? "no crop set"}
                  </div>
                </div>
                <Link className="btn btn-ghost btn-sm" to={`/app/farms/${f.id}`}>Edit</Link>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {(user.role === "expert" || user.role === "admin") && (
        <Link className="tile" to="/app/expert">
          <span className="icon"><Icon name="shield" /></span>
          <span><strong>{t("expert_queue")}</strong><span>Review farmer photos and record a verdict.</span></span>
        </Link>
      )}
      {user.role === "admin" && (
        <Link className="tile" to="/app/admin" style={{ marginTop: "0.75rem" }}>
          <span className="icon"><Icon name="chart" /></span>
          <span><strong>{t("admin")}</strong><span>Platform stats, audit log and ingestion status.</span></span>
        </Link>
      )}

      <section className="card" style={{ marginTop: "0.9rem" }}>
        <h2>{t("change_password")}</h2>
        <form onSubmit={changePassword}>
          <Field label={t("current_password")}>
            <input className="input" type="password" autoComplete="current-password" value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })} required />
          </Field>
          <Field label={t("new_password")} hint={t("password_hint")}>
            <input className="input" type="password" autoComplete="new-password" minLength={8} value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })} required />
          </Field>
          <button className="btn btn-secondary" type="submit">{t("change_password")}</button>
          {pwMsg && <p className="small" style={{ color: "var(--teal-700)" }}>{pwMsg}</p>}
        </form>
      </section>

      {meta && (
        <section className="card">
          <h2>{pick("About this app", "इस ऐप के बारे में")}</h2>
          <dl>
            <div className="kv"><dt>Version</dt><dd>{meta.app_version}</dd></div>
            <div className="kv"><dt>Disease model</dt><dd>{meta.model_versions.disease}</dd></div>
            <div className="kv"><dt>Crop model</dt><dd>{meta.model_versions.crop_rec}</dd></div>
            <div className="kv"><dt>Prices</dt><dd>{meta.features.live_mandi_prices ? "Live" : "Demo fixtures"}</dd></div>
          </dl>
          <ul className="footer-note" style={{ paddingLeft: "1.1rem" }}>
            {meta.limitations.map((l: string, i: number) => <li key={i}>{l}</li>)}
          </ul>
        </section>
      )}

      <button className="btn btn-secondary btn-block" onClick={() => void logout()}>{t("sign_out")}</button>
      {farm && <p className="footer-note">Primary farm: {farm.name}, {farm.district?.name}</p>}
    </>
  );
}

export function FarmFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { farms, reload, selectFarm } = useFarms();
  const { t } = useI18n();
  const [districts, setDistricts] = useState<District[]>([]);
  const [crops, setCrops] = useState<any[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const editing = useMemo(() => farms.find((f) => f.id === id) ?? null, [farms, id]);

  const [form, setForm] = useState({
    name: "", district_slug: "", village: "", latitude: "", longitude: "",
    area_acres: "", soil_type: "black", irrigation_source: "rainfed",
    primary_crop_slug: "", is_primary: false,
  });

  useEffect(() => {
    api.get("/districts").then((r) => setDistricts(r.data)).catch(setError);
    api.get("/crops").then((r) => setCrops(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!editing) return;
    setForm({
      name: editing.name ?? "",
      district_slug: editing.district?.slug ?? "",
      village: editing.village ?? "",
      latitude: String(editing.latitude ?? ""),
      longitude: String(editing.longitude ?? ""),
      area_acres: editing.area_acres != null ? String(editing.area_acres) : "",
      soil_type: editing.soil_type ?? "black",
      irrigation_source: editing.irrigation_source ?? "rainfed",
      primary_crop_slug: editing.primary_crop_slug ?? "",
      is_primary: editing.is_primary,
    });
  }, [editing?.id]);

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function pickDistrict(slug: string) {
    const d = districts.find((x) => x.slug === slug);
    setForm((f) => ({
      ...f,
      district_slug: slug,
      latitude: f.latitude || (d ? String(d.latitude) : ""),
      longitude: f.longitude || (d ? String(d.longitude) : ""),
    }));
  }

  const grouped = useMemo(() => {
    const map = new Map<string, District[]>();
    districts.forEach((d) => {
      map.set(d.state, [...(map.get(d.state) ?? []), d]);
    });
    return [...map.entries()];
  }, [districts]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const payload = {
      name: form.name.trim(),
      district_slug: form.district_slug,
      village: form.village || null,
      latitude: Number(form.latitude),
      longitude: Number(form.longitude),
      area_acres: form.area_acres ? Number(form.area_acres) : null,
      soil_type: form.soil_type || null,
      irrigation_source: form.irrigation_source || null,
      primary_crop_slug: form.primary_crop_slug || null,
      is_primary: form.is_primary,
    };
    try {
      if (editing) await api.patch(`/users/me/farms/${editing.id}`, payload);
      else {
        const res = await api.post("/users/me/farms", payload);
        selectFarm(res.data.id);
      }
      await reload();
      navigate("/app");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead title={editing ? "Edit farm" : t("add_farm")} back="/app/profile" />
      {error !== null && <ErrorNote error={error} />}
      <form className="card" onSubmit={submit}>
        <Field label={t("farm_name")}>
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} required maxLength={80} />
        </Field>
        <Field label={t("district")}>
          <select className="select" value={form.district_slug} onChange={(e) => pickDistrict(e.target.value)} required>
            <option value="">Choose…</option>
            {grouped.map(([state, list]) => (
              <optgroup key={state} label={state}>
                {list.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
              </optgroup>
            ))}
          </select>
        </Field>
        <Field label={t("village")}>
          <input className="input" value={form.village} onChange={(e) => set("village", e.target.value)} maxLength={80} />
        </Field>
        <div className="grid two">
          <Field label={t("latitude")}>
            <input className="input" inputMode="decimal" value={form.latitude} onChange={(e) => set("latitude", e.target.value)} required />
          </Field>
          <Field label={t("longitude")}>
            <input className="input" inputMode="decimal" value={form.longitude} onChange={(e) => set("longitude", e.target.value)} required />
          </Field>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          style={{ marginBottom: "0.9rem" }}
          onClick={() => {
            if (!navigator.geolocation) return;
            navigator.geolocation.getCurrentPosition(
              (pos) => setForm((f) => ({
                ...f,
                latitude: pos.coords.latitude.toFixed(5),
                longitude: pos.coords.longitude.toFixed(5),
              })),
              () => setError(new ApiError(0, "GEO", "Could not read your location. Enter coordinates manually.")),
            );
          }}
        >
          <Icon name="map" size={20} /> {t("use_location")}
        </button>
        <Field label={t("area_acres")}>
          <input className="input" inputMode="decimal" value={form.area_acres} onChange={(e) => set("area_acres", e.target.value)} />
        </Field>
        <Field label={t("soil_type")}>
          <select className="select" value={form.soil_type} onChange={(e) => set("soil_type", e.target.value)}>
            {["black", "red", "alluvial", "laterite", "sandy", "unknown"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label={t("irrigation")}>
          <select className="select" value={form.irrigation_source} onChange={(e) => set("irrigation_source", e.target.value)}>
            {["rainfed", "borewell", "well", "canal", "tank", "river", "other"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label={t("primary_crop")}>
          <select className="select" value={form.primary_crop_slug} onChange={(e) => set("primary_crop_slug", e.target.value)}>
            <option value="">—</option>
            {crops.map((c) => <option key={c.slug} value={c.slug}>{c.name_en}</option>)}
          </select>
        </Field>
        <label className="checkbox" style={{ marginBottom: "1rem" }}>
          <input type="checkbox" checked={form.is_primary} onChange={(e) => set("is_primary", e.target.checked)} />
          <span>Make this my primary farm</span>
        </label>
        <button className="btn btn-primary btn-block" disabled={busy} type="submit">
          {busy ? t("saving") : t("save_farm")}
        </button>
      </form>

      {editing && farms.length > 1 && (
        <button
          className="btn btn-danger btn-block"
          onClick={async () => {
            if (!window.confirm("Remove this farm? Soil reports and checks for it will also be removed.")) return;
            try {
              await api.del(`/users/me/farms/${editing.id}`);
              await reload();
              navigate("/app");
            } catch (err) {
              setError(err);
            }
          }}
        >
          Delete farm
        </button>
      )}
    </>
  );
}

export function AdminPage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [stats, setStats] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState("");

  function loadAll() {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(setError);
    api.get("/admin/ingestion-runs").then((r) => setRuns(r.data)).catch(() => {});
    api.get("/admin/audit-logs?limit=25").then((r) => setAudit(r.data)).catch(() => {});
  }

  useEffect(() => {
    if (user?.role === "admin") loadAll();
  }, [user?.role]);

  if (!user || user.role !== "admin") {
    return (
      <div className="card">
        <h1>{t("admin")}</h1>
        <p className="muted">This area is for admin accounts only.</p>
        <Link className="btn btn-secondary" to="/app">{t("home")}</Link>
      </div>
    );
  }

  return (
    <>
      <PageHead title={t("admin")} lead="Platform health, audit trail and price ingestion." />
      {error !== null && <ErrorNote error={error} onRetry={loadAll} />}
      {!stats && !error && <Loading />}
      {stats && (
        <div className="grid three">
          {[
            ["Users", stats.users.total], ["Farmers", stats.users.farmer], ["Experts", stats.users.expert],
            ["Farms", stats.farms], ["Detections", stats.detections], ["Uncertain", stats.detections_uncertain],
            ["Pending review", stats.reviews_pending], ["Price rows", stats.price_rows], ["Markets", stats.markets],
          ].map(([label, value]) => (
            <div className="stat" key={String(label)}>
              <div className="label">{label}</div>
              <div className="value">{value}</div>
            </div>
          ))}
        </div>
      )}

      <section className="card" style={{ marginTop: "0.9rem" }}>
        <h2>Price ingestion</h2>
        <p className="small muted">
          Without AGMARKNET_API_KEY the app serves labelled demo prices. This button reports that honestly instead of pretending to fetch.
        </p>
        <button
          className="btn btn-secondary"
          onClick={async () => {
            setNote("");
            try {
              const r = await api.post("/admin/ingestion/run");
              setNote(`Run started: ${r.data.status}`);
              loadAll();
            } catch (e) {
              setNote(e instanceof ApiError ? e.message : "Could not start ingestion.");
            }
          }}
        >
          Run ingestion now
        </button>
        {note && <p className="small" style={{ marginTop: "0.5rem" }}>{note}</p>}
        {runs.length > 0 && (
          <table className="table" style={{ marginTop: "0.7rem" }}>
            <thead><tr><th>Source</th><th>Status</th><th className="num">Rows</th><th>Started</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.source}</td>
                  <td>{r.status}</td>
                  <td className="num">{r.rows_upserted}/{r.rows_received}</td>
                  <td className="small">{r.started_at?.slice(0, 16).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Audit log</h2>
        {audit.length === 0 && <Empty body="No audit rows yet." />}
        <table className="table">
          <thead><tr><th>Action</th><th>Entity</th><th>When</th></tr></thead>
          <tbody>
            {audit.map((a) => (
              <tr key={a.id}>
                <td>{a.action}</td>
                <td className="small muted">{a.entity}</td>
                <td className="small">{a.created_at?.slice(0, 16).replace("T", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
