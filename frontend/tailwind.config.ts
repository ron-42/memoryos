import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#090b10",
        panel: "#10131a",
        muted: "#94a3b8",
        accent: "#3b82f6"
      }
    }
  },
  plugins: []
};

export default config;
