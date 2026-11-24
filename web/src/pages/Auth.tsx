import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../session";
import { useI18n } from "../i18n";
import { ErrorNote } from "../ui";

function AuthShell({ children, title, sub }: { children: React.ReactNode; title: string; sub: string }) {
  const { t, lang, setLang } = useI18n();
  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <img src="/logo.svg" alt="" width={58} height={58} />
        <h1>{t("app_name")}</h1>
        <p>{t("tagline")}</p>
        <div className="lang-switch" role="group" aria-label={t("language")} style={{ marginTop: "0.9rem" }}>
          <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>{t("english")}</button>
          <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>{t("hindi")}</button>
        </div>
      </div>
      <div className="auth-card">
        <div className="inner">
          <h2>{title}</h2>
          <p className="muted small" style={{ marginBottom: "1rem" }}>{sub}</p>
          {children}
        </div>
      </div>
    </div>
  );
}

type Sent = { requestId: string; resendAt: number; phone: string };

function useCountdown(until: number | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return until ? Math.max(0, Math.ceil((until - now) / 1000)) : 0;
}

function OtpCodeForm({
  sent, busy, error, onVerify, onResend, onReset,
}: {
  sent: Sent;
  busy: boolean;
  error: unknown;
  onVerify: (code: string) => void;
  onResend: () => void;
  onReset: () => void;
}) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const remaining = useCountdown(sent.resendAt);

  return (
    <>
      {error !== null && <ErrorNote error={error} />}
      <p className="small muted" style={{ marginTop: 0 }}>
Verification code sent to your registered mobile number ending in ****{sent.phone.slice(-4)}.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onVerify(code.trim());
        }}
      >
        <div className="field">
          <label htmlFor="otp">{t("enter_code")}</label>
          <input
            id="otp"
            className="input mono"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]*"
            maxLength={6}
            placeholder="••••••"
            style={{ letterSpacing: "0.3em", fontSize: "1.3rem", textAlign: "center" }}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            autoFocus
            required
            minLength={4}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy || code.length < 4}>
          {busy ? t("verifying") : t("verify_code")}
        </button>
      </form>

      <div className="row between" style={{ marginTop: "0.9rem" }}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={onResend}
          disabled={busy || remaining > 0}
        >
          {remaining > 0 ? `${t("resend_in")} ${remaining}s` : t("resend_code")}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onReset} disabled={busy}>
          {t("change_number")}
        </button>
      </div>
    </>
  );
}

export function LoginPage() {
  const { login, verifyOtp } = useAuth();
  const { t } = useI18n();
  const [mode, setMode] = useState<"otp" | "password">("otp");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function sendCode(target = phone) {
    setError(null);
    setBusy(true);
    try {
      const res = await api.post("/auth/otp/request", { phone: target.trim(), purpose: "login" });
      const d = res.data;
      setSent({
        requestId: d.request_id,
        resendAt: Date.now() + (d.resend_after ?? 60) * 1000,
        phone: d.phone ?? target,
      });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function verify(code: string) {
    if (!sent) return;
    setError(null);
    setBusy(true);
    try {
      await verifyOtp(sent.requestId, code);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function submitPassword(p = phone, pw = password) {
    setError(null);
    setBusy(true);
    try {
      await login(p.trim(), pw);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("sign_in")} sub={t("otp_phone_hint")}>
      {mode === "otp" ? (
        sent ? (
          <OtpCodeForm
            sent={sent}
            busy={busy}
            error={error}
            onVerify={verify}
            onResend={() => void sendCode(sent.phone)}
            onReset={() => { setSent(null); setError(null); }}
          />
        ) : (
          <>
            {error !== null && <ErrorNote error={error} />}
            <form onSubmit={(e) => { e.preventDefault(); void sendCode(); }}>
              <div className="field">
                <label htmlFor="phone">{t("phone")}</label>
                <input id="phone" className="input" type="tel" inputMode="tel" autoComplete="tel"
                  placeholder="+919876543210" value={phone} onChange={(e) => setPhone(e.target.value)}
                  required minLength={10} />
                <span className="hint">{t("otp_phone_hint")}</span>
              </div>
              <button className="btn btn-primary btn-block" disabled={busy} type="submit">
                {busy ? t("sending_code") : t("send_code")}
              </button>
            </form>
            <button type="button" className="btn btn-ghost btn-block" style={{ marginTop: "0.4rem" }}
              onClick={() => { setMode("password"); setError(null); }}>
              {t("use_password")}
            </button>
          </>
        )
      ) : (
        <>
          {error !== null && <ErrorNote error={error} />}
          <form onSubmit={(e) => { e.preventDefault(); void submitPassword(); }}>
            <div className="field">
              <label htmlFor="phone">{t("phone")}</label>
              <input id="phone" className="input" type="tel" inputMode="tel" autoComplete="tel"
                placeholder="+919876543210" value={phone} onChange={(e) => setPhone(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="password">{t("password")}</label>
              <input id="password" className="input" type="password" autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button className="btn btn-primary btn-block" disabled={busy} type="submit">
              {busy ? t("loading") : t("sign_in")}
            </button>
          </form>
          <button type="button" className="btn btn-ghost btn-block" style={{ marginTop: "0.4rem" }}
            onClick={() => { setMode("otp"); setError(null); }}>
            {t("use_otp")}
          </button>

        </>
      )}

      <p className="small muted" style={{ marginTop: "0.9rem" }}>
        {t("new_here")} <Link to="/register">{t("create_account")}</Link>
      </p>
    </AuthShell>
  );
}

export function RegisterPage() {
  const { verifyOtp } = useAuth();
  const { t, lang } = useI18n();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function sendCode(target = phone, name = fullName) {
    setError(null);
    setBusy(true);
    try {
      const res = await api.post("/auth/otp/request", {
        phone: target.trim(),
        purpose: "signup",
        full_name: name.trim(),
        language: lang,
      });
      const d = res.data;
      setSent({
        requestId: d.request_id,
        resendAt: Date.now() + (d.resend_after ?? 60) * 1000,
        phone: d.phone ?? target,
      });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function verify(code: string) {
    if (!sent) return;
    setError(null);
    setBusy(true);
    try {
      await verifyOtp(sent.requestId, code);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("create_account")} sub={t("otp_phone_hint")}>
      {sent ? (
        <OtpCodeForm
          sent={sent}
          busy={busy}
          error={error}
          onVerify={verify}
          onResend={() => void sendCode(sent.phone, fullName)}
          onReset={() => { setSent(null); setError(null); }}
        />
      ) : (
        <>
          {error !== null && <ErrorNote error={error} />}
          <form onSubmit={(e) => { e.preventDefault(); void sendCode(); }}>
            <div className="field">
              <label htmlFor="name">{t("full_name")}</label>
              <input id="name" className="input" autoComplete="name" value={fullName}
                onChange={(e) => setFullName(e.target.value)} required minLength={2} />
            </div>
            <div className="field">
              <label htmlFor="phone">{t("phone")}</label>
              <input id="phone" className="input" type="tel" inputMode="tel" autoComplete="tel"
                placeholder="+919876543210" value={phone} onChange={(e) => setPhone(e.target.value)}
                required minLength={10} />
              <span className="hint">{t("otp_phone_hint")}</span>
            </div>
            <button className="btn btn-primary btn-block" disabled={busy} type="submit">
              {busy ? t("sending_code") : t("send_code")}
            </button>
          </form>
        </>
      )}
      <p className="small muted" style={{ marginTop: "0.9rem" }}>
        {t("sign_in")}? <Link to="/login">{t("sign_in")}</Link>
      </p>
    </AuthShell>
  );
}
