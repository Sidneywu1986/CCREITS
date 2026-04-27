/**
 * API模块测试
 * 测试策略�? * 1. 测试API成功调用
 * 2. 测试API失败降级到Mock数据
 * 3. 测试错误处理
 */

// 设置Jest环境为jsdom
/**
 * @jest-environment jsdom
 */

// Mock ALL_FUNDS 数据
const MOCK_FUNDS = [
  {
    code: '508001',
    name: '中金普洛�?,
    price: 3.456,
    change_percent: 1.23,
    sector: 'logistics'
  },
  {
    code: '180201',
    name: '华夏越秀',
    price: 2.789,
    change_percent: -0.45,
    sector: 'transport'
  }
];

// 在测试环境中设置全局变量
global.ALL_FUNDS = MOCK_FUNDS;

describe('API模块测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // 重置USE_MOCK为false
    global.USE_MOCK = false;
  });

  describe('getFunds函数', () => {
    test('应该成功获取基金列表', async () => {
      // 模拟成功的API响应
      const mockResponse = {
        success: true,
        data: MOCK_FUNDS
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      // 重新导入模块以获取最新的fetch
      const { getFunds } = require('./api.js');

      const result = await getFunds();

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(result).toEqual(mockResponse);
    });

    test('API失败时应该降级到Mock数据', async () => {
      // 模拟API失败
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      // 重新导入模块
      const { getFunds } = require('./api.js');

      const result = await getFunds();

      expect(global.fetch).toHaveBeenCalledWith('/api/funds', expect.any(Object));
      expect(result).toEqual({ data: MOCK_FUNDS });
    });

    test('USE_MOCK为true时应该直接使用Mock数据', async () => {
      // 设置USE_MOCK为true
      global.USE_MOCK = true;

      // 重新导入模块
      const { getFunds } = require('./api.js');

      const result = await getFunds();

      expect(global.fetch).not.toHaveBeenCalled();
      expect(result).toEqual({ data: MOCK_FUNDS });
    });
  });

  describe('getFundDetail函数', () => {
    test('应该成功获取基金详情', async () => {
      const mockFund = MOCK_FUNDS[0];
      const mockResponse = {
        success: true,
        data: mockFund
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { getFundDetail } = require('./api.js');

      const result = await getFundDetail('508001');

      expect(global.fetch).toHaveBeenCalledWith('/api/funds/508001', expect.any(Object));
      expect(result).toEqual(mockResponse);
    });

    test('API失败时应该降级到Mock数据', async () => {
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      const { getFundDetail } = require('./api.js');

      const result = await getFundDetail('508001');

      expect(global.fetch).toHaveBeenCalledWith('/api/funds/508001', expect.any(Object));
      expect(result).toEqual({ data: MOCK_FUNDS[0] });
    });

    test('USE_MOCK为true时应该直接使用Mock数据', async () => {
      global.USE_MOCK = true;

      const { getFundDetail } = require('./api.js');

      const result = await getFundDetail('508001');

      expect(global.fetch).not.toHaveBeenCalled();
      expect(result).toEqual({ data: MOCK_FUNDS[0] });
    });

    test('当基金代码不存在时应该返回undefined', async () => {
      global.USE_MOCK = true;

      const { getFundDetail } = require('./api.js');

      const result = await getFundDetail('999999');

      expect(result).toEqual({ data: undefined });
    });
  });

  describe('getKline函数', () => {
    test('应该成功获取K线数�?, async () => {
      const mockKline = [
        { time: '2024-01-01', open: 3.4, high: 3.5, low: 3.3, close: 3.45 },
        { time: '2024-01-02', open: 3.45, high: 3.6, low: 3.4, close: 3.55 }
      ];
      const mockResponse = {
        success: true,
        data: mockKline
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { getKline } = require('./api.js');

      const result = await getKline('508001', '1d', 100);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/funds/508001/kline?period=1d&limit=100',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });

    test('API失败时应该返回空数组', async () => {
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      const { getKline } = require('./api.js');

      const result = await getKline('508001', '1d', 100);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/funds/508001/kline?period=1d&limit=100',
        expect.any(Object)
      );
      expect(result).toEqual({ data: [] });
    });
  });

  describe('getAnnouncements函数', () => {
    test('应该成功获取公告列表', async () => {
      const mockAnnouncements = [
        { id: 1, title: '分红公告', category: 'dividend' },
        { id: 2, title: '季报发布', category: 'report' }
      ];
      const mockResponse = {
        success: true,
        data: mockAnnouncements
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { getAnnouncements } = require('./api.js');

      const params = { category: 'dividend', limit: 10 };
      const result = await getAnnouncements(params);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/announcements?category=dividend&limit=10',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });

    test('API失败时应该返回空数组', async () => {
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      const { getAnnouncements } = require('./api.js');

      const result = await getAnnouncements({ category: 'dividend' });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/announcements?category=dividend',
        expect.any(Object)
      );
      expect(result).toEqual({ data: [] });
    });

    test('应该正确处理空参�?, async () => {
      const mockResponse = {
        success: true,
        data: []
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { getAnnouncements } = require('./api.js');

      const result = await getAnnouncements();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/announcements?',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('错误处理', () => {
    test('HTTP错误状态码应该触发降级', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: false,
        status: 500
      });

      const { getFunds } = require('./api.js');

      const result = await getFunds();

      expect(result).toEqual({ data: MOCK_FUNDS });
    });

    test('API返回success为false应该触发降级', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: false, error: 'Server error' })
      });

      const { getFunds } = require('./api.js');

      const result = await getFunds();

      expect(result).toEqual({ data: MOCK_FUNDS });
    });
  });
});
