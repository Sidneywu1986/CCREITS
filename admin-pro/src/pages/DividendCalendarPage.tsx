import React from 'react';
import { DividendCalendar } from '../components/DividendCalendar';
import { DividendList } from '../components/DividendList';
import { DividendChart } from '../components/DividendChart';
import { DividendRanking } from '../components/DividendRanking';
import { UpcomingReminder } from '../components/UpcomingReminder';
import { DividendProvider } from '../context/DividendContext';

export function DividendCalendarPage(): JSX.Element {
  return (
    <DividendProvider>
      <div className="min-h-screen bg-slate-50">
        {/* 头部 */}
        <header className="h-[60px] bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-none z-40">
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              R
            </div>
            <span className="font-bold text-gray-900 text-lg tracking-tight">REITs数据平台</span>
            <nav className="hidden md:flex items-center gap-0.5 ml-4">
              <a href="./market.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">市场</a>
              <a href="./fund-detail.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">详情</a>
              <a href="./ai-chat.html" className="px-3 py-1.5 text-sm font-medium text-purple-600 bg-purple-50 rounded-lg transition-all flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse"></span>
                AI聊REITs
              </a>
              <a href="./announcements.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">公告</a>
              <a href="./portfolio.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">自选</a>
              <a href="./compare.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">对比</a>
              <a href="./tools.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">工具</a>
              <a href="./dividend-calendar.html" className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg">分红</a>
              <a href="./fund-archive.html" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">AI投研</a>
            </nav>
          </div>

          <div className="w-40 mx-2">
            <div className="relative">
              <input type="text" id="global-search" placeholder="搜索基金代码或名称..."
                className="w-full pl-10 pr-4 py-2 bg-gray-100 border border-transparent rounded-lg text-sm focus:outline-none focus:bg-white focus:border-blue-500 transition-all" />
              <svg className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            </div>
          </div>

          <div className="flex items-center gap-3 md:gap-4">
            <button className="p-2 text-gray-500 hover:text-gray-700 relative" onclick="window.location.href='./announcements.html'">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
              <span id="nav-badge" className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full hidden"></span>
            </button>
            <button onclick="window.location.href='./portfolio.html'" className="hidden sm:flex px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:shadow-lg hover:shadow-blue-200 transition-all items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
              自选
            </button>
            <button onclick="showAbout()" className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-full flex items-center justify-center text-xs hover:shadow-lg transition-all" title="关于平台">?</button>
          </div>
        </header>

        {/* 主内容区 */}
        <main className="flex-1 overflow-auto bg-slate-50 p-4">
          <div className="max-w-7xl mx-auto">
            {/* 三栏布局 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              {/* 左栏：分红日历详细列表 */}
              <div className="lg:col-span-1">
                <DividendList className="h-full" />
              </div>

              {/* 中栏：收益分析 */}
              <div className="lg:col-span-1 space-y-4">
                <DividendChart className="h-80" />
                <DividendRanking className="h-80" />
              </div>

              {/* 右栏：我的分红 */}
              <div className="lg:col-span-1 space-y-4">
                <UpcomingReminder className="h-64" />
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-3">
                  <h3 className="font-bold text-gray-900 text-sm mb-2">🧮 税务计算</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">持有期限</span>
                      <select className="text-xs border rounded px-2 py-1">
                        <option>1个月以内</option>
                        <option>1-12个月</option>
                        <option>1年以上</option>
                      </select>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">分红金额</span>
                      <input type="text" placeholder="10000" className="w-20 text-xs border rounded px-2 py-1 text-right" />
                    </div>
                    <div className="flex items-center justify-between text-xs border-t pt-2">
                      <span className="text-gray-700 font-medium">应纳税额</span>
                      <span className="text-red-600 font-bold">2000元</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 紧凑日历 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <DividendCalendar className="w-full" />
            </div>
          </div>
        </main>
      </div>
    </DividendProvider>
  );
}