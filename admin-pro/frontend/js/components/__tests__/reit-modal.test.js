/**
 * TDD: <reit-modal> — Modal dialog
 */

describe('<reit-modal>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined', () => {
    expect(customElements.get('reit-modal')).toBeDefined();
  });

  it('should be hidden by default', () => {
    const el = document.createElement('reit-modal');
    el.setAttribute('title', 'Test Modal');
    document.body.appendChild(el);
    expect(el.querySelector('.modal-panel').style.display).toBe('none');
  });

  it('should show when open() is called', () => {
    const el = document.createElement('reit-modal');
    el.setAttribute('title', 'Test');
    document.body.appendChild(el);
    el.open();
    expect(el.style.display).not.toBe('none');
    expect(el.querySelector('.modal-title').textContent).toBe('Test');
  });

  it('should hide when close() is called', () => {
    const el = document.createElement('reit-modal');
    el.setAttribute('title', 'Test');
    document.body.appendChild(el);
    el.open();
    el.close();
    expect(el.querySelector('.modal-panel').style.display).toBe('none');
  });

  it('should render slot content', () => {
    document.body.innerHTML = '<reit-modal title="Info">Modal Body Content</reit-modal>';
    const el = document.querySelector('reit-modal');
    expect(el.querySelector('.modal-body').textContent).toContain('Modal Body Content');
  });

  it('should escape title to prevent XSS', () => {
    const el = document.createElement('reit-modal');
    el.setAttribute('title', '<img src=x onerror=alert(1)>');
    document.body.appendChild(el);
    el.open();
    expect(el.querySelector('img')).toBeNull();
  });
});

require('../reit-modal.js');
