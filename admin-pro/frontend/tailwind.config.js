/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./js/*.js"],
  theme: {
    extend: {
      // ── Color Tokens (UI-SPEC v2) ──
      colors: {
        // Semantic base
        dominant:   '#f8fafc',   // 60% — page background
        secondary:  '#ffffff',   // 30% — cards, panels
        surface:    '#f1f5f9',   // sidebar, table headers
        accent:     '#0ea5e9',   // 10% — primary actions, links
        'accent-hover': '#0284c7',
        success:    '#10b981',
        warning:    '#f59e0b',
        destructive:'#ef4444',
        'text-primary':   '#0f172a',
        'text-secondary': '#64748b',
        border:     '#e2e8f0',

        // REITs semantic (涨跌幅 / 板块)
        'reit-up':    '#ef4444',   // A股红涨
        'reit-down':  '#16a34a',   // A股绿跌
        'reit-blue':  '#0ea5e9',   // 基础设施/交通
        'reit-purple':'#8b5cf6',   // 产业园/仓储
        'reit-orange':'#f97316',   // 能源/环保
      },

      // ── Font Family ──
      fontFamily: {
        sans: [
          '"PingFang SC"',
          '"Microsoft YaHei"',
          '"Hiragino Sans GB"',
          '"Noto Sans SC"',
          'system-ui',
          '-apple-system',
          'sans-serif'
        ],
        mono: [
          '"JetBrains Mono"',
          '"SF Mono"',
          '"Cascadia Code"',
          'Consolas',
          'monospace'
        ],
      },

      // ── Font Size (UI-SPEC typography) ──
      fontSize: {
        'body':   ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'label':  ['12px', { lineHeight: '1.4', fontWeight: '500' }],
        'heading':['18px', { lineHeight: '1.3', fontWeight: '600' }],
        'display':['24px', { lineHeight: '1.2', fontWeight: '700' }],
        'mono-sm':['13px', { lineHeight: '1.5', fontWeight: '400' }],
      },

      // ── Spacing (4px grid) ──
      spacing: {
        'xs':  '4px',
        'sm':  '8px',
        'md':  '16px',
        'lg':  '24px',
        'xl':  '32px',
        '2xl': '48px',
        '3xl': '64px',
        // Layout constants
        'sidebar': '240px',
        'header':  '56px',
        'footer':  '32px',
        'row':     '40px',
      },

      // ── Border Radius ──
      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },

      // ── Shadows ──
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)',
        'dropdown': '0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04)',
        'modal': '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)',
      },

      // ── Max Width ──
      maxWidth: {
        'content': '1440px',
        'prose': '65ch',
      },

      // ── Z-Index Scale ──
      zIndex: {
        'dropdown': 100,
        'sticky':   200,
        'modal':    300,
        'toast':    400,
      },
    },
  },
  plugins: [],
}
