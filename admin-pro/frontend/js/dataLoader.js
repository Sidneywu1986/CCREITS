/**
 * 数据加载器模�? * 使用TDD方式开发，确保代码质量和可测试�? */

/**
 * 从API加载基金数据
 * @returns {Promise<Array>} 基金数据数组
 */
async function loadFundsFromAPI() {
  const API_BASE_URL = 'http://localhost:5074/api';
  const response = await fetch(`${API_BASE_URL}/funds`, {
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data = await response.json();

  if (!data.success) {
    throw new Error(data.error || '请求失败');
  }

  return data.data || [];
}

/**
 * 加载基金数据（带降级策略�? * @param {Array} mockData - 降级使用的Mock数据
 * @returns {Promise<Object>} { data: Array, source: string }
 */
async function loadFunds(mockData = []) {
  try {
    const data = await loadFundsFromAPI();
    return { data, source: 'api' };
  } catch (error) {
    console.warn('API加载失败，使用Mock数据:', error.message);
    return { data: mockData, source: 'mock' };
  }
}

/**
 * 筛选基金数�? * @param {Array} funds - 基金数据数组
 * @param {Object} filters - 筛选条�? * @returns {Array} 筛选后的基金数�? */
function filterFunds(funds, filters = {}) {
  let filtered = [...funds];

  // 按板块筛�?  if (filters.sector && filters.sector !== 'all') {
    filtered = filtered.filter(f => f.sector === filters.sector);
  }

  // 按关键词搜索
  if (filters.keyword) {
    const kw = filters.keyword.toLowerCase();
    filtered = filtered.filter(f => {
      const code = (f.code || '').toString().toLowerCase();
      const name = (f.name || '').toString().toLowerCase();
      return code.includes(kw) || name.includes(kw);
    });
  }

  return filtered;
}

/**
 * 排序基金数据
 * @param {Array} funds - 基金数据数组
 * @param {string} sortBy - 排序方式
 * @returns {Array} 排序后的基金数据
 */
function sortFunds(funds, sortBy = 'change-desc') {
  const [field, order] = sortBy.split('-');
  const sorted = [...funds];

  sorted.sort((a, b) => {
    let va = a[field];
    let vb = b[field];

    // 安全处理undefined/null/NaN - 使用Number.isNaN()精确判断NaN
    const isVaInvalid = va === undefined || va === null || Number.isNaN(va);
    const isVbInvalid = vb === undefined || vb === null || Number.isNaN(vb);

    // 如果a的值无效，排在后面
    if (isVaInvalid && !isVbInvalid) return 1;
    // 如果b的值无效，排在前面
    if (!isVaInvalid && isVbInvalid) return -1;
    // 如果都无效，保持原顺�?    if (isVaInvalid && isVbInvalid) return 0;

    // 正常比较
    return order === 'asc' ? va - vb : vb - va;
  });

  return sorted;
}

/**
 * 格式化数值文�? * @param {number} value - 数�? * @returns {string} 格式化后的文�? */
function formatValueText(value) {
  // 处理负数
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  // 先判断亿�?00,000,000�?  if (absValue >= 100000000) {
    const billionValue = absValue / 100000000;
    return `${sign}${billionValue.toFixed(2)}亿`;
  }

  // 再判断万�?0,000�?  if (absValue >= 10000) {
    const tenThousandValue = absValue / 10000;
    return `${sign}${tenThousandValue.toFixed(2)}万`;
  }

  return `${sign}${absValue.toLocaleString()}`;
}

/**
 * 格式化涨跌幅
 * @param {number} change - 涨跌�? * @returns {string} 格式化后的文�? */
function formatChange(change) {
  if (change > 0) return `+${change}%`;
  if (change < 0) return `${change}%`;
  return `0%`;
}

/**
 * 判断当前是否在交易时�? * @returns {boolean} 是否在交易时�? */
function isTradingTime() {
  const now = new Date();
  const day = now.getDay();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const time = hour * 100 + minute;

  // 周末休市
  if (day === 0 || day === 6) return false;

  // 上午 9:30-11:30，下�?13:00-15:00
  const isMorning = time >= 930 && time <= 1130;
  const isAfternoon = time >= 1300 && time <= 1500;

  return isMorning || isAfternoon;
}

// 浏览器环境：直接暴露全局函数
window.REITS_DataLoader = {
  loadFunds,
  filterFunds,
  sortFunds,
  formatValueText,
  formatChange,
  isTradingTime
};
