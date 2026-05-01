/**
 * <safe-text> — XSS-safe text rendering Web Component
 * Renders content via textContent ONLY. Never uses innerHTML.
 */

class SafeText extends HTMLElement {
  static get observedAttributes() {
    return ['text'];
  }

  connectedCallback() {
    this._render();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (name === 'text' && oldVal !== newVal) {
      this._render();
    }
  }

  _render() {
    const textAttr = this.getAttribute('text');
    if (textAttr !== null) {
      // ALWAYS use textContent — never innerHTML
      this.textContent = textAttr;
    } else {
      // Fallback: keep existing slotted text content (already set by parser)
      // No-op: the slot content is already the textContent
    }
  }
}

customElements.define('safe-text', SafeText);
