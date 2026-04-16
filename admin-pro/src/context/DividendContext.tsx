import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { Dividend, DividendFilters, DividendState, DividendStore, DividendStats, MonthlyDividendData } from '../types/dividend';
import { dividendService } from '../services/dividendService';

interface DividendContextValue extends DividendStore {}

const DividendContext = createContext<DividendContextValue | undefined>(undefined);

type DividendAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_DIVIDENDS'; payload: Dividend[] }
  | { type: 'SET_STATS'; payload: DividendStats[] }
  | { type: 'SET_MONTHLY_DATA'; payload: MonthlyDividendData }
  | { type: 'SET_UPCOMING'; payload: Dividend[] }
  | { type: 'SET_FILTERS'; payload: Partial<DividendFilters> }
  | { type: 'CLEAR_ERROR' };

const initialState: DividendState = {
  dividends: [],
  loading: false,
  error: null,
  filters: {},
  stats: [],
  monthlyData: {},
  upcoming: [],
};

function dividendReducer(state: DividendState, action: DividendAction): DividendState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_DIVIDENDS':
      return { ...state, dividends: action.payload };
    case 'SET_STATS':
      return { ...state, stats: action.payload };
    case 'SET_MONTHLY_DATA':
      return { ...state, monthlyData: action.payload };
    case 'SET_UPCOMING':
      return { ...state, upcoming: action.payload };
    case 'SET_FILTERS':
      return { ...state, filters: { ...state.filters, ...action.payload } };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

interface DividendProviderProps {
  children: ReactNode;
}

export function DividendProvider({ children }: DividendProviderProps): JSX.Element {
  const [state, dispatch] = useReducer(dividendReducer, initialState);

  const loadDividends = async (filters?: DividendFilters): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'CLEAR_ERROR' });

      const effectiveFilters = { ...state.filters, ...filters };
      const response = await dividendService.getDividendCalendar(effectiveFilters);

      if (response.success) {
        dispatch({ type: 'SET_DIVIDENDS', payload: response.data });

        // 生成月度数据
        const monthlyData = dividendService.generateMonthlyData(response.data);
        dispatch({ type: 'SET_MONTHLY_DATA', payload: monthlyData });
      } else {
        throw new Error(response.message || '获取分红数据失败');
      }
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : '未知错误' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const loadStats = async (): Promise<void> => {
    try {
      const response = await dividendService.getDividendStats();
      if (response.success) {
        dispatch({ type: 'SET_STATS', payload: response.data });
      }
    } catch (error) {
      console.error('加载统计失败:', error);
    }
  };

  const loadUpcoming = async (days: number = 30): Promise<void> => {
    try {
      const response = await dividendService.getUpcomingDividends(days);
      if (response.success) {
        dispatch({ type: 'SET_UPCOMING', payload: response.data });
      }
    } catch (error) {
      console.error('加载即将分红失败:', error);
    }
  };

  const setFilters = (filters: Partial<DividendFilters>): void => {
    dispatch({ type: 'SET_FILTERS', payload: filters });
  };

  const clearError = (): void => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  // 初始化加载
  useEffect(() => {
    loadDividends();
    loadStats();
    loadUpcoming();
  }, []);

  const value: DividendContextValue = {
    ...state,
    loadDividends,
    loadStats,
    loadUpcoming,
    setFilters,
    clearError,
  };

  return <DividendContext.Provider value={value}>{children}</DividendContext.Provider>;
}

export function useDividend(): DividendStore {
  const context = useContext(DividendContext);
  if (context === undefined) {
    throw new Error('useDividend必须在DividendProvider内使用');
  }
  return context;
}