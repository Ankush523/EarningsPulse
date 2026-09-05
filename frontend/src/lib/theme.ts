export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "earningspulse-theme";

export function resolveTheme(stored: string | null): Theme | null {
  if (stored === "light" || stored === "dark") return stored;
  return null;
}

export function systemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    return resolveTheme(localStorage.getItem(THEME_STORAGE_KEY)) ?? systemTheme();
  } catch {
    return systemTheme();
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
}

export const themeInitScript = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var s=localStorage.getItem(k);var t=s==="light"||s==="dark"?s:(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");document.documentElement.classList.toggle("dark",t==="dark");document.documentElement.style.colorScheme=t;}catch(e){}})();`;
