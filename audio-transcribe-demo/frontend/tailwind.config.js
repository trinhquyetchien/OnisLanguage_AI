/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 24px 60px rgba(15, 23, 42, 0.12)",
      },
      colors: {
        ink: {
          50: "#f7f8fb",
        },
      },
      backgroundImage: {
        halo:
          "radial-gradient(circle at top left, rgba(56,189,248,0.22), transparent 34%), radial-gradient(circle at bottom right, rgba(244,114,182,0.18), transparent 28%)",
      },
    },
  },
  plugins: [],
};
