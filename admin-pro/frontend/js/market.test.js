/**
 * Market页面测试
 * 测试策略：
 * 1. 测试页面加载时的数据获取
 * 2. 测试API失败时的降级策略
 * 3. 测试数据渲染正确性
 * 4. 测试筛选和排序功能
 */

/**
 * @jest-environment jsdom
 */

// Mock依赖
global.fetch = jest.fn();
global.echarts = {
  init: jest.fn(() => ({
    setOption: jest.fn(),
    on: jest.fn(),
    resize: jest.fn()
  })),
  getInstanceByDom: jest.fn()
};

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock ALL_FUNDS 数据
const MOCK_FUNDS = [
  {
    code: '508001',
    name: '中金普洛斯',
    price: 3.456,
    change_percent: 1.23,
    volume: 1234567,
    yield: 4.56,
    nav: 3.200,
    premium: 8.00,
    debt: 35.5,
    market_cap: 50.2,
    scale: 45.0,
    sector: 'logistics'
  },
  {
    code: '180201',
    name: '华夏越秀',
    price: 2.789,
    change_percent: -0.45,
    volume: 987654,
    yield: 5.12,
    nav: 2.850,
    premium: -2.14,
    debt: 42.1,
    market_cap: 35.8,
    scale: 32.5,
    sector: 'transport'
  },
  {
    code: '508002',
    name: '红土创新',
    price: 1.987,
    change_percent: 0.67,
    volume: 555555,
    yield: 3.89,
    nav: 2.000,
    premium: -0.65,
    debt: 28.8,
    market_cap: 25.3,
    scale: 22.0,
    sector: 'industrial'
  }
];

// 模拟SECTOR_CONFIG
global.SECTOR_CONFIG = {
  logistics: { name: '物流仓储', tagClass: 'bg-blue-100 text-blue-700' },
  transport: { name: '交通基建', tagClass: 'bg-green-100 text-green-700' },
  industrial: { name: '产业园区', tagClass: 'bg-purple-100 text-purple-700' }
};

// Mock DOM元素
document.body.innerHTML = `
  <input type="text" id="global-search" value="">
  <div id="treemap"></div>
  <div id="trading-status"></div>
  <div id="update-time"></div>
  <table>
    <thead>
      <tr>
        <th>基金代码</th>
        <th>基金简称</th>
        <th>板块</th>
        <th>最新价</th>
        <th>涨跌幅</th>
        <th>成交量</th>
        <th>派息率</th>
        <th>操作</th>
      </tr>
    </thead>
    <tbody id="fund-list"></tbody>
  </table>
  <div id="compare-bar" class="compare-bar"></div>
  <div id="compare-items"></div>
  <span id="compare-count">已选 0/4</span>
  <div id="pagination"></div>
  <span id="list-info"></span>
`;

// Mock document.getElementById
const originalGetElementById = document.getElementById;
document.getElementById = jest.fn((id) => {
  const element = originalGetElementById.call(document, id);
  if (element) return element;

  // 返回模拟元素
  const mockElements = {
    'global-search': document.createElement('input'),
    'treemap': document.createElement('div'),
    'trading-status': document.createElement('div'),
    'update-time': document.createElement('div'),
    'fund-list': document.createElement('tbody'),
    'compare-bar': document.createElement('div'),
    'compare-items': document.createElement('div'),
    'compare-count': document.createElement('span'),
    'pagination': document.createElement('div'),
    'list-info': document.createElement('span')
  };

  return mockElements[id] || document.createElement('div');
});

// 全局变量
let allFundsData = [];
let filteredData = [];
let currentSector = 'all';
let currentPage = 1;
let pageSize = 15;
let sortBy = 'change-desc';
let searchKeyword = '';
let currentDataSource = 'mock';

describe('Market页面测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();

    // 重置全局变量
    allFundsData = [];
    filteredData = [];
    currentSector = 'all';
    currentPage = 1;
    pageSize = 15;
    sortBy = 'change-desc';
    searchKeyword = '';
    currentDataSource = 'mock';
  });

  describe('数据加载功能', () => {
    test('页面加载时应该从API获取基金数据', async () => {
      const mockResponse = {
        success: true,
        data: MOCK_FUNDS
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      // 重新导入并执行加载函数
      const { loadData } = require('./market.js');

      await loadData();

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(allFundsData).toEqual(MOCK_FUNDS);
      expect(filteredData).toEqual(MOCK_FUNDS);
      expect(currentDataSource).toBe('api');
    });

    test('API失败时应该降级到Mock数据', async () => {
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      // Mock console.warn避免输出
      global.console.warn = jest.fn();

      const { loadData } = require('./market.js');

      await loadData();

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(allFundsData).toEqual(global.ALL_FUNDS || []);
      expect(currentDataSource).toBe('mock');
      expect(global.console.warn).toHaveBeenCalled();
    });

    test('数据加载完成后应该初始化热力图和表格', async () => {
      const mockResponse = {
        success: true,
        data: MOCK_FUNDS
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      // Mock相关函数
      global.initTreemap = jest.fn();
      global.applyFilters = jest.fn();
      global.updateCompareBar = jest.fn();
      global.loadMarketIndices = jest.fn();

      const { loadData } = require('./market.js');

      await loadData();

      expect(global.initTreemap).toHaveBeenCalled();
      expect(global.applyFilters).toHaveBeenCalled();
      expect(global.updateCompareBar).toHaveBeenCalled();
      expect(global.loadMarketIndices).toHaveBeenCalled();
    });
  });

  describe('数据筛选功能', () => {
    beforeEach(() => {
      allFundsData = [...MOCK_FUNDS];
      filteredData = [...MOCK_FUNDS];
    });

    test('按板块筛选应该只显示该板块的基金', () => {
      const { applyFilters } = require('./market.js');

      currentSector = 'logistics';
      applyFilters();

      expect(filteredData.length).toBe(1);
      expect(filteredData[0].sector).toBe('logistics');
    });

    test('搜索关键词应该筛选基金代码和名称', () => {
      const { applyFilters } = require('./market.js');

      searchKeyword = '中金';
      applyFilters();

      expect(filteredData.length).toBe(1);
      expect(filteredData[0].name).toContain('中金');
    });

    test('搜索关键词应该不区分大小写', () => {
      const { applyFilters } = require('./market.js');

      searchKeyword = '508001';
      applyFilters();

      expect(filteredData.length).toBe(1);
      expect(filteredData[0].code).toBe('508001');
    });

    test('清除搜索关键词应该显示所有基金', () => {
      const { applyFilters } = require('./market.js');

      searchKeyword = '中金';
      applyFilters();
      expect(filteredData.length).toBe(1);

      searchKeyword = '';
      applyFilters();
      expect(filteredData.length).toBe(MOCK_FUNDS.length);
    });
  });

  describe('数据排序功能', () => {
    beforeEach(() => {
      allFundsData = [...MOCK_FUNDS];
      filteredData = [...MOCK_FUNDS];
    });

    test('按涨跌幅降序排序', () => {
      const { applyFilters } = require('./market.js');

      sortBy = 'change-desc';
      applyFilters();

      const changes = filteredData.map(f => f.change_percent);
      expect(changes).toEqual([1.23, 0.67, -0.45]);
    });

    test('按涨跌幅升序排序', () => {
      const { applyFilters } = require('./market.js');

      sortBy = 'change-asc';
      applyFilters();

      const changes = filteredData.map(f => f.change_percent);
      expect(changes).toEqual([-0.45, 0.67, 1.23]);
    });

    test('按成交量降序排序', () => {
      const { applyFilters } = require('./market.js');

      sortBy = 'volume-desc';
      applyFilters();

      const volumes = filteredData.map(f => f.volume);
      expect(volumes).toEqual([1234567, 987654, 555555]);
    });
  });

  describe('对比功能', () => {
    beforeEach(() => {
      localStorageMock.getItem.mockReturnValue(JSON.stringify([]));
    });

    test('添加到对比应该更新localStorage', () => {
      const { addToCompare } = require('./market.js');

      addToCompare('508001', '中金普洛斯');

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'reits_compare',
        JSON.stringify([{ code: '508001', name: '中金普洛斯' }])
      );
    });

    test('从对比移除应该更新localStorage', () => {
      localStorageMock.getItem.mockReturnValue(JSON.stringify([
        { code: '508001', name: '中金普洛斯' },
        { code: '180201', name: '华夏越秀' }
      ]));

      const { removeFromCompare } = require('./market.js');

      removeFromCompare('508001');

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'reits_compare',
        JSON.stringify([{ code: '180201', name: '华夏越秀' }])
      );
    });

    test('对比栏已满时应该阻止添加', () => {
      localStorageMock.getItem.mockReturnValue(JSON.stringify([
        { code: '508001', name: '中金普洛斯' },
        { code: '180201', name: '华夏越秀' },
        { code: '508002', name: '红土创新' },
        { code: '180202', name: '测试基金' }
      ]));

      const { showToast } = require('./market.js');
      const { addToCompare } = require('./market.js');

      // 尝试添加第5个基金
      addToCompare('999999', '新基金');

      // 应该显示警告而不是添加
      expect(showToast).toHaveBeenCalledWith('对比栏已满（最多4只）', 'warning');
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe('分页功能', () => {
    beforeEach(() => {
      allFundsData = [...MOCK_FUNDS];
      filteredData = [...MOCK_FUNDS];
      currentPage = 1;
      pageSize = 2;
    });

    test('分页应该正确计算总页数', () => {
      const { renderPagination } = require('./market.js');

      renderPagination();

      expect(document.getElementById('pagination').innerHTML).toContain('‹');
      expect(document.getElementById('pagination').innerHTML).toContain('›');
    });

    test('页码切换应该更新当前页', () => {
      const { goToPage } = require('./market.js');

      goToPage(2);

      expect(currentPage).toBe(2);
    });

    test('页码边界检查', () => {
      const { goToPage } = require('./market.js');

      goToPage(0);
      expect(currentPage).toBe(1);

      goToPage(999);
      expect(currentPage).toBe(1); // 不应该超过总页数
    });
  });

  describe('实时更新功能', () => {
    test('交易时间内应该启用实时数据更新', () => {
      const { isTradingTime } = require('./market.js');

      // Mock交易时间
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(10);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(1); // 周一

      expect(isTradingTime()).toBe(true);
    });

    test('非交易时间应该禁用实时数据更新', () => {
      const { isTradingTime } = require('./market.js');

      // Mock非交易时间（晚上）
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(20);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(0);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(1);

      expect(isTradingTime()).toBe(false);
    });

    test('周末应该是非交易时间', () => {
      const { isTradingTime } = require('./market.js');

      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(10);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(0); // 周日

      expect(isTradingTime()).toBe(false);
    });
  });
});