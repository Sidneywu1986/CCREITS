import React, { useEffect, useRef, useState } from 'react';
import { useDividend } from '../context/DividendContext';
import * as echarts from 'echarts';
import { MonthlyDividendData } from '../types/dividend';

interface DividendChartProps {
  className?: string;
  height?: string;
  title?: string;
  showLegend?: boolean;
}

export function DividendChart({
  className,
  height = '300px',
  title = "📊 月度分红趋势",
  showLegend = false
}: DividendChartProps): JSX.Element {
  const { monthlyData, loading, error } = useDividend();
  const chartRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<echarts.ECharts | null>(null);

  // 初始化图表
  useEffect(() => {
    if (chartRef.current && !chart) {
      const newChart = echarts.init(chartRef.current);
      setChart(newChart);

      // 响应式处理
      const handleResize = () => {
        newChart.resize();
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        newChart.dispose();
      };
    }
  }, [chart]);

  // 更新图表数据
  useEffect(() => {
    if (chart && monthlyData) {
      const option = {
        backgroundColor: 'transparent',
        title: {
          text: title,
          textStyle: {
            fontSize: 14,
            fontWeight: 'bold',
            color: '#1e293b'
          },
          left: 'center',
          top: 10
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(30, 41, 59, 0.9)',
          borderColor: 'rgba(59, 130, 246, 0.5)',
          textStyle: {
            color: '#fff',
            fontSize: 12
          },
          formatter: (params: any) => {
            const month = params[0].name;
            const amount = params[0].value || 0;
            return `${month}: ¥${amount.toFixed(2)}元`;
          }
        },
        grid: {
          left: showLegend ? '15%' : '8%',
          right: '8%',
          bottom: '15%',
          top: '25%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
          axisLine: {
            lineStyle: {
              color: '#e2e8f0'
            }
          },
          axisLabel: {
            color: '#64748b',
            fontSize: 11,
            interval: 0
          },
          axisTick: {
            show: false
          }
        },
        yAxis: {
          type: 'value',
          name: '分红金额(元)',
          nameTextStyle: {
            fontSize: 12,
            color: '#64748b'
          },
          axisLine: {
            show: false
          },
          axisLabel: {
            color: '#64748b',
            fontSize: 11,
            formatter: (value: number) => `¥${value.toFixed(0)}`
          },
          splitLine: {
            lineStyle: {
              color: '#f1f5f9',
              type: 'dashed'
            }
          },
          axisTick: {
            show: false
          }
        },
        series: [{
          type: 'bar',
          data: Object.values(monthlyData || {}),
          barWidth: '40%',
          itemStyle: {
            borderRadius: [3, 3, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#60a5fa' }
            ])
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(59, 130, 246, 0.3)'
            }
          },
          animationDuration: 800,
          animationEasing: 'elasticOut'
        }]
      };

      chart.setOption(option, true);
    }
  }, [chart, monthlyData, title, showLegend]);

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-center" style={{ height }}>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-2 text-sm text-gray-600">加载图表数据...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
        <div className="text-center" style={{ height }}>
          <div className="text-red-500 mb-2">⚠️ 图表加载失败</div>
          <div className="text-sm text-gray-600">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>
      <div className="p-3 border-b border-gray-100">
        <h3 className="font-bold text-gray-900 text-sm">{title}</h3>
      </div>
      <div ref={chartRef} style={{ height: `calc(${height} - 60px)` }} />
    </div>
  );
}