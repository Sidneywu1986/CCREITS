/**
 * TDD: <reit-card> — REIT fund info card
 */

describe('<reit-card>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined', () => {
    expect(customElements.get('reit-card')).toBeDefined();
  });

  it('should render fund name and code', () => {
    const el = document.createElement('reit-card');
    el.setAttribute('name', '华夏中国交建REIT');
    el.setAttribute('code', '508018');
    document.body.appendChild(el);
    expect(el.textContent).toContain('华夏中国交建REIT');
    expect(el.textContent).toContain('508018');
  });

  it('should render change percentage with up styling', () => {
    const el = document.createElement('reit-card');
    el.setAttribute('name', 'Test');
    el.setAttribute('code', '000001');
    el.setAttribute('change', '+2.5');
    document.body.appendChild(el);
    expect(el.textContent).toContain('+2.5%');
    expect(el.querySelector('.reit-badge--up')).not.toBeNull();
  });

  it('should render change percentage with down styling', () => {
    const el = document.createElement('reit-card');
    el.setAttribute('name', 'Test');
    el.setAttribute('code', '000001');
    el.setAttribute('change', '-1.2');
    document.body.appendChild(el);
    expect(el.textContent).toContain('-1.2%');
    expect(el.querySelector('.reit-badge--down')).not.toBeNull();
  });

  it('should render sector badge', () => {
    const el = document.createElement('reit-card');
    el.setAttribute('name', 'Test');
    el.setAttribute('code', '000001');
    el.setAttribute('sector', 'transport');
    document.body.appendChild(el);
    expect(el.textContent).toContain('交通基础设施');
  });

  it('should be safe from XSS in fund name', () => {
    const el = document.createElement('reit-card');
    el.setAttribute('name', '<script>window.CARD_XSS=1</script>');
    el.setAttribute('code', '000001');
    document.body.appendChild(el);
    expect(window.CARD_XSS).toBeUndefined();
    expect(el.querySelector('script')).toBeNull();
  });
});

require('../reit-card.js');
