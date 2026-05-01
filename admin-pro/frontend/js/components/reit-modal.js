/**
 * <reit-modal> — Modal dialog component
 * Usage: <reit-modal title="Title">Content</reit-modal>
 */

class ReitModal extends HTMLElement {
  static get observedAttributes() {
    return ['title'];
  }

  constructor() {
    super();
    this._visible = false;
    this._slotContent = '';
  }

  connectedCallback() {
    // Save slot content before rendering
    this._slotContent = this.innerHTML;
    this._render();
    this._bindEvents();
  }

  _render() {
    this.innerHTML = '';

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay fixed inset-0 bg-black/40 z-[299]';
    overlay.style.display = 'none';

    const panel = document.createElement('div');
    panel.className = 'modal-panel fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-lg bg-white rounded-xl shadow-modal z-[300] overflow-hidden';
    panel.style.display = 'none';

    const header = document.createElement('div');
    header.className = 'flex items-center justify-between px-5 py-4 border-b border-gray-200';

    const titleEl = document.createElement('h3');
    titleEl.className = 'modal-title text-lg font-semibold text-gray-900';
    titleEl.textContent = this.getAttribute('title') || '';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors';
    closeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

    const body = document.createElement('div');
    body.className = 'modal-body px-5 py-4 text-gray-700 text-sm leading-relaxed';
    body.innerHTML = this._slotContent;

    header.appendChild(titleEl);
    header.appendChild(closeBtn);
    panel.appendChild(header);
    panel.appendChild(body);
    this.appendChild(overlay);
    this.appendChild(panel);
  }

  _bindEvents() {
    const overlay = this.querySelector('.modal-overlay');
    const closeBtn = this.querySelector('.modal-close');

    overlay?.addEventListener('click', () => this.close());
    closeBtn?.addEventListener('click', () => this.close());

    this._onKey = (e) => {
      if (e.key === 'Escape') this.close();
    };
  }

  open() {
    this._visible = true;
    const overlay = this.querySelector('.modal-overlay');
    const panel = this.querySelector('.modal-panel');
    if (overlay) overlay.style.display = 'block';
    if (panel) panel.style.display = 'block';
    document.addEventListener('keydown', this._onKey);
    document.body.style.overflow = 'hidden';
  }

  close() {
    this._visible = false;
    const overlay = this.querySelector('.modal-overlay');
    const panel = this.querySelector('.modal-panel');
    if (overlay) overlay.style.display = 'none';
    if (panel) panel.style.display = 'none';
    document.removeEventListener('keydown', this._onKey);
    document.body.style.overflow = '';
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (name === 'title' && oldVal !== newVal) {
      const titleEl = this.querySelector('.modal-title');
      if (titleEl) titleEl.textContent = newVal || '';
    }
  }
}

customElements.define('reit-modal', ReitModal);
