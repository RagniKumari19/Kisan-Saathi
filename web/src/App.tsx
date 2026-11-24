import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import { AuthProvider, FarmsProvider, useAuth, useFarms } from "./session";
import { I18nProvider, useI18n } from "./i18n";
import { useTheme } from "./theme";
import { Icon, Loading, type IconName } from "./ui";
import { LoginPage, RegisterPage } from "./pages/Auth";
import { Dashboard } from "./pages/Dashboard";
import { PlanHub, SoilPage, WeatherPage, RecommendPage, CropInfoPage } from "./pages/Plan";
import { CalendarHub, NewPlanPage, PlanDetailPage } from "./pages/Calendar";
import { ProtectHub, CapturePage, HistoryPage, DetectionPage, LibraryPage, LibraryItemPage, ExpertPage } from "./pages/Protect";
import { SellHub, PricesPage, ComparePage, TrendsPage, MspPage } from "./pages/Sell";
import { ProfilePage, FarmFormPage, AdminPage } from "./pages/Profile";

type NavItem = { to: string; label: string; icon: IconName; end?: boolean };

const PRIMARY_NAV: NavItem[] = [
  { to: "/app", label: "home", icon: "home", end: true },
  { to: "/app/plan", label: "plan", icon: "leaf" },
  { to: "/app/protect", label: "protect", icon: "shield" },
  { to: "/app/sell", label: "sell", icon: "rupee" },
];

const ACCOUNT_NAV: NavItem[] = [{ to: "/app/profile", label: "profile", icon: "user" }];

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function FarmSelector() {
  const { farms, farm, selectFarm } = useFarms();
  const { t } = useI18n();
  if (farms.length < 2) return null;
  return (
    <label className="row" style={{ gap: "0.55rem", flex: 1 }}>
      <span className="farm-label">{t("choose_farm")}</span>
      <select
        className="select"
        style={{ minHeight: 44, padding: "0.25rem 0.5rem", width: "auto", flex: 1, maxWidth: 280 }}
        value={farm?.id ?? ""}
        onChange={(e) => selectFarm(e.target.value)}
      >
        {farms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
      </select>
    </label>
  );
}

function staffLinks(user: ReturnType<typeof useAuth>["user"]): NavItem[] {
  if (!user) return [];
  if (user.role === "admin") {
    return [
      { to: "/app/expert", label: "expert_queue", icon: "shield" },
      { to: "/app/admin", label: "admin", icon: "chart" },
    ];
  }
  if (user.role === "expert") return [{ to: "/app/expert", label: "expert_queue", icon: "shield" }];
  return [];
}

function ThemeButton() {
  const { mode, cycle } = useTheme();
  const { t } = useI18n();
  const label =
    mode === "dark" ? t("theme_dark") : mode === "light" ? t("theme_light") : t("theme_system");
  return (
    <button
      className="icon-only"
      onClick={cycle}
      title={`${t("appearance")}: ${label}`}
      aria-label={`${t("appearance")}: ${label}`}
    >
      <Icon name={mode === "dark" ? "sun" : "moon"} size={19} />
    </button>
  );
}

function MoreSheet({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const { mode, setMode } = useTheme();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="sheet-overlay" onClick={onClose} role="presentation">
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={t("menu")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-grip" />
        <div className="sheet-grid">
          {[...ACCOUNT_NAV, ...staffLinks(user)].map((item) => (
            <NavLink key={item.to} to={item.to} className="sheet-item" onClick={onClose}>
              <Icon name={item.icon} size={22} />
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
        </div>

        <div className="sheet-row">
          <span className="small muted">{t("language")}</span>
          <div className="seg" role="group" aria-label={t("language")}>
            <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>{t("english")}</button>
            <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>{t("hindi")}</button>
          </div>
        </div>

        <div className="sheet-row">
          <span className="small muted">{t("appearance")}</span>
          <div className="seg" role="group" aria-label={t("appearance")}>
            {(["light", "dark", "system"] as const).map((m) => (
              <button key={m} aria-pressed={mode === m} onClick={() => setMode(m)}>
                {t(`theme_${m}`)}
              </button>
            ))}
          </div>
        </div>

        <button className="btn btn-secondary btn-block" onClick={() => { onClose(); void logout(); }}>
          {t("sign_out")}
        </button>
      </div>
    </div>
  );
}

function AppLayout() {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const staff = staffLinks(user);
  const initial = (user?.full_name ?? user?.phone ?? "?").charAt(0).toUpperCase();

  useEffect(() => {
    window.scrollTo({ top: 0 });
    setMoreOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>

      <aside className="sidebar">
        <NavLink to="/app" className="side-brand">
          <img src="/logo.svg" alt="" width={38} height={38} />
          <span>
            <span className="brand-name">{t("app_name")}</span>
            <span className="brand-sub">{t("tagline")}</span>
          </span>
        </NavLink>

        <nav className="side-nav" aria-label={t("menu")}>
          <span className="nav-label">{t("menu")}</span>
          {PRIMARY_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <Icon name={item.icon} size={19} />
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
          <span className="nav-label">{t("account")}</span>
          {[...ACCOUNT_NAV, ...staff].map((item) => (
            <NavLink key={item.to} to={item.to}>
              <Icon name={item.icon} size={19} />
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          {user && (
            <div className="side-user">
              <span className="avatar" aria-hidden="true">{initial}</span>
              <span className="who">
                <strong>{user.full_name ?? user.phone}</strong>
                <span>{t(`role_${user.role}`)}</span>
              </span>
            </div>
          )}
          <div className="side-actions">
            <div className="lang-switch" role="group" aria-label={t("language")}>
              <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>{t("english")}</button>
              <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>{t("hindi")}</button>
            </div>
            <ThemeButton />
            <button className="icon-only" onClick={() => { void logout(); }} aria-label={t("sign_out")} title={t("sign_out")}>
              <Icon name="logout" size={19} />
            </button>
          </div>
        </div>
      </aside>

      <div className="main-col">
        <header className="mobile-bar">
          <NavLink to="/app" className="brand">
            <img src="/logo.svg" alt="" width={34} height={34} />
            <span>
              <span className="brand-name">{t("app_name")}</span>
              <span className="brand-sub">{t("tagline")}</span>
            </span>
          </NavLink>
          <span className="topbar-spacer" />
          <ThemeButton />
          <NavLink to="/app/profile" aria-label={t("profile")} style={{ display: "inline-flex" }}>
            <span className="avatar" aria-hidden="true">{initial}</span>
          </NavLink>
        </header>

        <main className="container" id="main">
          <div className="farm-bar"><FarmSelector /></div>
          <Outlet />
        </main>

        <nav className="tabbar" aria-label={t("menu")}>
          {PRIMARY_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <Icon name={item.icon} size={23} />
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
          <button
            onClick={() => setMoreOpen(true)}
            aria-expanded={moreOpen}
            aria-haspopup="dialog"
            className={moreOpen ? "active" : undefined}
          >
            <Icon name="more" size={23} />
            <span>{t("more")}</span>
          </button>
        </nav>

        {moreOpen && <MoreSheet onClose={() => setMoreOpen(false)} />}
      </div>
    </div>
  );
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (user) return <Navigate to="/app" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/app" replace />} />
            <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
            <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
            <Route path="/app" element={<Protected><FarmsProvider><AppLayout /></FarmsProvider></Protected>}>
              <Route index element={<Dashboard />} />
              <Route path="plan" element={<PlanHub />} />
              <Route path="plan/soil" element={<SoilPage />} />
              <Route path="plan/weather" element={<WeatherPage />} />
              <Route path="plan/recommend" element={<RecommendPage />} />
              <Route path="plan/calendar" element={<CalendarHub />} />
              <Route path="plan/calendar/new" element={<NewPlanPage />} />
              <Route path="plan/calendar/:id" element={<PlanDetailPage />} />
              <Route path="plan/crops" element={<CropInfoPage />} />
              <Route path="plan/crops/:slug" element={<CropInfoPage />} />
              <Route path="protect" element={<ProtectHub />} />
              <Route path="protect/capture" element={<CapturePage />} />
              <Route path="protect/history" element={<HistoryPage />} />
              <Route path="protect/library" element={<LibraryPage />} />
              <Route path="protect/library/:slug" element={<LibraryItemPage />} />
              <Route path="protect/:id" element={<DetectionPage />} />
              <Route path="sell" element={<SellHub />} />
              <Route path="sell/prices" element={<PricesPage />} />
              <Route path="sell/compare" element={<ComparePage />} />
              <Route path="sell/trends" element={<TrendsPage />} />
              <Route path="sell/msp" element={<MspPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="farms/new" element={<FarmFormPage />} />
              <Route path="farms/:id" element={<FarmFormPage />} />
              <Route path="expert" element={<ExpertPage />} />
              <Route path="admin" element={<AdminPage />} />
              <Route path="*" element={<Navigate to="/app" replace />} />
            </Route>
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}
