import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        panel: "var(--panel)",
        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        rule: "var(--rule)",
        "rule-soft": "var(--rule-soft)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        up: "var(--up)",
        down: "var(--down)",
        caution: "var(--caution)",
        "up-wash": "var(--up-wash)",
        "down-wash": "var(--down-wash)",
        "caution-wash": "var(--caution-wash)",
        "panel-ink-text": "var(--panel-ink-text)",
        "panel-ink-soft": "var(--panel-ink-soft)",
        "panel-ink-rule": "var(--panel-ink-rule)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "SF Pro Text",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.75rem", { lineHeight: "1.4" }],
      },
      maxWidth: {
        measure: "40rem",
      },
      boxShadow: {
        glass: "var(--glass-shadow)",
        "glass-sm": "var(--glass-shadow-sm)",
      },
      borderRadius: {
        glass: "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;
