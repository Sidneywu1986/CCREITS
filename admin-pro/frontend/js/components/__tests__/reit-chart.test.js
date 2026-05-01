/**
 * TDD: <reit-chart> — ECharts wrapper
 */

describe('<reit-chart>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined', () => {
    expect(customElements.get('reit-chart')).toBeDefined();
  });

  it('should show fallback when echarts is not loaded', () => {
    const el = document.createElement('reit-chart');
    el.setAttribute('option', JSON.stringify({ title: { text: 'Test' } }));
    document.body.appendChild(el);
    expect(el.textContent).toContain('ECharts not loaded');
  });
});

require('../reit-chart.js');
