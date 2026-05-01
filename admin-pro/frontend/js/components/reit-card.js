/**
 * <reit-card> — REIT fund information card
 * Attributes: name, code, change, sector, nav
 */

(function() {
  function _escapeHtml(text) {
    if (text == null) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  const _SECTOR_CONFIG = (typeof SECTOR_CONFIG !== 'undefined' && SECTOR_CONFIG) || {
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

  class ReitCard extends HTMLElement {
    static get observedAttributes() {
      return ['name', 'code', 'change', 'sector', 'nav'];
    }

    connectedCallback() {
      this._render();
    }

    attributeChangedCallback(name, oldVal, newVal) {
      if (oldVal !== newVal) this._render();
    }

    _render() {
      const name = this.getAttribute('name') || '';
      const code = this.getAttribute('code') || '';
      const change = parseFloat(this.getAttribute('change') || '0');
      const sectorKey = this.getAttribute('sector') || 'other';
      const nav = this.getAttribute('nav') || '';

      const sector = _SECTOR_CONFIG[sectorKey] || _SECTOR_CONFIG['other'];

      const isUp = change >= 0;
      const changeStr = (change >= 0 ? '+' : '') + change + '%';
      const badgeColor = isUp ? 'text-red-600' : 'text-green-600';
      const badgeClass = isUp ? 'reit-badge--up' : 'reit-badge--down';

      this.className = 'reit-card p-4 cursor-pointer';
      this.innerHTML = `
        <div class="flex items-start justify-between mb-2">
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-gray-900 text-sm text-truncate">${_escapeHtml(name)}</div>
            <div class="flex items-center gap-2 mt-1">
              <span class="mono text-xs text-gray-500">${_escapeHtml(code)}</span>
              <span class="reit-badge reit-badge--sector-blue text-xs">${_escapeHtml(sector.name)}</span>
            </div>
          </div>
          <div class="text-right ml-3">
            <span class="reit-badge ${badgeClass} font-bold text-lg mono">${changeStr}</span>
            ${nav ? `<div class="text-xs text-gray-400 mt-0.5">净值 ${_escapeHtml(nav)}</div>` : ''}
          </div>
        </div>
      `;

      this.addEventListener('click', () => {
        if (code) window.location.href = `./fund-detail.html?code=${encodeURIComponent(code)}`;
      });
    }
  }

  customElements.define('reit-card', ReitCard);
})();
