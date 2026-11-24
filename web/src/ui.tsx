import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { useI18n } from "./i18n";
import { ApiError } from "./api";
import { useFarms, type Farm } from "./session";

export type IconName =
  | "home" | "leaf" | "shield" | "rupee" | "user" | "soil" | "cloud" | "sprout"
  | "camera" | "history" | "book" | "chart" | "scale" | "map" | "alert" | "back" | "check" | "info"
  | "logout" | "sun" | "moon" | "more";

const PATHS: Record<IconName, ReactNode> = {
  home: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></>,
  leaf: <><path d="M20 4C10 4 4 9 4 15a5 5 0 0 0 5 5c6 0 11-6 11-16Z" /><path d="M4 21c2-6 6-10 12-13" /></>,
  shield: <><path d="M12 3 4.5 6v6c0 5 3.2 8 7.5 9 4.3-1 7.5-4 7.5-9V6L12 3Z" /><path d="m9 12 2 2 4-4" /></>,
  rupee: <><path d="M7 4h10" /><path d="M7 9h10" /><path d="M7 4c6 0 6 9 0 9h-1l8 8" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6" /></>,
  soil: <><path d="M12 3v9" /><path d="M8 7h8" /><path d="M5 14h14l-2 7H7l-2-7Z" /></>,
  cloud: <><path d="M7 18a4 4 0 0 1 0-8 6 6 0 0 1 11.5 1.5A3.5 3.5 0 0 1 18 18H7Z" /><path d="M8 21h8" /></>,
  sprout: <><path d="M12 21v-8" /><path d="M12 13C12 8 8 5 3 5c0 5 4 8 9 8Z" /><path d="M12 13c0-4 3-7 8-7 0 4-3 7-8 7Z" /></>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4V8Z" /><circle cx="12" cy="13" r="3.5" /></>,
  history: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></>,
  book: <><path d="M4 5c3-1 6-1 8 1 2-2 5-2 8-1v14c-3-1-6-1-8 1-2-2-5-2-8-1V5Z" /><path d="M12 6v14" /></>,
  chart: <><path d="M4 20V4" /><path d="M4 20h16" /><path d="m7 15 4-5 3 3 5-7" /></>,
  scale: <><path d="M12 3v18" /><path d="M6 21h12" /><path d="M4 7h16" /><path d="M4 7 1 14h6L4 7Z" /><path d="m20 7-3 7h6l-3-7Z" /></>,
  map: <><path d="m3 6 6-2 6 2 6-2v14l-6 2-6-2-6 2V6Z" /><path d="M9 4v14M15 6v14" /></>,
  alert: <><path d="M12 3 2 20h20L12 3Z" /><path d="M12 9v5" /><path d="M12 17h.01" /></>,
  back: <><path d="M15 5 8 12l7 7" /></>,
  check: <><path d="m4 12 5 5L20 6" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6" /><path d="M12 7h.01" /></>,
  logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /><path d="m10 8-4 4 4 4" /><path d="M6 12h9" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <><path d="M20 14.5A8 8 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" /></>,
  more: <><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></>,
};

export function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}

export function MockBadge({ isMock, live }: { isMock: boolean; live?: boolean }) {
  const { t } = useI18n();
  if (isMock) return <span className="badge badge-mock">{t("mock_badge")}</span>;
  return <span className="badge badge-live">{live ? t("live_badge") : "Verified"}</span>;
}

export function Provenance({ prov, className }: { prov?: any; className?: string }) {
  const { t } = useI18n();
  if (!prov) return null;
  const parts: string[] = [];
  if (prov.data_date) parts.push(`${t("arrival_date")}: ${prov.data_date}`);
  if (prov.source) parts.push(`${t("source")}: ${prov.source.replace(/_/g, " ")}`);
  if (prov.stale) parts.push("Data may be stale.");
  return (
    <div className={`footer-note ${className ?? ""}`}>
      <span className="row wrap" style={{ gap: "0.4rem" }}>
        <MockBadge isMock={Boolean(prov.is_mock)} />
        {parts.length > 0 && <span>{parts.join(" · ")}</span>}
      </span>
      {prov.note && <div style={{ marginTop: 4 }}>{prov.note}</div>}
    </div>
  );
}

export function Loading({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div className="center" role="status" aria-live="polite">
      <div className="spinner" />
      <span className="muted">{label ?? t("loading")}</span>
    </div>
  );
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useI18n();
  const message = error instanceof ApiError ? error.message : t("error_generic");
  const details = error instanceof ApiError ? error.details : [];
  return (
    <div className="alert danger" role="alert">
      <span className="dot" />
      <div>
        <strong>{message}</strong>
        {details.length > 0 && (
          <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
            {details.map((d, i) => (
              <li key={i} className="small">{d.field ? `${d.field}: ` : ""}{d.issue}</li>
            ))}
          </ul>
        )}
        {onRetry && (
          <div style={{ marginTop: "0.5rem" }}>
            <button className="btn btn-secondary btn-sm" onClick={onRetry}>{t("retry")}</button>
          </div>
        )}
      </div>
    </div>
  );
}

export function Empty({ title, body, action }: { title?: string; body?: string; action?: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className="center">
      <div style={{ color: "var(--muted)" }}><Icon name="info" size={34} /></div>
      <strong>{title ?? t("no_data")}</strong>
      {body && <p className="muted small" style={{ maxWidth: 380, margin: 0 }}>{body}</p>}
      {action}
    </div>
  );
}

export function PageHead({ title, lead, back }: { title: string; lead?: string; back?: string }) {
  const { t } = useI18n();
  return (
    <header className="page-head">
      {back && (
        <Link className="backlink" to={back}>
          <Icon name="back" size={20} /> {t("back")}
        </Link>
      )}
      <h1>{title}</h1>
      {lead && <p className="lead">{lead}</p>}
    </header>
  );
}

export function Field({
  label, hint, children,
}: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}

export function FarmGate({ children }: { children: (farm: Farm) => ReactNode }) {
  const { farm, loading } = useFarms();
  const { t } = useI18n();
  if (loading) return <Loading />;
  if (!farm) {
    return (
      <div className="card tinted">
        <h2>{t("no_farm_title")}</h2>
        <p className="muted">{t("no_farm_body")}</p>
        <Link className="btn btn-primary" to="/app/farms/new">{t("add_farm")}</Link>
      </div>
    );
  }
  return <>{children(farm)}</>;
}

export function Money({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="muted">—</span>;
  return <span className="mono">₹{value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>;
}
