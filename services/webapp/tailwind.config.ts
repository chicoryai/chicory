import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/{**,.client,.server}/**/*.{js,jsx,ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Purple shades
        purple: {
          50: '#c2a5ff',
          100: '#ac93ff',
          200: '#9780ff',
          300: '#816eff',
          400: '#6C5CE7', // primary
          500: '#5649b8',
          600: '#40378a',
          700: '#362e73',
          800: '#2b245c',
          900: '#443a94',
        },
        // Lime shades
        lime: {
          50: '#ffffa5',
          100: '#ffff93',
          200: '#ffff80',
          300: '#ffff6e',
          400: '#D7E75C', // complementary
          500: '#acb849',
          600: '#818a37',
          700: '#6b732e',
          800: '#565c24',
          900: '#2b245d',
        },
        chicoryGreen: {
          50: '#f2fff2',
          100: '#ac93ff',
          200: '#9780ff',
          300: '#816eff',
          400: '#f2fff2', // primary
          500: '#5649b8',
          600: '#40378a',
          700: '#362e73',
          800: '#005b00',
          900: '#a6ffa6',
        },
        whiteLime: {
          50: '#fffff2',
          100: '#fefff2',
        },
        whitePurple: {
          50: '#f2f2ff',
          100: '#d9d9ff',
          200: '#a6a6ff',
        },
        // Text colors
        text: {
          light: '#111827', // dark text for light mode
          dark: '#F5F7F9',  // light text for dark mode
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
        'textReveal': 'textReveal 1s ease-out forwards',
        'ellipsis': 'ellipsis 1.5s infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-up-message': 'slideUpMessage 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in': 'slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'glow-sweep': 'glowSweep 3s linear infinite',
        'border-beam': 'borderBeam 4s linear infinite',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '0.9', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.1)' },
        },
        textReveal: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        ellipsis: {
          '0%': { opacity: '0.3' },
          '50%': { opacity: '1' },
          '100%': { opacity: '0.3' },
        },
        glowSweep: {
          '0%': {
            opacity: '0',
            transform: 'rotate(0deg)'
          },
          '10%': {
            opacity: '1'
          },
          '80%': {
            opacity: '1'
          },
          '100%': {
            opacity: '0',
            transform: 'rotate(360deg)'
          },
        },
        slideUp: {
          '0%': {
            transform: 'translateY(var(--tw-translate-y-start, 100px)) scale(0.95)',
            opacity: '0.7'
          },
          '100%': {
            transform: 'translateY(0) scale(1)',
            opacity: '1'
          },
        },
        slideUpMessage: {
          '0%': {
            transform: 'translateY(var(--slide-distance, 0px))',
            opacity: '0.8'
          },
          '100%': {
            transform: 'translateY(0)',
            opacity: '1'
          },
        },
        slideIn: {
          '0%': {
            transform: 'translateY(10px)',
            opacity: '0'
          },
          '100%': {
            transform: 'translateY(0)',
            opacity: '1'
          },
        },
        borderBeam: {
          '0%': {
            transform: 'rotate(0deg)',
          },
          '100%': {
            transform: 'rotate(360deg)',
          },
        }
      },
      boxShadow: {
        'node': '0 0 15px rgba(255,255,255,0.2)',
        'node-selected': '0 0 20px rgba(132,204,22,0.4)',
      },
      fontFamily: {
        // Display font for headings and high-impact elements
        display: [
          "Outfit",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        // UI font for interface elements
        ui: [
          "Sora",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        // Body font for reading and content
        body: [
          "'Plus Jakarta Sans'",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        // Fallback system font stack
        sans: [
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
          "Apple Color Emoji",
          "Segoe UI Emoji",
          "Segoe UI Symbol",
          "Noto Color Emoji",
        ],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    // Custom base styles for consistent styling
    function ({ addBase }: { addBase: (css: Record<string, Record<string, string>>) => void }) {
      addBase({
        // These styles are kept only if actually needed by custom markdown components
        // TODO: Remove once MarkdownComponents.tsx is refactored to not need global styles
      });
    }
  ],
} satisfies Config;
