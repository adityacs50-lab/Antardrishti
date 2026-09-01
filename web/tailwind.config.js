/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces — deep, low-chroma slate. Industrial control room, not consumer app.
        bg: "hsl(var(--bg))",
        surface: {
          DEFAULT: "hsl(var(--surface-1))",
          raised: "hsl(var(--surface-2))",
          sunken: "hsl(var(--surface-0))",
        },
        line: { DEFAULT: "hsl(var(--border))", strong: "hsl(var(--border-strong))" },
        ink: {
          DEFAULT: "hsl(var(--text-1))",
          muted: "hsl(var(--text-2))",
          faint: "hsl(var(--text-3))",
        },
        // Status — reserved. Never reused as a series colour.
        status: {
          good: "#0ca30c",
          warning: "#fab219",
          serious: "#ec835a",
          critical: "#d03b3b",
        },
        // Categorical series — validated against surface #131A22 (dark).
        series: {
          1: "#3987e5", // blue
          2: "#d95926", // orange
          3: "#199e70", // aqua
          4: "#c98500", // yellow
        },
        // Evidence-span highlight hues — validated all-pairs.
        cue: { energy: "#3987e5", control: "#d95926", context: "#199e70" },
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
      borderRadius: { lg: "0.5rem", md: "0.375rem", sm: "0.25rem" },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%,100%": { opacity: "0.35" },
          "50%": { opacity: "0.9" },
        },
      },
      animation: {
        "fade-in": "fade-in 140ms ease-out",
        "slide-up": "slide-up 160ms ease-out",
        "pulse-ring": "pulse-ring 2.2s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
