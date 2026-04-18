/**
 * API封装模块
 * 简单直接，不做复杂转换
 */

const API_BASE_URL = 'http://localhost:5074/api';
const USE_MOCK = false;

async function request(url, options = {}) {
    const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
    
    const response = await fetch(fullUrl, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || '请求失败');
    }
    
    return data;
}

// 获取基金列表
async function getFunds() {
    if (USE_MOCK) {
        return { data: ALL_FUNDS || [] };
    }
    
    try {
        return await request('/funds');
    } catch (error) {
        console.warn('API失败，使用Mock:', error.message);
        return { data: ALL_FUNDS || [] };
    }
}

// 获取基金详情
async function getFundDetail(code) {
    if (USE_MOCK) {
        const fund = ALL_FUNDS.find(f => f.code === code);
        return { data: fund };
    }
    
    try {
        return await request(`/funds/${code}`);
    } catch (error) {
        const fund = ALL_FUNDS.find(f => f.code === code);
        return { data: fund };
    }
}

// 获取K线数据
async function getKline(code, period = '1d', limit = 100) {
    try {
        return await request(`/funds/${code}/kline?period=${period}&limit=${limit}`);
    } catch (error) {
        return { data: [] };
    }
}

// 获取公告列表
async function getAnnouncements(params = {}) {
    try {
        const queryString = new URLSearchParams(params).toString();
        return await request(`/announcements?${queryString}`);
    } catch (error) {
        return { data: [] };
    }
}

// 导出API
window.REITS_API = {
    getFunds,
    getFundDetail,
    getKline,
    getAnnouncements
};
