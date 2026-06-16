/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Space Grotesk', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        ink: {
          DEFAULT: '#ffffff',
          50:  '#0a0a0f',
          100: '#0f0f18',
          200: '#16161f',
          300: '#1e1e2e',
          400: '#2a2a3e',
          500: '#3d3d5c',
          600: '#6b6b8a',
          700: '#9595ae',
          800: '#c2c2d0',
          900: '#e8e8f0',
        },
        brand: {
          DEFAULT: '#3b82f6',
          50:  '#0d1829',
          100: '#1a2e4a',
          200: '#1e3a5f',
          300: '#1d4ed8',
          400: '#2563eb',
          500: '#3b82f6',
          600: '#60a5fa',
          700: '#93c5fd',
          800: '#bfdbfe',
          900: '#dbeafe',
        },
        accent: { DEFAULT: '#f59e0b', light: '#1c1500' },
      },
      animation: {
        'fade-in':  'fadeIn 0.3s ease forwards',
        'slide-up': 'slideUp 0.3s ease forwards',
        'slide-in': 'slideIn 0.25s ease forwards',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' },                                to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideIn: { from: { opacity: '0', transform: 'translateX(-6px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
      },
    },
  },
  plugins: [],
}
