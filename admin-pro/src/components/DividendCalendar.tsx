import React, { useState, useEffect } from 'react';
import { useDividend } from '../context/DividendContext';
import { Dividend } from '../types/dividend';
import { dividendService } from '../services/dividendService';

interface DividendCalendarProps {
  className?: string;
}

export function DividendCalendar({ className }: DividendCalendarProps): JSX.Element {
  const { dividends, loading, error } = useDividend();
  const [currentYear, setCurrentYear] = useState<number>(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(new Date().getMonth() + 1);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const getDividendsForDate = (year: number, month: number, day: number): Dividend[] => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return dividends.filter(d => d.dividend_date === dateStr);
  };

  const renderMiniCalendar = (): JSX.Element => {
    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const startWeekday = firstDay.getDay();
    const daysInMonth = lastDay.getDate();
    const today = new Date();
    const isCurrentMonth = today.getFullYear() === currentYear && today.getMonth() + 1 === currentMonth;

    const weekDays = ['日', '一', '二', '三', '四', '五', '六'];

    return (
      <div className="mini-calendar space-y-2">
        {/* 星期标题 */}
        <div className="grid grid-cols-7 gap-1 text-center">
          {weekDays.map((day, idx) => (
            <div
              key={idx}
              className={`py-1 text-xs font-medium ${
                idx === 0 ? 'text-red-500' : idx === 6 ? 'text-blue-500' : 'text-gray-600'
              }`}
            >
              {day}
            </div>
          ))}
        </div>

        {/* 日期格子 */}
        <div className="grid grid-cols-7 gap-1">
          {/* 空白占位 */}
          {Array.from({ length: startWeekday }).map((_, i) => (
            <div key={`empty-${i}`} className="day-cell bg-gray-50 rounded min-h-[48px]" />
          ))}

          {/* 日期 */}
          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const dayDividends = getDividendsForDate(currentYear, currentMonth, day);
            const hasDividend = dayDividends.length > 0;
            const isToday = isCurrentMonth && today.getDate() === day;

            return (
              <div
                key={day}
                className={`day-cell border rounded cursor-pointer hover:shadow-md transition-all min-h-[48px] p-1 ${
                  isToday
                    ? 'bg-blue-50 border-2 border-blue-500'
                    : hasDividend
                    ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-white border-gray-100'
                }`}
                onClick={() => hasDividend && setSelectedDay(day)}
              >
                <div
                  className={`text-xs font-medium text-center mb-1 ${
                    isToday ? 'text-blue-600' : 'text-gray-700'
                  }`}
                >
                  {day}
                </div>

                {hasDividend && (
                  <div className="space-y-1">
                    {dayDividends.slice(0, 2).map(dividend => (
                      <div
                        key={dividend.id}
                        className="dividend-tag text-[10px] px-1 py-0.5 rounded truncate"
                        title={`${dividend.fund_name || ''} ¥${dividend.dividend_amount}`}
                      >
                        {dividend.fund_name?.replace('REIT', '').slice(0, 4)} ¥{dividend.dividend_amount}
                      </div>
                    ))}
                    {dayDividends.length > 2 && (
                      <div className="text-[10px] text-orange-600 text-center">+{dayDividends.length - 2}</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const changeMonth = (delta: number): void => {
    let newMonth = currentMonth + delta;
    let newYear = currentYear;

    if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    } else if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    }

    setCurrentYear(newYear);
    setCurrentMonth(newMonth);
  };

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

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>
      {/* 头部 */}
      <div className="p-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-bold text-gray-900 text-sm">📅 分红日历</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => changeMonth(-1)}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-sm font-medium text-gray-900">
            {currentYear}年{currentMonth}月
          </span>
          <button
            onClick={() => changeMonth(1)}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* 紧凑日历 */}
      <div className="p-3">{renderMiniCalendar()}</div>

      {/* 选中日期的详细信息 */}
      {selectedDay && (
        <div className="border-t border-gray-100 p-3">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-900">
              {currentYear}年{currentMonth}月{selectedDay}日 分红详情
            </h4>
            <button
              onClick={() => setSelectedDay(null)}
              className="text-gray-400 hover:text-gray-600 p-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="space-y-2">
            {getDividendsForDate(currentYear, currentMonth, selectedDay).map(dividend => (
              <div key={dividend.id} className="p-2 border border-gray-100 rounded-lg hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="font-medium text-xs text-gray-900 truncate">{dividend.fund_name}</div>
                    <div className="text-xs text-gray-400">{dividend.fund_code}</div>
                  </div>
                  <div className="text-right flex-none ml-2">
                    <div className="text-red-600 font-bold text-sm">¥{dividend.dividend_amount}</div>
                    <div className="text-xs text-gray-400">派息率{dividend.yield || 0}%</div>
                  </div>
                </div>
                <div className="flex gap-3 mt-1 text-xs text-gray-500">
                  <span>除息: <span className="text-gray-700">{dividend.ex_dividend_date?.slice(5) || '-'}</span></span>
                  <span>派息: <span className="text-gray-700">{dividend.payment_date?.slice(5) || '-'}</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}