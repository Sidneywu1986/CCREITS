import React, { useEffect, useState } from 'react';
import { useDividend } from '../context/DividendContext';
import { Dividend } from '../types/dividend';
import { dividendService } from '../services/dividendService';

interface UpcomingReminderProps {
  className?: string;
  title?: string;
  days?: number;
  maxItems?: number;
  showEmpty?: boolean;
}

export function UpcomingReminder({
  className,
  title = "⏰ 即将到账",
  days = 30,
  maxItems = 5,
  showEmpty = true
}: UpcomingReminderProps): JSX.Element {
  const { upcoming: contextUpcoming, loading, error, loadUpcoming } = useDividend();
  const [upcoming, setUpcoming] = useState<Dividend[]>([]);
  const [useContext, setUseContext] = useState(true);

  // 加载即将分红数据
  useEffect(() => {
    loadUpcoming(days);
  }, [days, loadUpcoming]);

  // 使用context数据或本地数据
  useEffect(() => {
    if (contextUpcoming && contextUpcoming.length > 0) {
      setUpcoming(contextUpcoming);
      setUseContext(true);
    } else {
      // 降级：从dividendService获取
      dividendService.getUpcomingDividends(days)
        .then(response => {
          if (response.success) {
            setUpcoming(response.data);
            setUseContext(false);
          }
        })
        .catch(() => {
          setUpcoming([]);
        });
    }
  }, [contextUpcoming, days]);

  const sortedUpcoming = [...(upcoming || [])]
    .sort((a, b) => new Date(a.payment_date || '').getTime() - new Date(b.payment_date || '').getTime())
    .slice(0, maxItems);

  const getUrgencyLevel = (daysLeft: number): { level: 'urgent' | 'warning' | 'normal'; text: string } => {
    if (daysLeft <= 3) return { level: 'urgent', text: `${daysLeft}天后` };
    if (daysLeft <= 7) return { level: 'warning', text: `${daysLeft}天后` };
    return { level: 'normal', text: `${daysLeft}天后` };
  };

  const getUrgencyClass = (level: 'urgent' | 'warning' | 'normal'): string => {
    switch (level) {
      case 'urgent':
        return 'bg-red-50 border-red-100 text-red-600';
      case 'warning':
        return 'bg-yellow-50 border-yellow-100 text-yellow-600';
      default:
        return 'bg-green-50 border-green-100 text-green-600';
    }
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-center py-6">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
          <span className="ml-2 text-xs text-gray-600">加载中...</span>
        </div>
      </div>
    );
  }

  if (error && useContext) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center py-6">
          <div className="text-red-500 text-sm mb-1">⚠️ 加载失败</div>
          <div className="text-xs text-gray-600">无法获取即将分红数据</div>
        </div>
      </div>
    );
  }

  if (sortedUpcoming.length === 0 && showEmpty) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center py-6">
          <div className="text-gray-400 text-sm mb-1">✅ 暂无即将到账分红</div>
          <div className="text-xs text-gray-500">未来{days}天内无分红到账</div>
        </div>
      </div>
    );
  }

  if (sortedUpcoming.length === 0 && !showEmpty) {
    return <></>;
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-gray-900 text-sm">{title}</h3>
          <span className="text-xs text-gray-500">
            未来{days}天 · {sortedUpcoming.length}条
          </span>
        </div>
      </div>

      <div className="p-3 space-y-2">
        {sortedUpcoming.map(dividend => {
          const daysLeft = dividend.payment_date
            ? Math.ceil((new Date(dividend.payment_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
            : null;

          if (daysLeft === null || daysLeft < 0) return null;

          const urgency = getUrgencyLevel(daysLeft);
          const sectorClass = dividend.sector || 'industrial';

          return (
            <div
              key={dividend.id}
              className={`p-2 border rounded-lg transition-colors ${getUrgencyClass(urgency.level)}`}
              onClick={() => window.location.href = `./fund-archive.html?code=${dividend.fund_code}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full bg-${sectorClass === 'industrial' ? 'indigo' : sectorClass === 'logistics' ? 'blue' : sectorClass === 'transport' ? 'green' : sectorClass === 'energy' ? 'yellow' : sectorClass === 'housing' ? 'purple' : sectorClass === 'consumer' ? 'pink' : 'gray'}-500`} />
                    <div className="font-medium text-xs text-gray-900 truncate">
                      {dividend.fund_name || '未知基金'}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mono">{dividend.fund_code}</div>
                </div>
                <div className="text-right flex-none ml-2">
                  <div className="text-red-600 font-bold text-sm">
                    ¥{dividend.dividend_amount?.toFixed(2) || '0.00'}
                  </div>
                  <div className={`text-xs font-medium ${urgency.level === 'urgent' ? 'text-red-600' : urgency.level === 'warning' ? 'text-yellow-600' : 'text-green-600'}`}>
                    {urgency.text}
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-1 text-xs text-gray-500">
                <span>除息: {dividend.ex_dividend_date?.slice(5) || '-'}</span>
                <span>到账: {dividend.payment_date?.slice(5) || '-'}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}