// 分红日历数据类型定义

export interface Dividend {
  id: number;
  fund_code: string;
  fund_name?: string;
  dividend_date: string; // 分红日期
  dividend_amount: number; // 分红金额（每份）
  record_date?: string; // 权益登记日
  ex_dividend_date?: string; // 除息日
  exchange?: string; // 交易所
  created_at?: string;
}

export interface DividendCalendarResponse {
  success: boolean;
  data: Dividend[];
  total: number;
  message?: string;
}

export interface DividendStats {
  fund_code: string;
  fund_name: string;
  exchange: string;
  dividend_count: number;
  total_dividend: number;
  avg_dividend: number;
  max_dividend: number;
  min_dividend: number;
}

export interface MonthlyDividendData {
  [month: number]: number;
}

export interface SectorConfig {
  name: string;
  icon: string;
  tagClass: string;
  color: string;
}

export type TimeRange = 'week' | 'month' | 'year' | 'all';
export type SortBy = 'date' | 'amount' | 'yield';

export interface DividendFilters {
  fund_codes?: string[];
  start_date?: string;
  end_date?: string;
  exchange?: string;
  sector?: string;
  page?: number;
  page_size?: number;
  sort_by?: SortBy;
  time_range?: TimeRange;
}

export interface DividendState {
  dividends: Dividend[];
  loading: boolean;
  error: string | null;
  filters: DividendFilters;
  stats: DividendStats[];
  monthlyData: MonthlyDividendData;
  upcoming: Dividend[];
}

export interface DividendActions {
  loadDividends: (filters?: DividendFilters) => Promise<void>;
  loadStats: () => Promise<void>;
  loadUpcoming: (days?: number) => Promise<void>;
  setFilters: (filters: Partial<DividendFilters>) => void;
  clearError: () => void;
}

export type DividendStore = DividendState & DividendActions;