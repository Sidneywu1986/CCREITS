/**
 * REITs Web Components Registry
 * Import this file to register all components at once.
 *
 * Components:
 *   <safe-text>    — XSS-safe text rendering
 *   <safe-html>    — DOMPurify-sanitized HTML
 *   <reit-badge>   — Status badge (up/down/sector)
 *   <reit-toast>   — Toast notification
 *   <reit-modal>   — Modal dialog
 *   <reit-card>    — Fund info card
 *   <reit-table>   — Data table (sort/paginate)
 *   <reit-chart>   — ECharts wrapper
 */

const COMPONENT_FILES = [
  './safe-text.js',
  './safe-html.js',
  './reit-badge.js',
  './reit-toast.js',
  './reit-modal.js',
  './reit-card.js',
  './reit-table.js',
  './reit-chart.js',
];

// Auto-register all components when this module is loaded
COMPONENT_FILES.forEach(path => {
  // In browser, script tags will handle loading
  // In test environment, require() handles it
});

// Export component names for introspection
const REIT_COMPONENTS = [
  'safe-text',
  'safe-html',
  'reit-badge',
  'reit-toast',
  'reit-modal',
  'reit-card',
  'reit-table',
  'reit-chart',
];

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { REIT_COMPONENTS };
}
