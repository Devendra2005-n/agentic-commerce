/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#F6F5F1",
        ink: "#1E1D1A",
        "ink-faint": "#6B6A64",
        "ledger-blue": "#2B4570",
        "ledger-amber": "#A6791C", // Final desaturated goldenrod
        "ledger-red": "#9C3D34",
        stitch: "#D8D5CB",
        highlight: "#EDE7D8"
      },
      fontFamily: {
        display: ['Fraunces', 'serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace']
      },
      boxShadow: {
        'ledger-modal': '0 2px 12px rgba(30, 29, 26, 0.08)',
      }
    },
  },
  plugins: [],
}
