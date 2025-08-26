import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#5F2EEA',
        accent: '#FF5555',
        success: '#2D8C3C',
        error: '#D32F2F',
        background: '#F5F5F5',
        text: '#333333',
      },
      fontFamily: {
        sans: ['Heebo', 'sans-serif'],
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: true,
  },
  rtl: true,
} satisfies Config
