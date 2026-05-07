import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Inter", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        accent: {
          ok: "#22c55e",
          warn: "#eab308",
          bad: "#ef4444",
          info: "#3b82f6",
        },
      },
      animation: {
        "pulse-slow": "pulse 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [typography],
};
