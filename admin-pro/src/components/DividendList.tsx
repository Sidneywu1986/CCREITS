import React, { useState, useMemo } from 'react';
import { useDividend } from '../context/DividendContext';
import { Dividend } from '../types/dividend';
import { dividendService } from '../services/dividendService';

interface DividendListProps {
  className?: string;
  dividends?: Dividend[];
  title?: string;
  showFilters?: boolean;
  maxItems?: number;
}

export function DividendList({
  className,
  dividends: propDividends,
  title = "📋 分红明细",
  showFilters = true,
  maxItems = 20
}: DividendListProps): JSX.Element {
  const { dividends: contextDividends, loading, error } = useDividend();
  const [sortBy, setSortBy] = useState<'date' | 'amount' | 'name'>('date');
  const [filterSector, setFilterSector] = useState<string>('');

  // 使用传入的dividends或context中的数据
  const dividends = propDividends || contextDividends;

  // 获取板块配置
  const getSectorTagClass = (sector: string): string => {
    const tagMap: Record<string, string> = {
      'industrial': 'sector-industrial',
      'logistics': 'sector-logistics',
      'transport': 'sector-transport',
      'energy': 'sector-energy',
      'housing': 'sector-housing',
      'consumer': 'sector-consumer',
      'eco': 'sector-eco',
      'water': 'sector-water',
      'municipal': 'sector-municipal',
      'datacenter': 'sector-datacenter',
      'tourism': 'sector-tourism',
      'commercial': 'sector-commercial',
      'elderly': 'sector-elderly',
      'urban': 'sector-urban'
    };
    return tagMap[sector] || 'sector-industrial';
  };

  // 排序和过滤
  const sortedDividends = useMemo(() => {
    let filtered = [...dividends];

    // 按板块过滤
    if (filterSector) {
      filtered = filtered.filter(d => {
        const fund = dividends.find(f => f.fund_code === d.fund_code);
        return fund?.sector === filterSector;
      });
    }

    // 排序
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date':
          return new Date(b.dividend_date).getTime() - new Date(a.dividend_date).getTime();
        case 'amount':
          return (b.dividend_amount || 0) - (a.dividend_amount || 0);
        case 'name':
          return (a.fund_name || '').localeCompare(b.fund_name || '');
        default:
          return 0;
      }
    });

    return filtered.slice(0, maxItems);
  }, [dividends, sortBy, filterSector, maxItems]);

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-2 text-sm text-gray-600">加载分红数据...</span>
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
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (dividends.length === 0) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">📅 暂无分红数据</div>
          <div className="text-sm text-gray-500">请选择其他时间范围或基金</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>
      {/* 头部 */}
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-gray-900 text-sm">{title}</h3>
          {showFilters && (
            <div className="flex gap-2">
              <button
                onClick={() => {
                  dividendService.clearCache();
                  window.location.reload();
                }}
                className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
              >
                🔄 刷新
              </button>
            </div>
          )}
        </div>

        {/* 筛选器 */}
        {showFilters && (
          <div className="flex flex-wrap gap-2 mb-3">
            {/* 排序选择 */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'date' | 'amount' | 'name')}
              className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
            >
              <option value="date">按日期排序</option>
              <option value="amount">按金额排序</option>
              <option value="name">按名称排序</option>
            </select>

            {/* 板块筛选 */}
            <select
              value={filterSector}
              onChange={(e) => setFilterSector(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
            >
              <option value="">全部板块</option>
              <option value="industrial">产业园区</option>
              <option value="logistics">仓储物流</option>
              <option value="transport">交通基础设施</option>
              <option value="energy">能源基础设施</option>
              <option value="housing">租赁住房</option>
              <option value="consumer">消费基础设施</option>
              <option value="eco">生态环保</option>
              <option value="datacenter">数据中心</option>
            </select>
          </div>
        )}
      </div>

      {/* 分红列表 */}
      <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
        {sortedDividends.map((dividend) => {
          const daysLeft = dividend.dividend_date
            ? Math.ceil((new Date(dividend.dividend_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
            : null;
          const isUrgent = daysLeft !== null && daysLeft >= 0 && daysLeft <= 3;

          return (
            <div
              key={dividend.id}
              className="p-2 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => window.location.href = `./fund-archive.html?code=${dividend.fund_code}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`w-2 h-2 rounded-full ${getSectorTagClass(dividend.sector || 'industrial').replace('sector-', 'bg-').replace('text-', '')}`}
                    title={dividend.sector || '未知板块'}
                  />
                  <div className="min-w-0">
                    <div className="font-medium text-xs text-gray-900 truncate">
                      {dividend.fund_name || '未知基金'}
                    </div>
                    <div className="text-xs text-gray-400 mono">{dividend.fund_code}</div>
                  </div>
                </div>
                <div className="text-right flex-none ml-2">
                  <div className="text-red-600 font-bold text-sm">
                    ¥{dividend.dividend_amount?.toFixed(2) || '0.00'}
                  </div>
                  <div className="text-xs text-gray-400">
                    {dividend.dividend_date?.slice(5) || '-'}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
                <span>登记: {dividend.record_date?.slice(5) || '-'}</span>
                <span>除息: {dividend.ex_dividend_date?.slice(5) || '-'}</span>
                {isUrgent && (
                  <span className="text-red-600 font-bold">⚠️ {daysLeft}天后</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 底部信息 */}
      <div className="p-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>共 {dividends.length} 条记录</span>
          <span>显示 {sortedDividends.length} 条</span>
        </div>
      </div>
    </div>
  );
}