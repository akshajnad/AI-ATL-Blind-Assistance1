/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Light theme - modern and clean
        'kora-bg': '#f8f9fa',
        'kora-surface': '#ffffff',
        'kora-panel': '#f0f4f8',
        'kora-border': '#e1e8ed',

        // Accent colors
        'kora-primary': '#00d9a3',      // Teal/mint green
        'kora-secondary': '#00b8ff',    // Soft blue
        'kora-accent': '#7c3aed',       // Purple
        'kora-lime': '#84cc16',         // Lime green

        // Status colors
        'kora-success': '#10b981',
        'kora-warning': '#f59e0b',
        'kora-danger': '#ef4444',
        'kora-info': '#3b82f6',

        // Text colors
        'kora-text': '#1a202c',
        'kora-text-secondary': '#64748b',
        'kora-text-muted': '#94a3b8',
      },
      backgroundImage: {
        'kora-gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'kora-gradient-light': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'kora-gradient-ar': 'linear-gradient(180deg, rgba(0, 217, 163, 0.05) 0%, rgba(0, 184, 255, 0.05) 100%)',
        'kora-mesh': 'radial-gradient(at 40% 20%, rgba(0, 217, 163, 0.1) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(124, 58, 237, 0.1) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(0, 184, 255, 0.1) 0px, transparent 50%)',
      },
      boxShadow: {
        'kora-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'kora-md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'kora-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'kora-xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'kora-glow': '0 0 20px rgba(0, 217, 163, 0.4)',
        'kora-glow-blue': '0 0 20px rgba(0, 184, 255, 0.4)',
        'kora-inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.4s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
      },
      keyframes: {
        'pulse-ring': {
          '0%, 100%': {
            transform: 'scale(1)',
            opacity: '1',
          },
          '50%': {
            transform: 'scale(1.1)',
            opacity: '0.5',
          },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

