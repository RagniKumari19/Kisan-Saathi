/// <reference types="vite/client" />
/** Tiny fetch wrapper: bearer auth, one automatic refresh, typed API errors. */
export const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export type Tokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

const TOKEN_KEY = "kisan.tokens";

export function loadTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

export function saveTokens(tokens: Tokens | null) {
  if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  code: string;
  details: { field?: string; issue?: string }[];
  status: number;
  constructor(status: number, code: string, message: string, details: { field?: string; issue?: string }[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const tokens = loadTokens();
  if (!tokens?.refresh_token) return false;
  if (!refreshing) {
    refreshing = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    })
      .then(async (r) => {
        if (!r.ok) return false;
        const body = await r.json();
        saveTokens(body.data.tokens);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        setTimeout(() => (refreshing = null), 0);
      });
  }
  return refreshing;
}

async function request<T = any>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const tokens = loadTokens();
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (tokens?.access_token) headers.Authorization = `Bearer ${tokens.access_token}`;
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the server. Check your connection and try again.");
  }

  if (res.status === 401 && retry && tokens?.refresh_token) {
    const ok = await tryRefresh();
    if (ok) return request<T>(path, options, false);
    saveTokens(null);
    window.dispatchEvent(new Event("kisan:signed-out"));
  }

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "NETWORK_ERROR",
      err?.message ?? "Could not reach the server. Check your connection and try again.",
      err?.details ?? [],
    );
  }
  return body as T;
}

export const api = {
  get: <T = any>(path: string) => request<T>(path),
  post: <T = any>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T = any>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T = any>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T = any>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

export function mediaUrl(key: string | null | undefined): string {
  if (!key) return "";
  if (key.startsWith("http")) return key;
  return key.startsWith("/media") ? key : `/media/${key.replace(/^\/+/, "")}`;
}
