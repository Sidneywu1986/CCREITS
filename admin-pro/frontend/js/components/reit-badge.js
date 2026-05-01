/**
 * <reit-badge> — Status badge for REITs
 * Types: up, down, sector-blue, sector-purple, sector-orange
 */

class ReitBadge extends HTMLElement {
  static get observedAttributes() {
    return ['text', 'type', 'size'];
  }

  constructor() {
    super();
    this._span = document.createElement('span');
  }

  connectedCallback() {
    if (!this.contains(this._span)) {
      this.appendChild(this._span);
    }
    this._render();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal !== newVal) {
      this._render();
    }
  }

  _render() {
    const type = this.getAttribute('type') || 'default';
    const text = this.getAttribute('text');
    const size = this.getAttribute('size') || 'md';

    // Reset classes
    this.className = 'reit-badge';
    this._span.className = '';

    // Apply type class
    const typeClass = `reit-badge--${type}`;
    if (['up', 'down', 'sector-blue', 'sector-purple', 'sector-orange'].includes(type)) {
      this.classList.add(typeClass);
    }

    // Apply size
    const sizeMap = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' };
    this._span.classList.add(sizeMap[size] || 'text-sm');

    // Render text safely
    if (text !== null) {
      this._span.textContent = text;
    } else {
      // Keep slot content (already in DOM), just wrap it
      // Move any existing text nodes into span
      this.childNodes.forEach(node => {
        if (node !== this._span) {
          this._span.appendChild(node);
        }
      });
    }
  }
}

customElements.define('reit-badge', ReitBadge);
