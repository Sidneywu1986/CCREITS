/**
 * <safe-html> — DOMPurify-sanitized HTML rendering
 * ONLY use for trusted sources. Prefer <safe-text> for user content.
 */

(function() {
  // Inline DOMPurify-style sanitization (lightweight fallback)
  function _sanitize(html) {
    if (!html) return '';
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    // Remove dangerous tags
    const dangerous = tmp.querySelectorAll('script,iframe,object,embed,form,input,textarea');
    dangerous.forEach(el => el.remove());
    // Remove event handlers
    const all = tmp.querySelectorAll('*');
    all.forEach(el => {
      [...el.attributes].forEach(attr => {
        if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
      });
    });
    return tmp.innerHTML;
  }

  class SafeHtml extends HTMLElement {
    static get observedAttributes() {
      return ['html'];
    }

    connectedCallback() {
      this._render();
    }

    attributeChangedCallback(name, oldVal, newVal) {
      if (name === 'html' && oldVal !== newVal) {
        this._render();
      }
    }

    _render() {
      const raw = this.getAttribute('html') || '';
      this.innerHTML = _sanitize(raw);
    }
  }

  customElements.define('safe-html', SafeHtml);
})();
