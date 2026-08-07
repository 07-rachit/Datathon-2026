/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0B0F17",
        panel: "#111826",
        panel2: "#161F2E",
        line: "#232E42",
        ink: "#DCE3EE",
        muted: "#7C8AA3",
        amber: "#F0A202",
        teal: "#3FD6C1",
        crit: "#E23D5B",
      },
      fontFamily: {
        display: ["'Barlow Condensed'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
