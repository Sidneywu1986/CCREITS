import { Dividend, DividendCalendarResponse, DividendStats, MonthlyDividendData } from '../types/dividend';

const API_BASE_URL = '/api';
const CACHE_PREFIX = 'reits_dividend_';
const CACHE_EXPIRY = 5 * 60 * 1000; // 5分钟缓存

class DividendService {
  private cache = new Map<string, { data: any; timestamp: number }>();

  private getCached<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_EXPIRY) {
      return cached.data as T;
    }
    return null;
  }

  private setCache<T>(key: string, data: T): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data as T;
    } catch (error) {
      console.error(`API请求失败: ${endpoint}`, error);
      throw error;
    }
  }

  // 获取分红日历列表
  async getDividendCalendar(filters?: {
    fund_codes?: string[];
    start_date?: string;
    end_date?: string;
    exchange?: string;
    page?: number;
    page_size?: number;
  }): Promise<DividendCalendarResponse> {
    const cacheKey = `calendar_${JSON.stringify(filters)}`;
    const cached = this.getCached<DividendCalendarResponse>(cacheKey);
    if (cached) {
      return cached;
    }

    const params = new URLSearchParams();
    if (filters?.fund_codes?.length) {
      params.append('fund_codes', filters.fund_codes.join(','));
    }
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);
    if (filters?.exchange) params.append('exchange', filters.exchange);
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());

    const endpoint = `/dividend-calendar/list${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.request<DividendCalendarResponse>(endpoint);

    this.setCache(cacheKey, response);
    return response;
  }

  // 获取即将分红
  async getUpcomingDividends(days: number = 30, fund_codes?: string[]): Promise<DividendCalendarResponse> {
    const cacheKey = `upcoming_${days}_${fund_codes?.join(',')}`;
    const cached = this.getCached<DividendCalendarResponse>(cacheKey);
    if (cached) {
      return cached;
    }

    const params = new URLSearchParams();
    params.append('days', days.toString());
    if (fund_codes?.length) {
      params.append('fund_codes', fund_codes.join(','));
    }

    const endpoint = `/dividend-calendar/upcoming${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.request<DividendCalendarResponse>(endpoint);

    this.setCache(cacheKey, response);
    return response;
  }

  // 获取基金分红历史
  async getFundDividends(fund_code: string, limit: number = 20): Promise<DividendCalendarResponse> {
    const cacheKey = `fund_${fund_code}_${limit}`;
    const cached = this.getCached<DividendCalendarResponse>(cacheKey);
    if (cached) {
      return cached;
    }

    const endpoint = `/dividend-calendar/${fund_code}?limit=${limit}`;
    const response = await this.request<DividendCalendarResponse>(endpoint);

    this.setCache(cacheKey, response);
    return response;
  }

  // 获取分红统计
  async getDividendStats(year?: number): Promise<{
    success: boolean;
    data: DividendStats[];
    message?: string;
  }> {
    const cacheKey = `stats_${year || 'all'}`;
    const cached = this.getCached<{ success: boolean; data: DividendStats[]; message?: string }>(cacheKey);
    if (cached) {
      return cached;
    }

    const params = year ? `?year=${year}` : '';
    const endpoint = `/dividend-calendar/stats/summary${params}`;
    const response = await this.request<{ success: boolean; data: DividendStats[]; message?: string }>(endpoint);

    this.setCache(cacheKey, response);
    return response;
  }

  // 生成月度统计数据
  generateMonthlyData(dividends: Dividend[]): MonthlyDividendData {
    const monthlyData: MonthlyDividendData = {};

    // 初始化12个月
    for (let i = 1; i <= 12; i++) {
      monthlyData[i] = 0;
    }

    // 累加每月分红金额
    dividends.forEach(dividend => {
      if (dividend.dividend_date) {
        const month = parseInt(dividend.dividend_date.split('-')[1]);
        if (!isNaN(month)) {
          monthlyData[month] += dividend.dividend_amount || 0;
        }
      }
    });

    return monthlyData;
  }

  // 获取基金列表（用于筛选）
  async getFunds(): Promise<{ code: string; name: string; exchange: string; sector: string }[]> {
    const cacheKey = 'funds_list';
    const cached = this.getCached<{ code: string; name: string; exchange: string; sector: string }[]>(cacheKey);
    if (cached) {
      return cached;
    }

    try {
      const response = await this.request<{ success: boolean; data: any[] }>('/funds');
      if (response.success) {
        const funds = response.data.map((fund: any) => ({
          code: fund.code,
          name: fund.name,
          exchange: fund.exchange,
          sector: fund.sector,
        }));
        this.setCache(cacheKey, funds);
        return funds;
      }
      return [];
    } catch (error) {
      console.error('获取基金列表失败:', error);
      return [];
    }
  }

  // 清除缓存
  clearCache(): void {
    this.cache.clear();
  }

  // 获取缓存大小
  getCacheSize(): number {
    return this.cache.size;
  }
}

// 导出单例实例
export const dividendService = new DividendService();