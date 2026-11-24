import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useFarms } from "../session";
import { useI18n } from "../i18n";
import {
  Empty, ErrorNote, FarmGate, Field, Icon, Loading, Money, PageHead, Provenance,
} from "../ui";

function useCommodities() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api.get("/commodities").then((r) => setItems(r.data)).catch(() => {});
  }, []);
  return items;
}

function useCommodity(farmCrop: string | null | undefined) {
  const [commodity, setCommodity] = useState(farmCrop ?? "");
  useEffect(() => {
    if (!commodity && farmCrop) setCommodity(farmCrop);
  }, [farmCrop]);
  return [commodity, setCommodity] as const;
}

function CommoditySelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const commodities = useCommodities();
  const { name, t } = useI18n();
  return (
    <Field label={t("commodity")}>
      <select className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t("commodity")}…</option>
        {commodities.map((c) => <option key={c.slug} value={c.slug}>{name(c)}</option>)}
      </select>
    </Field>
  );
}

export function SellHub() {
  const { t, pick } = useI18n();
  const { farm } = useFarms();
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    api.get("/markets/status").then((r) => setStatus(r.data)).catch(() => {});
  }, []);

  return (
    <>
      <PageHead title={t("sell_title")} lead={t("sell_sub")} />
      {status && (
        <div className="alert info">
          <span className="dot" />
          <div>
            <strong>{pick("Prices in this build are demonstration data", "इस बिल्ड के भाव डेमो डेटा हैं")}</strong>
            <div className="small">
              Latest report: {status.latest_date ?? "—"} · {status.rows} rows across {status.markets_reporting} mandis.
              Nothing here is a live AGMARKNET feed.
            </div>
          </div>
        </div>
      )}
      {farm?.primary_crop_slug && (
        <p className="small muted">Your main crop: <strong>{farm.primary_crop_slug}</strong></p>
      )}
      <div className="stack">
        <Link className="tile" to="/app/sell/prices">
          <span className="icon"><Icon name="scale" /></span>
          <span><strong>{t("prices")}</strong><span>{pick("Latest modal price per mandi, with the arrival date.", "हर मंडी का ताज़ा भाव, आवक तारीख के साथ।")}</span></span>
        </Link>
        <Link className="tile" to="/app/sell/compare">
          <span className="icon"><Icon name="map" /></span>
          <span><strong>{t("compare")}</strong><span>{pick("Distance and price together, including estimated transport.", "दूरी और भाव साथ में, भाड़े के अनुमान के साथ।")}</span></span>
        </Link>
        <Link className="tile" to="/app/sell/trends">
          <span className="icon"><Icon name="chart" /></span>
          <span><strong>{t("trends")}</strong><span>{pick("What prices actually did over the last weeks.", "पिछले हफ्तों में भाव क्या रहे।")}</span></span>
        </Link>
        <Link className="tile" to="/app/sell/msp">
          <span className="icon"><Icon name="book" /></span>
          <span><strong>{t("msp")}</strong><span>{pick("Official support prices with source and year.", "स्रोत और वर्ष के साथ समर्थन मूल्य।")}</span></span>
        </Link>
      </div>
    </>
  );
}

export function PricesPage() {
  const { t, pick, name } = useI18n();
  const { farm } = useFarms();
  const [commodity, setCommodity] = useCommodity(farm?.primary_crop_slug);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!commodity) return;
    setData(null);
    setError(null);
    api.get(`/markets/prices?commodity=${encodeURIComponent(commodity)}&limit=50`)
      .then((r) => setData(r))
      .catch(setError);
  }, [commodity]);

  return (
    <>
      <PageHead title={t("prices")} lead={pick("Latest modal price for each mandi.", "हर मंडी का ताज़ा सबसे आम भाव।")} back="/app/sell" />
      <CommoditySelect value={commodity} onChange={setCommodity} />
      {!commodity && <Empty body={pick("Choose a commodity to see mandi prices.", "भाव देखने के लिए फसल चुनें।")} />}
      {error !== null && <ErrorNote error={error} />}
      {commodity && !data && !error && <Loading />}
      {data && (
        <>
          <div className="row wrap" style={{ marginBottom: "0.7rem" }}>
            <span className="badge badge-neutral">{data.data.length} mandis</span>
            {data.meta?.data_date && <span className="badge badge-neutral">{t("arrival_date")} {data.meta.data_date}</span>}
          </div>
          {data.data.length === 0 && <div className="card"><Empty body={data.meta?.note ?? t("no_prices")} /></div>}
          <div className="stack">
            {data.data.map((p: any) => (
              <article className="card" key={p.market_id}>
                <div className="row between">
                  <div>
                    <h3 style={{ margin: 0 }}>{p.market_name}</h3>
                    <span className="small muted">{p.district}, {p.state}</span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="big-number" style={{ fontSize: "1.4rem" }}><Money value={p.modal_price} /></div>
                    <span className="small muted">{t("per_quintal")}</span>
                  </div>
                </div>
                <div className="row between small muted" style={{ marginTop: "0.4rem" }}>
                  <span>{t("min_price")} <Money value={p.min_price} /> · {t("max_price")} <Money value={p.max_price} /></span>
                  <span>{t("arrival_date")}: {p.arrival_date}</span>
                </div>
                <div className="small muted">{p.variety} · {p.grade} · {p.commodity_name_en ?? name({ name_en: p.commodity, name_hi: p.commodity })}</div>
              </article>
            ))}
          </div>
          {data.meta?.provenance && <Provenance prov={data.meta.provenance} />}
          <p className="footer-note">
            {pick("Modal price is the most common price, not an average.", "सबसे आम भाव का मतलब औसत भाव नहीं है।")}
          </p>
        </>
      )}
    </>
  );
}

export function ComparePage() {
  const { t, pick } = useI18n();
  const { farm } = useFarms();
  const [commodity, setCommodity] = useCommodity(farm?.primary_crop_slug);
  const [radius, setRadius] = useState(120);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!commodity || !farm) return;
    setData(null);
    setError(null);
    api.get(`/markets/compare?commodity=${encodeURIComponent(commodity)}&farm_id=${farm.id}&radius_km=${radius}`)
      .then((r) => setData(r.data))
      .catch(setError);
  }, [commodity, radius, farm?.id]);

  return (
    <>
      <PageHead title={t("compare")} lead={pick("Same commodity, different mandis, with distance.", "एक ही फसल, अलग मंडियां, दूरी के साथ।")} back="/app/sell" />
      <CommoditySelect value={commodity} onChange={setCommodity} />
      <Field label="Radius">
        <select className="select" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
          <option value={50}>Within 50 km</option>
          <option value={100}>Within 100 km</option>
          <option value={120}>Within 120 km</option>
          <option value={300}>Within 300 km</option>
        </select>
      </Field>
      {error !== null && <ErrorNote error={error} />}
      {commodity && !data && !error && <Loading />}
      {data && data.markets.length === 0 && (
        <div className="card">
          <Empty
            title={pick("No reported price in this radius", "इस दायरे में कोई भाव नहीं")}
            body={pick("Try a larger radius or a different commodity. A blank screen would hide the gap — this is the gap.", "बड़ा दायरा या दूसरी फसल चुनें।")}
          />
        </div>
      )}
      {data && data.markets.length > 0 && (
        <>
          <div className="card">
            <div className="row between">
              <div>
                <div className="small muted">{pick("Best modal price", "सबसे अच्छा भाव")}</div>
                <strong>{data.markets[0].market_name}</strong>
              </div>
              <div className="big-number"><Money value={data.markets[0].modal_price} /></div>
            </div>
            {data.spread != null && (
              <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
                Spread across mandis: <Money value={data.spread} /> ({data.spread_pct}%)
              </p>
            )}
          </div>
          <div className="stack">
            {data.markets.map((m: any) => (
              <article className="card" key={m.market_id}>
                <div className="row between">
                  <div>
                    <h3 style={{ margin: 0 }}>{m.market_name}</h3>
                    <span className="small muted">{m.district} · {m.distance_km != null ? `${m.distance_km} km` : "distance unknown"}</span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div><Money value={m.modal_price} /></div>
                    <span className="small muted">{t("arrival_date")} {m.arrival_date}</span>
                  </div>
                </div>
                {m.net_after_transport != null && (
                  <div className="row between small" style={{ marginTop: "0.4rem" }}>
                    <span className="muted">{t("net_after_transport")}</span>
                    <strong><Money value={m.net_after_transport} /></strong>
                  </div>
                )}
                {m.transport_note && <div className="footer-note" style={{ marginTop: 2 }}>{m.transport_note}</div>}
              </article>
            ))}
          </div>
          <Provenance prov={data.provenance} />
          <ul className="footer-note" style={{ paddingLeft: "1.1rem" }}>
            {(data.notes ?? []).map((n: string, i: number) => <li key={i}>{n}</li>)}
          </ul>
        </>
      )}
    </>
  );
}

function TrendChart({ points }: { points: any[] }) {
  const { t } = useI18n();
  const width = 340;
  const height = 170;
  const pad = 26;
  const values = points.map((p) => p.modal_price).filter((v) => v != null) as number[];
  if (values.length < 2) return <Empty body={t("no_data")} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i: number) => pad + (i / Math.max(1, points.length - 1)) * (width - pad * 2);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad * 2);

  const segments: string[] = [];
  let current: string[] = [];
  points.forEach((p, i) => {
    if (p.modal_price == null) {
      if (current.length > 1) segments.push(current.join(" "));
      current = [];
    } else {
      current.push(`${x(i).toFixed(1)},${y(p.modal_price).toFixed(1)}`);
    }
  });
  if (current.length > 1) segments.push(current.join(" "));

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Price trend">
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="var(--line-strong)" />
      <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="var(--line-strong)" />
      <text x={4} y={pad + 4}>{Math.round(max)}</text>
      <text x={4} y={height - pad}>{Math.round(min)}</text>
      {segments.map((s, i) => (
        <polyline key={i} points={s} fill="none" stroke="var(--teal-600)" strokeWidth="2.5" strokeLinejoin="round" />
      ))}
      {points.map((p, i) =>
        p.modal_price != null ? <circle key={i} cx={x(i)} cy={y(p.modal_price)} r="2.4" fill="var(--teal-600)" /> : null,
      )}
      <text x={pad} y={height - 6}>{points[0]?.date?.slice(5)}</text>
      <text x={width - pad - 26} y={height - 6}>{points[points.length - 1]?.date?.slice(5)}</text>
    </svg>
  );
}

export function TrendsPage() {
  const { t, pick, name } = useI18n();
  const { farm } = useFarms();
  const [commodity, setCommodity] = useCommodity(farm?.primary_crop_slug);
  const [days, setDays] = useState(30);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!commodity) return;
    setData(null);
    setError(null);
    api.get(`/markets/trends?commodity=${encodeURIComponent(commodity)}&days=${days}&district_id=${farm?.district_id ?? ""}`)
      .then((r) => setData(r.data))
      .catch(setError);
  }, [commodity, days, farm?.district_id]);

  const summary = data?.summary;

  return (
    <>
      <PageHead title={t("trends")} lead={pick("Median modal price across reporting mandis.", "रिपोर्ट करने वाली मंडियों का औसत भाव।")} back="/app/sell" />
      <CommoditySelect value={commodity} onChange={setCommodity} />
      <Field label="Window">
        <select className="select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={60}>60 days</option>
          <option value={90}>90 days</option>
        </select>
      </Field>
      {error !== null && <ErrorNote error={error} />}
      {commodity && !data && !error && <Loading />}
      {data && (
        <>
          <div className="card">
            <TrendChart points={data.points} />
            {data.missing_days > 0 && (
              <p className="small muted">{data.missing_days} day(s) have no mandi report; the line breaks there.</p>
            )}
          </div>
          {summary && (
            <div className="grid three">
              <div className="stat">
                <div className="label">Change</div>
                <div className={`value ${summary.direction === "up" ? "" : ""}`} style={{ color: summary.direction === "up" ? "var(--teal-700)" : summary.direction === "down" ? "var(--red-700)" : undefined }}>
                  {summary.change_pct > 0 ? "+" : ""}{summary.change_pct}%
                </div>
              </div>
              <div className="stat">
                <div className="label">Median</div>
                <div className="value"><Money value={summary.median_price} /></div>
              </div>
              <div className="stat">
                <div className="label">Volatility</div>
                <div className="value">{summary.volatility_pct}%</div>
              </div>
            </div>
          )}
          {data.provenance && <Provenance prov={data.provenance} />}
          <p className="footer-note">{data.note}</p>
        </>
      )}
    </>
  );
}

export function MspPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get("/markets/msp").then((r) => setRows(r.data)).catch(setError);
  }, []);

  return (
    <>
      <PageHead title={t("msp")} lead="Minimum support prices with the official source." back="/app/sell" />
      {error !== null && <ErrorNote error={error} />}
      {!rows && !error && <Loading />}
      <div className="card flush">
        <table className="table">
          <thead>
            <tr><th>Commodity</th><th>Season</th><th className="num">₹/quintal</th></tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.commodity + r.season}>
                <td>
                  {r.commodity}
                  <div className="small muted">{[r.marketing_year, r.last_verified && `verified ${r.last_verified}`].filter(Boolean).join(" · ")}</div>
                </td>
                <td>{r.season}</td>
                <td className="num"><Money value={r.price_per_quintal} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows?.[0] && (
        <p className="footer-note">
          Source: <a href={rows[0].source_url} target="_blank" rel="noreferrer">Official MSP table</a>. Rates are for the marketing year shown; always check the latest government notification.
        </p>
      )}
    </>
  );
}
