export type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "earningspulse-theme";

const themeListeners = new Set<() => void>();

function resolveTheme(stored: string | null): Theme | null {
  if (stored === "light" || stored === "dark") return stored;
  return null;
}

function systemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function hasStoredTheme(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) != null;
  } catch {
    return false;
  }
}

export function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    return resolveTheme(localStorage.getItem(THEME_STORAGE_KEY)) ?? systemTheme();
  } catch {
    return systemTheme();
  }
}

export function getThemeSnapshot(): Theme {
  return readStoredTheme();
}

export function getThemeServerSnapshot(): Theme {
  return "light";
}

export function subscribeTheme(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  themeListeners.add(onStoreChange);

  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onMedia = () => {
    if (hasStoredTheme()) return;
    onStoreChange();
  };
  const onStorage = (event: StorageEvent) => {
    if (event.key === THEME_STORAGE_KEY || event.key === null) {
      onStoreChange();
    }
  };

  media.addEventListener("change", onMedia);
  window.addEventListener("storage", onStorage);

  return () => {
    themeListeners.delete(onStoreChange);
    media.removeEventListener("change", onMedia);
    window.removeEventListener("storage", onStorage);
  };
}

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
}

export function persistTheme(theme: Theme): void {
  applyTheme(theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // ignore storage failures
  }
  themeListeners.forEach((listener) => listener());
}

export const themeInitScript = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var s=localStorage.getItem(k);var t=s==="light"||s==="dark"?s:(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");document.documentElement.classList.toggle("dark",t==="dark");document.documentElement.style.colorScheme=t;}catch(e){}})();`;
