/**
 * REITs 数据平台 - 统一对比栏组�? * 所有需要对比功能的页面共享
 */

(function () {
    const { getCompareList, saveCompareList, toggleCompare, isInCompare, SECTOR_CONFIG } = window.REITS || {};

    // 渲染对比�?HTML 到容�?    function renderCompareBar(containerId) {
        const container = document.getElementById(containerId || 'compare-bar-container');
        if (!container) return;

        container.innerHTML = `
            <div id="compare-bar" class="compare-bar fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50 transform translate-y-full transition-transform duration-300">
                <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
                    <div class="flex items-center gap-4">
                        <span class="text-sm font-medium text-gray-700">对比�?/span>
                        <span id="compare-count" class="text-xs text-gray-500">(0/4)</span>
                        <div id="compare-items" class="flex items-center gap-2"></div>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="REITS_CompareBar.clearAll()" class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors">清空</button>
                        <button id="compare-action-btn" onclick="REITS_CompareBar.goCompare()" class="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-all opacity-50 cursor-not-allowed" disabled>
                            开始对�?                        </button>
                    </div>
                </div>
            </div>
        `;

        updateUI();
    }

    // 更新对比�?UI
    function updateUI() {
        const list = getCompareList ? getCompareList() : [];
        const itemsContainer = document.getElementById('compare-items');
        const countEl = document.getElementById('compare-count');
        const bar = document.getElementById('compare-bar');
        const actionBtn = document.getElementById('compare-action-btn');

        if (countEl) countEl.textContent = `(${list.length}/4)`;

        if (itemsContainer) {
            itemsContainer.innerHTML = list.map(item => {
                const sector = SECTOR_CONFIG ? (SECTOR_CONFIG[item.sector] || {}) : {};
                return `
                    <div class="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-md text-xs">
                        <span class="font-medium">${item.name}</span>
                        <button onclick="REITS_CompareBar.remove('${item.code}')" class="text-gray-400 hover:text-red-500 ml-1">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>
                `;
            }).join('');
        }

        // 显示/隐藏对比�?        if (bar) {
            if (list.length > 0) {
                bar.classList.add('show');
                bar.style.transform = 'translateY(0)';
            } else {
                bar.style.transform = 'translateY(100%)';
            }
        }

        // 更新按钮状�?        if (actionBtn) {
            if (list.length >= 2) {
                actionBtn.disabled = false;
                actionBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                actionBtn.disabled = true;
                actionBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }

        // 触发页面自定义更�?        if (window.REITS && window.REITS.updateCompareBarUI) {
            window.REITS.updateCompareBarUI(list);
        }
    }

    // 公共方法
    function add(code, name, sector) {
        if (toggleCompare) {
            const result = toggleCompare(code, name, sector);
            updateUI();
            return result;
        }
        return false;
    }

    function remove(code) {
        const list = getCompareList ? getCompareList() : [];
        const filtered = list.filter(c => c.code !== code);
        if (saveCompareList) saveCompareList(filtered);
        updateUI();
    }

    function clearAll() {
        if (saveCompareList) saveCompareList([]);
        updateUI();
    }

    function goCompare() {
        window.location.href = './compare.html';
    }

    // 暴露全局
    window.REITS_CompareBar = {
        render: renderCompareBar,
        update: updateUI,
        add,
        remove,
        clearAll,
        goCompare
    };

    console.log('[REITS CompareBar] component loaded');
})();
