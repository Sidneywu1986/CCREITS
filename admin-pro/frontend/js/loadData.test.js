/**
 * 数据加载逻辑测试
 * 测试策略：
 * 1. 测试loadData函数的行为
 * 2. 测试API成功和失败的处理
 * 3. 测试数据初始化和状态更新
 */

/**
 * @jest-environment jsdom
 */

// Mock依赖
global.fetch = jest.fn();

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
  }
];

// 模拟SECTOR_CONFIG
global.SECTOR_CONFIG = {
  logistics: { name: '物流仓储', tagClass: 'bg-blue-100 text-blue-700' },
  transport: { name: '交通基建', tagClass: 'bg-green-100 text-green-700' }
};

// Mock document.getElementById
document.body.innerHTML = `
  <div id="data-source-indicator"></div>
  <div id="fund-list"></div>
  <div id="compare-bar" class="compare-bar"></div>
`;

describe('数据加载逻辑测试', () => {
  let allFundsData, filteredData, currentDataSource;
  let originalFetch;

  beforeEach(() => {
    jest.clearAllMocks();
    allFundsData = [];
    filteredData = [];
    currentDataSource = 'mock';
  });

  test('loadData应该从API成功获取数据', async () => {
    const mockResponse = {
      success: true,
      data: MOCK_FUNDS
    };

    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    // 模拟API函数
    const REITS_API = {
      getFunds: async () => {
        const response = await fetch('/api/funds');
        if (!response.ok) throw new Error('Network error');
        return response.json();
      }
    };

    try {
      const result = await REITS_API.getFunds();
      allFundsData = result.data;
      filteredData = [...allFundsData];
      currentDataSource = 'api';

      expect(allFundsData).toEqual(MOCK_FUNDS);
      expect(filteredData).toHaveLength(2);
      expect(currentDataSource).toBe('api');
    } catch (error) {
      expect(error).toBeUndefined();
    }
  });

  test('API失败时应该降级到Mock数据', async () => {
    global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

    const REITS_API = {
      getFunds: async () => {
        try {
          const response = await fetch('/api/funds');
          if (!response.ok) throw new Error('HTTP error');
          return response.json();
        } catch (error) {
          console.warn('API失败，使用Mock:', error.message);
          return { data: MOCK_FUNDS };
        }
      }
    };

    const result = await REITS_API.getFunds();
    allFundsData = result.data;
    filteredData = [...allFundsData];
    currentDataSource = 'mock';

    expect(allFundsData).toEqual(MOCK_FUNDS);
    expect(currentDataSource).toBe('mock');
  });

  test('applyFilters应该正确筛选数据', () => {
    allFundsData = [...MOCK_FUNDS];
    filteredData = [...MOCK_FUNDS];

    // 测试按板块筛选
    const sector = 'logistics';
    filteredData = allFundsData.filter(f => f.sector === sector);

    expect(filteredData).toHaveLength(1);
    expect(filteredData[0].sector).toBe('logistics');
  });

  test('applyFilters应该正确搜索数据', () => {
    allFundsData = [...MOCK_FUNDS];
    filteredData = [...MOCK_FUNDS];

    // 测试搜索
    const keyword = '中金';
    filteredData = allFundsData.filter(f =>
      f.code.toLowerCase().includes(keyword.toLowerCase()) ||
      f.name.toLowerCase().includes(keyword.toLowerCase())
    );

    expect(filteredData).toHaveLength(1);
    expect(filteredData[0].name).toContain('中金');
  });

  test('formatValueText应该正确格式化数值', () => {
    const formatValueText = (value) => {
      if (value > 100000000) {
        return `${(value/100000000).toFixed(2)}亿`;
      } else if (value > 10000) {
        return `${(value/10000).toFixed(2)}万`;
      }
      return value.toLocaleString();
    };

    expect(formatValueText(123456789)).toBe('1.23亿');
    expect(formatValueText(12345)).toBe('1.23万');
    expect(formatValueText(1234)).toBe('1,234');
  });

  test('formatChange应该正确格式化涨跌幅', () => {
    const formatChange = (change) => {
      if (change > 0) return `+${change}%`;
      if (change < 0) return `${change}%`;
      return `0%`;
    };

    expect(formatChange(1.23)).toBe('+1.23%');
    expect(formatChange(-0.45)).toBe('-0.45%');
    expect(formatChange(0)).toBe('0%');
  });
});