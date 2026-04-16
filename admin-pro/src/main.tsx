import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { DividendCalendarPage } from './pages/DividendCalendarPage';
import { DividendProvider } from './context/DividendContext';

// 简单的导航组件
function Navigation(): JSX.Element {
  return (
    <nav className="hidden md:flex items-center gap-0.5 ml-4">
      <Link to="/market" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">市场</Link>
      <Link to="/fund-detail" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">详情</Link>
      <Link to="/ai-chat" className="px-3 py-1.5 text-sm font-medium text-purple-600 bg-purple-50 rounded-lg transition-all flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse"></span>
        AI聊REITs
      </Link>
      <Link to="/announcements" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">公告</Link>
      <Link to="/portfolio" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">自选</Link>
      <Link to="/compare" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">对比</Link>
      <Link to="/tools" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">工具</Link>
      <Link to="/dividend-calendar" className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg">分红</Link>
      <Link to="/fund-archive" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-all">AI投研</Link>
    </nav>
  );
}

// 主应用组件
function App(): JSX.Element {
  return (
    <React.StrictMode>
      <BrowserRouter>
        <DividendProvider>
          <div className="min-h-screen bg-slate-50">
            {/* 头部 */}
            <header className="h-[60px] bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-none z-40">
              <div className="flex items-center gap-4">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-sm">R</div>
                <span className="font-bold text-gray-900 text-lg tracking-tight">REITs数据平台</span>
                <Navigation />
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
                <button className="p-2 text-gray-500 hover:text-gray-700 relative" onClick={() => window.location.href = '/announcements'}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                  </svg>
                  <span id="nav-badge" className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full hidden"></span>
                </button>
                <button onClick={() => window.location.href = '/portfolio'} className="hidden sm:flex px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:shadow-lg hover:shadow-blue-200 transition-all items-center gap-2">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                  自选
                </button>
                <button onClick={() => alert('关于平台功能')} className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-full flex items-center justify-center text-xs hover:shadow-lg transition-all" title="关于平台">?</button>
              </div>
            </header>

            {/* 主内容区 */}
            <main className="flex-1 overflow-auto bg-slate-50 p-4">
              <Routes>
                <Route path="/dividend-calendar" element={<DividendCalendarPage />} />
                <Route path="/" element={<DividendCalendarPage />} />
                {/* 其他路由将逐步添加 */}
              </Routes>
            </main>
          </div>
        </DividendProvider>
      </BrowserRouter>
    </React.StrictMode>
  );
}

// 渲染应用
const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(<App />);
} else {
  console.error('无法找到root元素，请确保HTML中包含<div id="root"></div>');
}