import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./contexts/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fci: {
          primary: "#1E7D32",
          dark: "#145A24",
          light: "#EAF7EC",
          accent: "#43A047",
          ink: "#1B1B1B",
          mist: "#F7FAF8",
          line: "#ECECEC",
          amber: "#C47B2E",
          steel: "#45515F"
        },
      },
      boxShadow: {
        soft: "0 18px 60px rgba(20, 90, 36, 0.12)",
        crisp: "0 1px 0 rgba(27, 27, 27, 0.08), 0 16px 40px rgba(27, 27, 27, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
