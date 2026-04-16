/**
 * dataLoader模块测试
 * 使用TDD方式验证所有功能
 */

/**
 * @jest-environment jsdom
 */

global.fetch = jest.fn();

// Mock console.warn to prevent warnings from failing tests
global.console.warn = jest.fn();

// Mock数据
const MOCK_FUNDS = [
  {
    code: '508001',
    name: '中金普洛斯',
    price: 3.456,
    change: 1.23,
    volume: 1234567,
    change_5d: 2.34,
    change_20d: 5.67,
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
    change: -0.45,
    volume: 987654,
    change_5d: -1.23,
    change_20d: 3.45,
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
    change: 0.67,
    volume: 555555,
    change_5d: 1.45,
    change_20d: 2.78,
    yield: 3.89,
    nav: 2.000,
    premium: -0.65,
    debt: 28.8,
    market_cap: 25.3,
    scale: 22.0,
    sector: 'industrial'
  }
];

const dataLoader = require('./dataLoader.js');

describe('dataLoader模块测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('loadFunds函数', () => {
    test('应该从API成功加载数据', async () => {
      const mockResponse = {
        success: true,
        data: MOCK_FUNDS
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await dataLoader.loadFunds();

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(result.data).toEqual(MOCK_FUNDS);
      expect(result.source).toBe('api');
    });

    test('API失败时应该降级到Mock数据', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await dataLoader.loadFunds(MOCK_FUNDS);

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(result.data).toEqual(MOCK_FUNDS);
      expect(result.source).toBe('mock');
    });

    test('HTTP错误状态码应该触发降级', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      });

      const result = await dataLoader.loadFunds(MOCK_FUNDS);

      expect(result.source).toBe('mock');
    });

    test('API返回success为false应该触发降级', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: false, error: 'Server error' })
      });

      const result = await dataLoader.loadFunds(MOCK_FUNDS);

      expect(result.source).toBe('mock');
    });

    test('API返回空数据应该返回空数组', async () => {
      const mockResponse = {
        success: true,
        data: []
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await dataLoader.loadFunds();

      expect(result.data).toEqual([]);
    });
  });

  describe('filterFunds函数', () => {
    test('应该按板块筛选基金', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { sector: 'logistics' });

      expect(filtered).toHaveLength(1);
      expect(filtered[0].sector).toBe('logistics');
    });

    test('sector为all时不应该筛选', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { sector: 'all' });

      expect(filtered).toHaveLength(3);
      expect(filtered).toEqual(MOCK_FUNDS);
    });

    test('应该按关键词搜索基金代码', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { keyword: '508' });

      expect(filtered).toHaveLength(2);
      expect(filtered.map(f => f.code)).toContain('508001');
      expect(filtered.map(f => f.code)).toContain('508002');
    });

    test('应该按关键词搜索基金名称', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { keyword: '中金' });

      expect(filtered).toHaveLength(1);
      expect(filtered[0].name).toContain('中金');
    });

    test('搜索应该不区分大小写', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { keyword: '508' });

      expect(filtered).toHaveLength(2);
      expect(filtered.map(f => f.code)).toContain('508001');
      expect(filtered.map(f => f.code)).toContain('508002');
    });

    test('应该组合板块和关键词筛选', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, {
        sector: 'logistics',
        keyword: '普洛斯'
      });

      expect(filtered).toHaveLength(1);
      expect(filtered[0].sector).toBe('logistics');
      expect(filtered[0].name).toContain('普洛斯');
    });

    test('空关键词不应该影响结果', () => {
      const filtered = dataLoader.filterFunds(MOCK_FUNDS, { keyword: '' });

      expect(filtered).toHaveLength(3);
    });
  });

  describe('sortFunds函数', () => {
    test('应该按涨跌幅降序排序', () => {
      const sorted = dataLoader.sortFunds(MOCK_FUNDS, 'change-desc');

      const changes = sorted.map(f => f.change);
      expect(changes).toEqual([1.23, 0.67, -0.45]);
    });

    test('应该按涨跌幅升序排序', () => {
      const sorted = dataLoader.sortFunds(MOCK_FUNDS, 'change-asc');

      const changes = sorted.map(f => f.change);
      expect(changes).toEqual([-0.45, 0.67, 1.23]);
    });

    test('应该按成交量降序排序', () => {
      const sorted = dataLoader.sortFunds(MOCK_FUNDS, 'volume-desc');

      const volumes = sorted.map(f => f.volume);
      expect(volumes).toEqual([1234567, 987654, 555555]);
    });

    test('应该按价格降序排序', () => {
      const sorted = dataLoader.sortFunds(MOCK_FUNDS, 'price-desc');

      const prices = sorted.map(f => f.price);
      expect(prices).toEqual([3.456, 2.789, 1.987]);
    });

    test('应该处理undefined字段值', () => {
      const fundsWithUndefined = [
        ...MOCK_FUNDS,
        { code: '999999', name: '测试基金', price: undefined, change: undefined }
      ];

      const sorted = dataLoader.sortFunds(fundsWithUndefined, 'change-desc');

      // undefined应该被视为0，排在后面
      expect(sorted[sorted.length - 1].code).toBe('999999');
    });

    test('应该处理NaN字段值', () => {
      const fundsWithNaN = [
        ...MOCK_FUNDS,
        { code: '999999', name: '测试基金', price: NaN, change: NaN }
      ];

      const sorted = dataLoader.sortFunds(fundsWithNaN, 'change-desc');

      // NaN应该被视为0，排在后面
      expect(sorted[sorted.length - 1].code).toBe('999999');
    });

    test('默认排序应该是change-desc', () => {
      const sorted = dataLoader.sortFunds(MOCK_FUNDS);

      const changes = sorted.map(f => f.change);
      expect(changes).toEqual([1.23, 0.67, -0.45]);
    });
  });

  describe('formatValueText函数', () => {
    test('应该格式化亿元级别的数值', () => {
      expect(dataLoader.formatValueText(123456789)).toBe('1.23亿');
      expect(dataLoader.formatValueText(100000000)).toBe('1.00亿');
      // 999999999 / 100000000 = 9.99999999, rounded to 2 decimal places = 10.00
      expect(dataLoader.formatValueText(999999999)).toBe('10.00亿');
    });

    test('应该格式化万元级别的数值', () => {
      expect(dataLoader.formatValueText(12345)).toBe('1.23万');
      expect(dataLoader.formatValueText(10000)).toBe('1.00万');
      // 99999 / 10000 = 9.9999, rounded to 2 decimal places = 10.00
      expect(dataLoader.formatValueText(99999)).toBe('10.00万');
    });

    test('应该格式化普通数值', () => {
      expect(dataLoader.formatValueText(1234)).toBe('1,234');
      expect(dataLoader.formatValueText(123)).toBe('123');
      expect(dataLoader.formatValueText(0)).toBe('0');
    });

    test('应该处理负数', () => {
      expect(dataLoader.formatValueText(-12345)).toBe('-1.23万');
      expect(dataLoader.formatValueText(-123456789)).toBe('-1.23亿');
    });
  });

  describe('formatChange函数', () => {
    test('应该格式化正涨跌幅', () => {
      expect(dataLoader.formatChange(1.23)).toBe('+1.23%');
      expect(dataLoader.formatChange(10)).toBe('+10%');
      expect(dataLoader.formatChange(0.01)).toBe('+0.01%');
    });

    test('应该格式化负涨跌幅', () => {
      expect(dataLoader.formatChange(-0.45)).toBe('-0.45%');
      expect(dataLoader.formatChange(-5)).toBe('-5%');
      expect(dataLoader.formatChange(-100)).toBe('-100%');
    });

    test('应该格式化零涨跌幅', () => {
      expect(dataLoader.formatChange(0)).toBe('0%');
    });

    test('应该处理undefined和null', () => {
      expect(dataLoader.formatChange(undefined)).toBe('0%');
      expect(dataLoader.formatChange(null)).toBe('0%');
    });
  });

  describe('isTradingTime函数', () => {
    test('应该在交易时间内返回true', () => {
      // Mock交易时间: 工作日上午10:30
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(10);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(1); // 周一

      expect(dataLoader.isTradingTime()).toBe(true);
    });

    test('应该在下午交易时间返回true', () => {
      // Mock交易时间: 工作日下午14:30
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(14);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(2); // 周二

      expect(dataLoader.isTradingTime()).toBe(true);
    });

    test('应该在非交易时间返回false', () => {
      // Mock非交易时间: 工作日上午8:00
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(8);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(0);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(3); // 周三

      expect(dataLoader.isTradingTime()).toBe(false);
    });

    test('应该在午间休市返回false', () => {
      // Mock午间休市: 工作日上午12:00
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(12);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(0);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(4); // 周四

      expect(dataLoader.isTradingTime()).toBe(false);
    });

    test('应该在收盘后返回false', () => {
      // Mock收盘后: 工作日下午16:00
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(16);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(0);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(5); // 周五

      expect(dataLoader.isTradingTime()).toBe(false);
    });

    test('应该在周末返回false', () => {
      // Mock周末: 周六上午10:30
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(10);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(6); // 周六

      expect(dataLoader.isTradingTime()).toBe(false);
    });

    test('应该在周日返回false', () => {
      // Mock周日: 周日上午10:30
      jest.spyOn(global.Date.prototype, 'getHours').mockReturnValue(10);
      jest.spyOn(global.Date.prototype, 'getMinutes').mockReturnValue(30);
      jest.spyOn(global.Date.prototype, 'getDay').mockReturnValue(0); // 周日

      expect(dataLoader.isTradingTime()).toBe(false);
    });
  });
});