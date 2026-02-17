import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slateInk: "#0F172A",
        mist: "#E2E8F0",
        signal: "#0EA5E9",
        ember: "#F97316",
      },
    },
  },
  plugins: [],
};

export default config;
