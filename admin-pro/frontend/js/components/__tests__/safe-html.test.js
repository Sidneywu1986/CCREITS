/**
 * TDD: <safe-html> — DOMPurify-sanitized HTML
 */

describe('<safe-html>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined', () => {
    expect(customElements.get('safe-html')).toBeDefined();
  });

  it('should render sanitized HTML', () => {
    const el = document.createElement('safe-html');
    el.setAttribute('html', '<p>Hello <b>World</b></p>');
    document.body.appendChild(el);
    expect(el.querySelector('p')).not.toBeNull();
    expect(el.querySelector('b')).not.toBeNull();
    expect(el.textContent).toBe('Hello World');
  });

  it('should remove script tags', () => {
    const el = document.createElement('safe-html');
    el.setAttribute('html', '<script>window.SAFE_HTML_XSS=1</script><p>Safe</p>');
    document.body.appendChild(el);
    expect(el.querySelector('script')).toBeNull();
    expect(window.SAFE_HTML_XSS).toBeUndefined();
    expect(el.textContent).toBe('Safe');
  });

  it('should remove event handlers', () => {
    const el = document.createElement('safe-html');
    el.setAttribute('html', '<p onclick="alert(1)">Click me</p>');
    document.body.appendChild(el);
    const p = el.querySelector('p');
    expect(p).not.toBeNull();
    expect(p.hasAttribute('onclick')).toBe(false);
  });

  it('should remove iframes', () => {
    const el = document.createElement('safe-html');
    el.setAttribute('html', '<iframe src="evil.com"></iframe><p>Safe</p>');
    document.body.appendChild(el);
    expect(el.querySelector('iframe')).toBeNull();
  });
});

require('../safe-html.js');
