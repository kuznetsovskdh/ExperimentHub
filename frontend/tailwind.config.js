/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Все цвета читаются из CSS-переменных в index.css — смена палитры
        // не требует правок в компонентах.
        ground: "var(--ground)",
        surface: "var(--surface)",
        raised: "var(--raised)",
        line: "var(--line)",
        "line-soft": "var(--line-soft)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        // Два полюса эксперимента. Цвет здесь кодирует роль, а не настроение.
        control: "var(--control)",
        treatment: "var(--treatment)",
        good: "var(--good)",
        warn: "var(--warn)",
        bad: "var(--bad)",
      },
      fontFamily: {
        display: ["Unbounded", "system-ui", "sans-serif"],
        sans: ["'Golos Text'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.045em",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "seam-grow": {
          from: { transform: "scaleY(0)" },
          to: { transform: "scaleY(1)" },
        },
      },
      animation: {
        "fade-up": "fade-up .7s cubic-bezier(.16,1,.3,1) both",
        "seam-grow": "seam-grow 1.2s cubic-bezier(.16,1,.3,1) both",
      },
    },
  },
  plugins: [],
};
