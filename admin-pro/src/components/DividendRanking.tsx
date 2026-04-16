import React, { useMemo, useState } from 'react';
import { useDividend } from '../context/DividendContext';
import { DividendStats } from '../types/dividend';

interface DividendRankingProps {
  className?: string;
  title?: string;
  limit?: number;
  showSector?: boolean;
}

export function DividendRanking({
  className,
  title = "🏆 高分红排行",
  limit = 10,
  showSector = true
}: DividendRankingProps): JSX.Element {
  const { stats, dividends, loading, error } = useDividend();
  const [sortBy, setSortBy] = useState<'total' | 'avg' | 'count'>('total');

  // 计算排行数据
  const ranking = useMemo(() => {
    if (stats && stats.length > 0) {
      // 使用真实统计数据
      return [...stats]
        .sort((a, b) => {
          switch (sortBy) {
            case 'total':
              return b.total_dividend - a.total_dividend;
            case 'avg':
              return b.avg_dividend - a.avg_dividend;
            case 'count':
              return b.dividend_count - a.dividend_count;
            default:
              return 0;
          }
        })
        .slice(0, limit);
    }

    // 降级：基于dividends计算
    const fundMap: Record<string, {
      name: string;
      shortName: string;
      total: number;
      count: number;
      sector: string;
      yield: number;
    }> = {};

    dividends.forEach(dividend => {
      if (!fundMap[dividend.fund_code]) {
        fundMap[dividend.fund_code] = {
          name: dividend.fund_name || '',
          shortName: dividend.fund_name?.replace('REIT', '').slice(0, 4) || '',
          total: 0,
          count: 0,
          sector: dividend.exchange || 'SSE',
          yield: 0
        };
      }
      fundMap[dividend.fund_code].total += dividend.dividend_amount || 0;
      fundMap[dividend.fund_code].count += 1;
    });

    return Object.entries(fundMap)
      .map(([code, data]) => ({
        code,
        ...data,
        avg: data.total / data.count
      }))
      .sort((a, b) => {
        switch (sortBy) {
          case 'total':
            return b.total - a.total;
          case 'avg':
            return b.avg - a.avg;
          case 'count':
            return b.count - a.count;
          default:
            return 0;
        }
      })
      .slice(0, limit);
  }, [stats, dividends, sortBy, limit]);

  const getRankClass = (index: number): string => {
    if (index === 0) return 'bg-yellow-100 text-yellow-700';
    if (index === 1) return 'bg-gray-200 text-gray-700';
    if (index === 2) return 'bg-orange-100 text-orange-700';
    return 'bg-gray-50 text-gray-500';
  };

  const getSectorColor = (sector: string): string => {
    const colorMap: Record<string, string> = {
      'SSE': 'text-blue-600',
      'SZSE': 'text-green-600'
    };
    return colorMap[sector] || 'text-gray-600';
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-2 text-sm text-gray-600">加载排行数据...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center py-8">
          <div className="text-red-500 mb-2">⚠️ 加载失败</div>
          <div className="text-sm text-gray-600">{error}</div>
        </div>
      </div>
    );
  }

  if (ranking.length === 0) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">📊 暂无排行数据</div>
          <div className="text-sm text-gray-500">暂无分红数据统计</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-gray-900 text-sm">{title}</h3>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'total' | 'avg' | 'count')}
            className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
          >
            <option value="total">累计分红</option>
            <option value="avg">平均分红</option>
            <option value="count">分红次数</option>
          </select>
        </div>
      </div>

      <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
        {ranking.map((item, index) => (
          <div
            key={item.code || item.fund_code}
            className="p-2 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
            onClick={() => window.location.href = `./fund-archive.html?code=${item.code || item.fund_code}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-6 h-6 rounded-full ${getRankClass(index)} flex items-center justify-center text-xs font-bold flex-none`}>
                {index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  {showSector && (
                    <span className={`w-1.5 h-1.5 rounded-full ${getSectorColor(item.sector || 'SSE')}`} />
                  )}
                  <div className="font-medium text-xs text-gray-900 truncate">
                    {item.name || item.fund_name}
                  </div>
                </div>
                <div className="text-xs text-gray-400 mono">{item.code || item.fund_code}</div>
              </div>
            </div>

            <div className="flex items-center justify-between mt-1 text-xs">
              <span className="text-red-600 font-bold">
                {sortBy === 'total' && `累计 ¥${(item.total || 0).toFixed(2)}`}
                {sortBy === 'avg' && `平均 ¥${(item.avg || 0).toFixed(2)}`}
                {sortBy === 'count' && `${item.count || item.dividend_count}次分红`}
              </span>
              {item.yield ? (
                <span className="text-green-600">年化 {item.yield}%</span>
              ) : (
                <span className="text-gray-400">{item.count || item.dividend_count}次</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}