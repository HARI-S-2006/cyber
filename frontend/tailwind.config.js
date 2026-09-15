/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#000000',
          bgSecondary: '#0a0a0a',
          panel: '#0d1117',
          panelBorder: '#1f2937',
          primary: '#39FF14',
          primaryGlow: '#00FF41',
          secondary: '#00FFFF',
          secondaryGlow: '#00FFFF',
          danger: '#FF0033',
          dangerGlow: '#FF0033',
          warning: '#FFCC00',
          info: '#00D4FF',
          text: '#E4E4E7',
          textDim: '#71717A',
          scanline: 'rgba(57, 255, 20, 0.03)',
        },
      },
      fontFamily: {
        mono: ['"Fira Code"', '"JetBrains Mono"', '"Courier New"', 'monospace'],
        sans: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      animation: {
        'scanline': 'scanline 8s linear infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'blink': 'blink 1s step-end infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-down': 'slide-down 0.3s ease-out',
        'glitch': 'glitch 0.5s ease-in-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'spin-slow': 'spin 20s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 5px #39FF14, 0 0 10px #39FF14, 0 0 15px #39FF14' },
          '50%': { boxShadow: '0 0 10px #39FF14, 0 0 20px #39FF14, 0 0 30px #39FF14' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        glitch: {
          '0%, 100%': { transform: 'translate(0)' },
          '20%': { transform: 'translate(-2px, 2px)' },
          '40%': { transform: 'translate(2px, -2px)' },
          '60%': { transform: 'translate(-2px, 2px)' },
          '80%': { transform: 'translate(2px, -2px)' },
        },
      },
      boxShadow: {
        'glow-primary': '0 0 5px #39FF14, 0 0 10px #39FF14, 0 0 15px #39FF14',
        'glow-secondary': '0 0 5px #00FFFF, 0 0 10px #00FFFF, 0 0 15px #00FFFF',
        'glow-danger': '0 0 5px #FF0033, 0 0 10px #FF0033, 0 0 15px #FF0033',
        'glow-warning': '0 0 5px #FFCC00, 0 0 10px #FFCC00, 0 0 15px #FFCC00',
        'panel': '0 0 0 1px #1f2937, 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(57, 255, 20, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(57, 255, 20, 0.03) 1px, transparent 1px)',
        'radial-glow': 'radial-gradient(ellipse at center, rgba(57, 255, 20, 0.1) 0%, transparent 70%)',
      },
    },
  },
  plugins: [],
}