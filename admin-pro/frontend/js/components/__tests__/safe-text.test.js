/**
 * TDD: <safe-text> — XSS-safe text rendering
 * Rule: innerHTML is NEVER used. Only textContent.
 */

// Must import implementation AFTER defining tests (TDD: test first)
// We'll require it at the bottom after the describe block

describe('<safe-text>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined as a custom element', () => {
    expect(customElements.get('safe-text')).toBeDefined();
  });

  it('should render text content via attribute', () => {
    const el = document.createElement('safe-text');
    el.setAttribute('text', 'Hello REITs');
    document.body.appendChild(el);
    expect(el.textContent.trim()).toBe('Hello REITs');
  });

  it('should NOT execute script tags (XSS prevention)', () => {
    const el = document.createElement('safe-text');
    el.setAttribute('text', '<script>window.XSS_TEST=1</script>');
    document.body.appendChild(el);
    expect(window.XSS_TEST).toBeUndefined();
    expect(el.textContent.trim()).toBe('<script>window.XSS_TEST=1</script>');
  });

  it('should escape HTML entities when rendering', () => {
    const el = document.createElement('safe-text');
    el.setAttribute('text', '<b>Bold</b>');
    document.body.appendChild(el);
    const html = el.innerHTML;
    expect(html).not.toContain('<b>');
    expect(html).toContain('&lt;b&gt;');
  });

  it('should update text when attribute changes', () => {
    const el = document.createElement('safe-text');
    el.setAttribute('text', 'First');
    document.body.appendChild(el);
    expect(el.textContent.trim()).toBe('First');

    el.setAttribute('text', 'Second');
    expect(el.textContent.trim()).toBe('Second');
  });

  it('should render slot content as fallback when no text attr', () => {
    document.body.innerHTML = '<safe-text>Fallback Text</safe-text>';
    const el = document.querySelector('safe-text');
    expect(el.textContent.trim()).toBe('Fallback Text');
  });

  it('should NOT have innerHTML set to untrusted data', () => {
    const el = document.createElement('safe-text');
    el.setAttribute('text', '<img src=x onerror=alert(1)>');
    document.body.appendChild(el);
    expect(el.innerHTML).not.toContain('<img');
    expect(el.querySelector('img')).toBeNull();
  });
});

require('../safe-text.js');
