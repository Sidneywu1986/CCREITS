/**
 * <reit-toast> — Toast notification component
 * Types: success, error, warning, info
 */

class ReitToast extends HTMLElement {
  static get observedAttributes() {
    return ['text', 'type'];
  }

  connectedCallback() {
    this._render();
    this._startAutoDismiss();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal !== newVal) this._render();
  }

  _render() {
    const type = this.getAttribute('type') || 'info';
    const text = this.getAttribute('text') || '';

    const colors = {
      success: 'bg-emerald-500',
      error: 'bg-red-500',
      warning: 'bg-amber-500',
      info: 'bg-blue-500'
    };

    this.className = `fixed top-20 left-1/2 -translate-x-1/2 ${colors[type] || colors.info} text-white px-4 py-2 rounded-lg shadow-lg z-[400] text-sm animate-fade-in`;
    this.textContent = text;
  }

  _startAutoDismiss() {
    this._timer = setTimeout(() => this.hide(), 3000);
  }

  hide() {
    if (this._timer) clearTimeout(this._timer);
    this.remove();
  }
}

customElements.define('reit-toast', ReitToast);
