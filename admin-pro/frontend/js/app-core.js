/**
 * REITs 数据平台 - 核心共享模块
 * 整合 common.js + api.js + dataLoader.js 功能
 * 所有页面统一引入，消除重复代码 */

(function () {
    'use strict';

    // ==================== 配置 ====================
    const API_BASE_URL = (typeof window !== 'undefined' && window.API_BASE_URL) || 'http://localhost:5074/api';
    const APP_VERSION = '20260423.1';

    // ==================== 板块配置 ====================
    const SECTOR_CONFIG = {
        'transport': { name: '交通基础设施', icon: '🛣', tagClass: 'sector-transport', color: 'green' },
        'logistics': { name: '仓储物流', icon: '📦', tagClass: 'sector-logistics', color: 'blue' },
        'industrial': { name: '产业园区', icon: '🏭', tagClass: 'sector-industrial', color: 'indigo' },
        'consumer': { name: '消费基础设施', icon: '🛒', tagClass: 'sector-consumer', color: 'pink' },
        'energy': { name: '能源基础设施', icon: '⚡', tagClass: 'sector-energy', color: 'yellow' },
        'housing': { name: '租赁住房', icon: '🏠', tagClass: 'sector-housing', color: 'purple' },
        'eco': { name: '生态环保', icon: '🌿', tagClass: 'sector-eco', color: 'emerald' },
        'water': { name: '水利设施', icon: '💧', tagClass: 'sector-water', color: 'cyan' },
        'municipal': { name: '市政设施', icon: '🏛', tagClass: 'sector-municipal', color: 'gray' },
        'datacenter': { name: '数据中心', icon: '🖥', tagClass: 'sector-datacenter', color: 'orange' },
        'commercial': { name: '商业办公', icon: '🏢', tagClass: 'sector-commercial', color: 'slate' },
        'elderly': { name: '养老设施', icon: '👴', tagClass: 'sector-elderly', color: 'rose' },
        'other': { name: '其他', icon: '📌', tagClass: 'sector-other', color: 'gray' }
    };

    // ==================== 导航配置 ====================
    const NAV_ITEMS = [
        { id: 'market', label: '市场', href: './market.html' },
        { id: 'fund-detail', label: '详情', href: './fund-detail.html' },
        { id: 'ai-chat', label: 'AI聊REITs', href: './ai-chat.html', highlight: true, highlightClass: 'purple' },
        { id: 'announcements', label: '公告', href: './announcements.html' },
        { id: 'article-search', label: '知识库', href: './article-search.html' },
        { id: 'portfolio', label: '自选', href: './portfolio.html' },
        { id: 'compare', label: '对比', href: './compare.html' },
        { id: 'tools', label: '工具', href: './tools.html' },
        { id: 'dividend-calendar', label: '分红', href: './dividend-calendar.html' },
        { id: 'fund-archive', label: 'AI投研', href: './fund-archive.html' },
    ];

    // ==================== 工具函数 ====================
    function debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function throttle(fn, delay) {
        let last = 0;
        return function (...args) {
            const now = Date.now();
            if (now - last >= delay) {
                last = now;
                fn.apply(this, args);
            }
        };
    }

    function formatChange(change) {
        if (change === undefined || change === null) return '--';
        const val = parseFloat(change);
        if (isNaN(val)) return '--';
        const sign = val >= 0 ? '+' : '';
        return `${sign}${val.toFixed(2)}%`;
    }

    function formatValueText(value) {
        const absValue = Math.abs(value || 0);
        const sign = (value || 0) < 0 ? '-' : '';
        if (absValue >= 100000000) return `${sign}${(absValue / 100000000).toFixed(2)}亿`;
        if (absValue >= 10000) return `${sign}${(absValue / 10000).toFixed(2)}万`;
        return `${sign}${absValue.toLocaleString()}`;
    }

    function isTradingTime() {
        const now = new Date();
        const day = now.getDay();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const time = hour * 100 + minute;
        if (day === 0 || day === 6) return false;
        const isMorning = time >= 930 && time <= 1130;
        const isAfternoon = time >= 1300 && time <= 1500;
        return isMorning || isAfternoon;
    }

    // ==================== API 封装 ====================
    async function request(url, options = {}) {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        const response = await fetch(fullUrl, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error || '请求失败');
        return data;
    }

    async function getFunds() {
        try { return await request('/funds/list'); }
        catch (e) { console.warn('API失败，使用Mock:', e.message); return { data: window.ALL_FUNDS || [] }; }
    }

    async function getFundDetail(code) {
        try { return await request(`/funds/detail?code=${code}`); }
        catch (e) { const fund = (window.ALL_FUNDS || []).find(f => f.code === code); return { data: fund }; }
    }

    async function getQuotesRealtime() {
        try {
            const res = await fetch(`${API_BASE_URL}/quotes/realtime`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return data;
        } catch (e) {
            console.warn('实时行情API失败:', e.message);
            return { success: false, data: [] };
        }
    }

    async function getMarketIndices() {
        try { return await request('/market-indices/list'); }
        catch (e) { return { data: [] }; }
    }

    async function getAnnouncements(params = {}) {
        try {
            const qs = new URLSearchParams(params).toString();
            return await request(`/announcements?${qs}`);
        } catch (e) { return { data: [] }; }
    }

    // ==================== 数据加载器====================
    async function loadFunds(mockData = []) {
        try {
            const result = await getFunds();
            return { data: result.data || [], source: 'api' };
        } catch (error) {
            console.warn('API加载失败，使用Mock数据:', error.message);
            return { data: mockData, source: 'mock' };
        }
    }

    function filterFunds(funds, filters = {}) {
        let filtered = [...funds];
        if (filters.sector && filters.sector !== 'all') {
            filtered = filtered.filter(f => f.sector === filters.sector);
        }
        if (filters.keyword) {
            const kw = filters.keyword.toLowerCase();
            filtered = filtered.filter(f => {
                const code = (f.code || '').toString().toLowerCase();
                const name = (f.name || '').toString().toLowerCase();
                const sectorName = (f.sectorName || SECTOR_CONFIG[f.sector]?.name || '').toLowerCase();
                return code.includes(kw) || name.includes(kw) || sectorName.includes(kw);
            });
        }
        return filtered;
    }

    function sortFunds(funds, sortBy = 'change-desc') {
        const [field, order] = sortBy.split('-');
        const sorted = [...funds];
        sorted.sort((a, b) => {
            let va = a[field], vb = b[field];
            const isVaInvalid = va === undefined || va === null || Number.isNaN(va);
            const isVbInvalid = vb === undefined || vb === null || Number.isNaN(vb);
            if (isVaInvalid && !isVbInvalid) return 1;
            if (!isVaInvalid && isVbInvalid) return -1;
            if (isVaInvalid && isVbInvalid) return 0;
            return order === 'asc' ? va - vb : vb - va;
        });
        return sorted;
    }

    // ==================== 对比栏功能====================
    function getCompareList() {
        try {
            const data = localStorage.getItem('reits_compare');
            return JSON.parse(data || '[]');
        } catch (e) {
            console.warn('读取对比列表失败:', e);
            return [];
        }
    }

    function saveCompareList(list) {
        localStorage.setItem('reits_compare', JSON.stringify(list));
    }

    function toggleCompare(code, name, sector) {
        const list = getCompareList();
        const idx = list.findIndex(c => c.code === code);
        if (idx >= 0) {
            list.splice(idx, 1);
            showToast('已从对比栏移除', 'info');
        } else {
            if (list.length >= 4) {
                showToast('对比栏已满（最多4只）', 'warning');
                return false;
            }
            list.push({ code, name, sector });
            showToast('已加入对比栏', 'success');
        }
        saveCompareList(list);
        if (window.REITS && window.REITS.updateCompareBarUI) {
            window.REITS.updateCompareBarUI(list);
        }
        return true;
    }

    function isInCompare(code) {
        return getCompareList().some(c => c.code === code);
    }

    // ==================== Toast 通知 ====================
    function showToast(message, type) {
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };
        const toast = document.createElement('div');
        toast.className = `fixed top-20 left-1/2 -translate-x-1/2 ${colors[type] || colors.info} text-white px-4 py-2 rounded-lg shadow-lg z-[200] text-sm animate-fade-in`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

    // ==================== 全局导出 ====================
    window.REITS = {
        SECTOR_CONFIG,
        NAV_ITEMS,
        API_BASE_URL,
        APP_VERSION,
        debounce,
        throttle,
        formatChange,
        formatValueText,
        isTradingTime,
        showToast,
        request,
        getFunds,
        getFundDetail,
        getQuotesRealtime,
        getMarketIndices,
        getAnnouncements,
        loadFunds,
        filterFunds,
        sortFunds,
        getCompareList,
        saveCompareList,
        toggleCompare,
        isInCompare,
        updateCompareBarUI: function() {}
    };

    console.log(`[REITS Core] v${APP_VERSION} loaded`);
})();
