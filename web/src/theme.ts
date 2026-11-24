import { useCallback, useEffect, useSyncExternalStore } from "react";

export type ThemeMode = "light" | "dark" | "system";

const THEME_KEY = "kisan.theme";
const listeners = new Set<() => void>();

function readMode(): ThemeMode {
  try {
    const raw = localStorage.getItem(THEME_KEY);
    return raw === "light" || raw === "dark" || raw === "system" ? raw : "system";
  } catch {
    return "system";
  }
}

let mode: ThemeMode = readMode();
let mediaBound = false;

function apply() {
  const dark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
  document
    .querySelector<HTMLMetaElement>('meta[name="theme-color"]')
    ?.setAttribute("content", dark ? "#0a1220" : "#f4f7fa");
}

function bindMedia() {
  if (mediaBound || typeof window === "undefined") return;
  mediaBound = true;
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (mode === "system") apply();
  });
}

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  return () => listeners.delete(onChange);
}

export function setThemeMode(next: ThemeMode) {
  mode = next;
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* private mode: keep the in-memory choice */
  }
  apply();
  listeners.forEach((listener) => listener());
}

/** Shared theme preference: light → dark → system. */
export function useTheme() {
  const current = useSyncExternalStore(subscribe, () => mode, () => mode);

  useEffect(() => {
    bindMedia();
    apply();
  }, [current]);

  const setMode = useCallback((next: ThemeMode) => setThemeMode(next), []);
  const cycle = useCallback(
    () => setThemeMode(mode === "light" ? "dark" : mode === "dark" ? "system" : "light"),
    [],
  );

  return { mode: current, setMode, cycle };
}
