/**
 * TDD: <reit-table> — Data table
 */

describe('<reit-table>', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('should be defined', () => {
    expect(customElements.get('reit-table')).toBeDefined();
  });

  it('should render columns and data', () => {
    const el = document.createElement('reit-table');
    el.setAttribute('columns', JSON.stringify([{ key: 'name', label: '名称' }, { key: 'code', label: '代码' }]));
    el.setAttribute('data', JSON.stringify([{ name: '华夏REIT', code: '508018' }, { name: '中金REIT', code: '508001' }]));
    document.body.appendChild(el);
    expect(el.querySelectorAll('th').length).toBe(2);
    expect(el.textContent).toContain('华夏REIT');
    expect(el.textContent).toContain('508001');
  });

  it('should show empty state when no data', () => {
    const el = document.createElement('reit-table');
    el.setAttribute('columns', JSON.stringify([{ key: 'name', label: '名称' }]));
    el.setAttribute('data', '[]');
    document.body.appendChild(el);
    expect(el.textContent).toContain('暂无数据');
  });

  it('should sort when sortable column header clicked', () => {
    const el = document.createElement('reit-table');
    el.setAttribute('columns', JSON.stringify([{ key: 'name', label: '名称', sortable: true }]));
    el.setAttribute('data', JSON.stringify([{ name: 'Zebra' }, { name: 'Apple' }]));
    document.body.appendChild(el);
    const th = el.querySelector('th');
    th.click();
    const rows = el.querySelectorAll('tbody tr');
    expect(rows[0].textContent).toContain('Apple');
  });

  it('should paginate data', () => {
    const el = document.createElement('reit-table');
    el.setAttribute('columns', JSON.stringify([{ key: 'name', label: '名称' }]));
    el.setAttribute('data', JSON.stringify([{ name: 'A' }, { name: 'B' }, { name: 'C' }]));
    el.setAttribute('page-size', '2');
    document.body.appendChild(el);
    expect(el.querySelectorAll('tbody tr').length).toBe(2);
    expect(el.textContent).toContain('第 1/2 页');
  });
});

require('../reit-table.js');
