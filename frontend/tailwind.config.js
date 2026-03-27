/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {
      colors: {
        night: "#0B0F1A",
        aurora: "#1BCFB4",
        ember: "#FF7A59",
        sky: "#6EA8FF",
        mist: "#A5B4FC"
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'DM Sans'", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
