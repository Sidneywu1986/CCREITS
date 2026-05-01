/**
 * Shared utilities for Web Components
 */

function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// SECTOR_CONFIG fallback for standalone component usage
const SECTOR_CONFIG = (typeof window !== 'undefined' && window.SECTOR_CONFIG) || {
  'transport': { name: '交通基础设施', icon: '🛣' },
  'logistics': { name: '仓储物流', icon: '📦' },
  'industrial': { name: '产业园区', icon: '🏭' },
  'consumer': { name: '消费基础设施', icon: '🛒' },
  'energy': { name: '能源基础设施', icon: '⚡' },
  'housing': { name: '租赁住房', icon: '🏠' },
  'eco': { name: '生态环保', icon: '🌿' },
  'water': { name: '水利设施', icon: '💧' },
  'municipal': { name: '市政设施', icon: '🏛' },
  'datacenter': { name: '数据中心', icon: '🖥' },
  'commercial': { name: '商业办公', icon: '🏢' },
  'elderly': { name: '养老设施', icon: '👴' },
  'other': { name: '其他', icon: '📌' }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { escapeHtml, SECTOR_CONFIG };
}
