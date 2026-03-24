/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./theme/templates/**/*.html",
    "./productionApp/templates/**/*.html",
    "./templates/**/*.html"
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('daisyui'),
  ],

  daisyui: {
    themes: ["light"], // Força o tema claro para não apanhares sustos com o dark mode do sistema
  }
}