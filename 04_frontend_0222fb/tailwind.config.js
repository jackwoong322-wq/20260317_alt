/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 프로젝트 디자인 토큰에 맞춘 커스텀 색상
        'chart-bg':     '#0d1117',
        'chart-panel':  '#161b27',
        'chart-border': 'rgba(255,255,255,0.08)',
        'accent':       '#bfa023',
        'buy':          '#5cb37f',
        'hold':         '#a0a3af',
        'sell':         '#d17d68',
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
