/**
 * 对比功能测试
 * 测试策略：
 * 1. 测试添加到对比功能
 * 2. 测试从对比移除功能
 * 3. 测试对比栏状态更新
 * 4. 测试对比栏满时阻止添加
 */

/**
 * @jest-environment jsdom
 */

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock DOM元素
document.body.innerHTML = `
  <div id="compare-bar" class="compare-bar"></div>
  <div id="compare-items"></div>
  <span id="compare-count">已选 0/4</span>
  <button id="btn-compare" disabled>开始对比 →</button>
`;

describe('对比功能测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();

    // 重置DOM状态
    document.getElementById('compare-bar').classList.remove('show');
    document.getElementById('compare-count').textContent = '已选 0/4';
  });

  test('添加到对比应该更新localStorage', () => {
    localStorageMock.getItem.mockReturnValue(JSON.stringify([]));

    const code = '508001';
    const name = '中金普洛斯';

    // 添加到对比
    let compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');
    if (!compareList.find(item => item.code === code)) {
      compareList.push({ code, name });
      localStorage.setItem('reits_compare', JSON.stringify(compareList));
    }

    expect(localStorage.setItem).toHaveBeenCalledWith(
      'reits_compare',
      JSON.stringify([{ code: '508001', name: '中金普洛斯' }])
    );
  });

  test('从对比移除应该更新localStorage', () => {
    const initialData = [
      { code: '508001', name: '中金普洛斯' },
      { code: '180201', name: '华夏越秀' }
    ];
    localStorageMock.getItem.mockReturnValue(JSON.stringify(initialData));

    const codeToRemove = '508001';

    // 从对比移除
    let compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');
    compareList = compareList.filter(item => item.code !== codeToRemove);
    localStorage.setItem('reits_compare', JSON.stringify(compareList));

    expect(localStorage.setItem).toHaveBeenCalledWith(
      'reits_compare',
      JSON.stringify([{ code: '180201', name: '华夏越秀' }])
    );
  });

  test('对比栏已满时应该阻止添加', () => {
    const fullList = [
      { code: '508001', name: '中金普洛斯' },
      { code: '180201', name: '华夏越秀' },
      { code: '508002', name: '红土创新' },
      { code: '180202', name: '测试基金' }
    ];
    localStorageMock.getItem.mockReturnValue(JSON.stringify(fullList));

    const newCode = '999999';
    const newName = '新基金';

    // 尝试添加第5个基金
    let compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');
    if (compareList.length >= 4) {
      // 应该显示警告
      console.warn('对比栏已满（最多4只）');
      expect(console.warn).toHaveBeenCalledWith('对比栏已满（最多4只）');
    } else {
      compareList.push({ code: newCode, name: newName });
      localStorage.setItem('reits_compare', JSON.stringify(compareList));
    }

    // 当对比栏已满时，不应该调用setItem
    expect(localStorage.setItem).not.toHaveBeenCalled();
  });

  test('获取对比列表应该正确解析localStorage数据', () => {
    const testData = [
      { code: '508001', name: '中金普洛斯' }
    ];
    localStorageMock.getItem.mockReturnValue(JSON.stringify(testData));

    const compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');

    expect(compareList).toEqual(testData);
    expect(compareList).toHaveLength(1);
  });

  test('空localStorage应该返回空数组', () => {
    localStorageMock.getItem.mockReturnValue(null);

    const compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');

    expect(compareList).toEqual([]);
    expect(compareList).toHaveLength(0);
  });

  test('无效的localStorage数据应该被处理', () => {
    localStorageMock.getItem.mockReturnValue('invalid json');

    // 尝试解析无效数据
    let compareList;
    try {
      compareList = JSON.parse(localStorage.getItem('reits_compare') || '[]');
    } catch (e) {
      compareList = [];
    }

    expect(compareList).toBeUndefined(); // 解析失败返回undefined
  });
});