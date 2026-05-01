/**
 * TDD: <reit-badge> — Status badge for REITs (up/down/sector)
 */

describe('<reit-badge>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined as a custom element', () => {
    expect(customElements.get('reit-badge')).toBeDefined();
  });

  it('should render text content', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', '+2.5%');
    document.body.appendChild(el);
    expect(el.textContent.trim()).toBe('+2.5%');
  });

  it('should apply "up" type styling', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', '+2.5%');
    el.setAttribute('type', 'up');
    document.body.appendChild(el);
    expect(el.classList.contains('reit-badge--up')).toBe(true);
  });

  it('should apply "down" type styling', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', '-1.2%');
    el.setAttribute('type', 'down');
    document.body.appendChild(el);
    expect(el.classList.contains('reit-badge--down')).toBe(true);
  });

  it('should apply "sector-blue" type styling', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', '交通基础设施');
    el.setAttribute('type', 'sector-blue');
    document.body.appendChild(el);
    expect(el.classList.contains('reit-badge--sector-blue')).toBe(true);
  });

  it('should apply default styling when type is unknown', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', 'Unknown');
    el.setAttribute('type', 'foobar');
    document.body.appendChild(el);
    expect(el.classList.contains('reit-badge--up')).toBe(false);
    expect(el.classList.contains('reit-badge--down')).toBe(false);
    expect(el.classList.contains('reit-badge')).toBe(true);
  });

  it('should support size attribute', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', 'Test');
    el.setAttribute('size', 'lg');
    document.body.appendChild(el);
    const span = el.querySelector('span');
    expect(span).not.toBeNull();
    expect(span.classList.contains('text-base')).toBe(true);
  });

  it('should update when text attribute changes', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', 'First');
    document.body.appendChild(el);
    expect(el.textContent.trim()).toBe('First');

    el.setAttribute('text', 'Second');
    expect(el.textContent.trim()).toBe('Second');
  });

  it('should render slot content as text when no text attr', () => {
    document.body.innerHTML = '<reit-badge type="up">+5.0%</reit-badge>';
    const el = document.querySelector('reit-badge');
    expect(el.textContent.trim()).toBe('+5.0%');
    expect(el.classList.contains('reit-badge--up')).toBe(true);
  });

  it('should be safe from XSS (no innerHTML)', () => {
    const el = document.createElement('reit-badge');
    el.setAttribute('text', '<img src=x onerror=alert(1)>');
    el.setAttribute('type', 'up');
    document.body.appendChild(el);
    expect(el.querySelector('img')).toBeNull();
    expect(el.textContent).toContain('<img');
  });
});

require('../reit-badge.js');
