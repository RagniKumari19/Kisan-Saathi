import {
  createContext, useContext, useEffect, useMemo, useState, type ReactNode,
} from "react";
import { api, loadTokens, saveTokens } from "./api";

export type User = {
  id: string;
  phone: string;
  full_name: string | null;
  role: "farmer" | "expert" | "admin";
  language: string;
  primary_farm?: Farm | null;
  farm_count?: number;
};

export type District = {
  id: string;
  name: string;
  state: string;
  slug: string;
  agro_zone: string;
  latitude: number;
  longitude: number;
};

export type Farm = {
  id: string;
  name: string;
  village: string | null;
  district_id: string;
  district: District | null;
  latitude: number;
  longitude: number;
  area_acres: number | null;
  soil_type: string | null;
  irrigation_source: string | null;
  primary_crop_slug: string | null;
  is_primary: boolean;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (phone: string, password: string) => Promise<void>;
  verifyOtp: (requestId: string, code: string) => Promise<void>;
  register: (data: { phone: string; password: string; full_name: string; language: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    if (!loadTokens()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get("/users/me");
      setUser(res.data);
    } catch {
      saveTokens(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshUser();
    const onOut = () => setUser(null);
    window.addEventListener("kisan:signed-out", onOut);
    return () => window.removeEventListener("kisan:signed-out", onOut);
  }, []);

  const value = useMemo<AuthCtx>(() => ({
    user,
    loading,
    async login(phone, password) {
      const res = await api.post("/auth/login", { phone, password });
      saveTokens(res.data.tokens);
      setUser(res.data.user);
    },
    async verifyOtp(requestId, code) {
      const res = await api.post("/auth/otp/verify", { request_id: requestId, code });
      saveTokens(res.data.tokens);
      setUser(res.data.user);
    },
    async register(data) {
      const res = await api.post("/auth/register", data);
      saveTokens(res.data.tokens);
      setUser(res.data.user);
    },
    async logout() {
      const tokens = loadTokens();
      try {
        await api.post("/auth/logout", { refresh_token: tokens?.refresh_token });
      } catch {
        /* the local session is cleared regardless */
      }
      saveTokens(null);
      setUser(null);
    },
    refreshUser,
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

type FarmCtx = {
  farms: Farm[];
  farm: Farm | null;
  loading: boolean;
  selectFarm: (id: string) => void;
  reload: () => Promise<void>;
};

const FarmsContext = createContext<FarmCtx | null>(null);
const SELECTED_KEY = "kisan.farm";

export function FarmsProvider({ children }: { children: ReactNode }) {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selected, setSelected] = useState<string | null>(localStorage.getItem(SELECTED_KEY));
  const [loading, setLoading] = useState(true);

  async function reload() {
    try {
      const res = await api.get("/users/me/farms");
      setFarms(res.data);
      const ids = res.data.map((f: Farm) => f.id);
      if (!selected || !ids.includes(selected)) {
        const primary = res.data.find((f: Farm) => f.is_primary) ?? res.data[0];
        if (primary) {
          setSelected(primary.id);
          localStorage.setItem(SELECTED_KEY, primary.id);
        }
      }
    } catch {
      setFarms([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  const farm = farms.find((f) => f.id === selected) ?? farms[0] ?? null;

  const value = useMemo<FarmCtx>(() => ({
    farms, farm, loading,
    selectFarm(id) {
      setSelected(id);
      localStorage.setItem(SELECTED_KEY, id);
    },
    reload,
  }), [farms, farm, loading, selected]);

  return <FarmsContext.Provider value={value}>{children}</FarmsContext.Provider>;
}

export function useFarms(): FarmCtx {
  const ctx = useContext(FarmsContext);
  if (!ctx) throw new Error("useFarms must be used inside FarmsProvider");
  return ctx;
}
