/**
 * <reit-table> — Data table with sort, pagination, empty state
 * Usage: <reit-table columns='[...]' data='[...]' page-size='10'></reit-table>
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

  class ReitTable extends HTMLElement {
    static get observedAttributes() {
      return ['columns', 'data', 'page-size'];
    }

    constructor() {
      super();
      this._columns = [];
      this._data = [];
      this._pageSize = 10;
      this._currentPage = 1;
      this._sortKey = null;
      this._sortDir = 'asc';
    }

    connectedCallback() {
      this._parseAttrs();
      this._render();
    }

    attributeChangedCallback(name, oldVal, newVal) {
      if (oldVal !== newVal) {
        this._parseAttrs();
        this._render();
      }
    }

    _parseAttrs() {
      try {
        this._columns = JSON.parse(this.getAttribute('columns') || '[]');
        this._data = JSON.parse(this.getAttribute('data') || '[]');
      } catch (e) {
        this._columns = [];
        this._data = [];
      }
      this._pageSize = parseInt(this.getAttribute('page-size') || '10', 10);
    }

    _sortedData() {
      let data = [...this._data];
      if (this._sortKey) {
        data.sort((a, b) => {
          const av = a[this._sortKey];
          const bv = b[this._sortKey];
          if (av == null) return 1;
          if (bv == null) return -1;
          if (typeof av === 'number' && typeof bv === 'number') {
            return this._sortDir === 'asc' ? av - bv : bv - av;
          }
          const cmp = String(av).localeCompare(String(bv));
          return this._sortDir === 'asc' ? cmp : -cmp;
        });
      }
      return data;
    }

    _pagedData() {
      const sorted = this._sortedData();
      const start = (this._currentPage - 1) * this._pageSize;
      return sorted.slice(start, start + this._pageSize);
    }

    _totalPages() {
      return Math.max(1, Math.ceil(this._data.length / this._pageSize));
    }

    _render() {
      this.innerHTML = '';

      if (!this._data.length) {
        this.innerHTML = `
          <div class="reit-empty">
            <div class="reit-empty__title">暂无数据</div>
            <div class="reit-empty__body">当前条件下没有找到相关数据，请尝试调整筛选条件。</div>
          </div>
        `;
        return;
      }

      const table = document.createElement('table');
      table.className = 'reit-table';

      // Header
      const thead = document.createElement('thead');
      const headerRow = document.createElement('tr');
      this._columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.label || col.key;
        if (col.sortable) {
          th.style.cursor = 'pointer';
          th.addEventListener('click', () => this._toggleSort(col.key));
          if (this._sortKey === col.key) {
            th.textContent += this._sortDir === 'asc' ? ' ▲' : ' ▼';
          }
        }
        headerRow.appendChild(th);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);

      // Body
      const tbody = document.createElement('tbody');
      const paged = this._pagedData();
      paged.forEach(row => {
        const tr = document.createElement('tr');
        this._columns.forEach(col => {
          const td = document.createElement('td');
          const val = row[col.key];
          if (col.format === 'badge') {
            const badge = document.createElement('reit-badge');
            badge.setAttribute('text', String(val));
            badge.setAttribute('type', val >= 0 ? 'up' : 'down');
            td.appendChild(badge);
          } else {
            td.textContent = val != null ? String(val) : '';
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);

      this.appendChild(table);

      // Pagination
      if (this._totalPages() > 1) {
        this._renderPagination();
      }
    }

    _renderPagination() {
      const total = this._totalPages();
      const nav = document.createElement('div');
      nav.className = 'flex items-center justify-between mt-4 px-2';
      nav.innerHTML = `
        <span class="text-xs text-gray-500">第 ${this._currentPage}/${total} 页 · 共 ${this._data.length} 条</span>
        <div class="flex gap-1">
          <button class="px-2 py-1 text-xs rounded border border-gray-200 hover:bg-gray-50 ${this._currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}">上一页</button>
          <button class="px-2 py-1 text-xs rounded border border-gray-200 hover:bg-gray-50 ${this._currentPage === total ? 'opacity-50 cursor-not-allowed' : ''}">下一页</button>
        </div>
      `;
      const [prev, next] = nav.querySelectorAll('button');
      if (this._currentPage > 1) {
        prev.addEventListener('click', () => { this._currentPage--; this._render(); });
      }
      if (this._currentPage < total) {
        next.addEventListener('click', () => { this._currentPage++; this._render(); });
      }
      this.appendChild(nav);
    }

    _toggleSort(key) {
      if (this._sortKey === key) {
        this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this._sortKey = key;
        this._sortDir = 'asc';
      }
      this._render();
    }
  }

  customElements.define('reit-table', ReitTable);
})();
