/**
 * TDD: <reit-toast> — Toast notification
 */

describe('<reit-toast>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should be defined', () => {
    expect(customElements.get('reit-toast')).toBeDefined();
  });

  it('should show message via text attribute', () => {
    const el = document.createElement('reit-toast');
    el.setAttribute('text', '操作成功');
    el.setAttribute('type', 'success');
    document.body.appendChild(el);
    expect(el.textContent).toContain('操作成功');
    expect(el.classList.contains('bg-green-500') || el.classList.contains('bg-emerald-500')).toBe(true);
  });

  it('should auto-dismiss after 3 seconds', () => {
    const el = document.createElement('reit-toast');
    el.setAttribute('text', 'Test');
    document.body.appendChild(el);
    expect(document.body.contains(el)).toBe(true);
    jest.advanceTimersByTime(3000);
    expect(document.body.contains(el)).toBe(false);
  });

  it('should support manual hide()', () => {
    const el = document.createElement('reit-toast');
    el.setAttribute('text', 'Test');
    document.body.appendChild(el);
    el.hide();
    expect(document.body.contains(el)).toBe(false);
  });

  it('should not execute scripts in message', () => {
    const el = document.createElement('reit-toast');
    el.setAttribute('text', '<script>window.TOAST_XSS=1</script>');
    document.body.appendChild(el);
    expect(window.TOAST_XSS).toBeUndefined();
  });
});

require('../reit-toast.js');
