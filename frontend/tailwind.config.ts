import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./store/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        fg: "rgb(var(--fg) / <alpha-value>)",
        panel: "rgb(var(--panel) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        accent2: "rgb(var(--accent2) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
      },
      boxShadow: {
        glow: "0 20px 80px rgba(10, 16, 30, 0.18)",
      },
      backgroundImage: {
        "ledger-grid":
          "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.18), transparent 24%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.14), transparent 18%), linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01))",
      },
    },
  },
  plugins: [],
};

export default config;

