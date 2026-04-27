/**
 * REITs 数据平台 - 统一导航栏组�? * 所有页面共享，消除 10+ 份重复代�? */

(function () {
    const { SECTOR_CONFIG, NAV_ITEMS, debounce, showToast } = window.REITS || {};

    // 当前页面标识（从 URL 路径提取�?    function getCurrentPageId() {
        const path = window.location.pathname;
        const filename = path.split('/').pop().replace('.html', '');
        // 映射特殊页面
        const map = { 'index': 'market', 'fund-archive': 'fund-archive' };
        return map[filename] || filename;
    }

    // 生成导航�?HTML
    function renderHeader(containerId, options = {}) {
        const container = document.getElementById(containerId || 'app-header');
        if (!container) {
            console.warn(`Header container #${containerId} not found`);
            return;
        }

        const currentPageId = getCurrentPageId();
        const searchMode = options.searchMode || 'global-dropdown'; // 'global-dropdown' | 'table-filter'
        const onSearch = options.onSearch || null; // 页面内搜索回�?
        // 构建导航链接
        let navHtml = '';
        for (const item of NAV_ITEMS) {
            const isActive = item.id === currentPageId;
            const activeClass = isActive
                ? `text-blue-600 bg-blue-50 ${item.id === 'ai-chat' ? 'bg-purple-50 text-purple-600' : ''}`
                : 'text-gray-600 hover:bg-gray-100';
            const highlightDot = item.highlight
                ? `<span class="w-1.5 h-1.5 bg-${item.highlightClass || 'purple'}-500 rounded-full animate-pulse"></span>`
                : '';
            navHtml += `<a href="${item.href}" class="px-3 py-1.5 text-sm font-medium rounded-lg transition-all flex items-center gap-1 ${activeClass}">${highlightDot}${item.label}</a>`;
        }

        // 构建搜索�?        const searchHtml = `
            <div class="w-48 mx-2">
                <div class="relative flex items-center">
                    <input type="text" id="global-search" placeholder="搜索基金代码或名�?.."
                        class="w-full pl-10 pr-16 py-2 bg-gray-100 border border-transparent rounded-lg text-sm focus:outline-none focus:bg-white focus:border-blue-500 transition-all"
                        autocomplete="off">
                    <svg class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    <button id="search-btn" class="absolute right-1 top-1/2 -translate-y-1/2 px-2 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors">
                        搜索
                    </button>
                </div>
                <!-- 全局搜索下拉 -->
                <div id="search-dropdown" class="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 hidden max-h-80 overflow-y-auto"></div>
            </div>
        `;

        container.innerHTML = `
            <header class="h-[60px] bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-none z-40 relative">
                <div class="flex items-center gap-4">
                    <div class="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-sm">R</div>
                    <span class="font-bold text-gray-900 text-lg tracking-tight">REITs数据平台</span>
                    <nav class="hidden md:flex items-center gap-0.5 ml-4">${navHtml}</nav>
                </div>
                ${searchHtml}
                <div class="flex items-center gap-3 md:gap-4">
                    <button class="p-2 text-gray-500 hover:text-gray-700 relative" onclick="window.location.href='./announcements.html'">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                        </svg>
                        <span id="nav-badge" class="hidden absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                    </button>
                    <button class="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-all flex items-center gap-1" onclick="window.location.href='./portfolio.html'">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/></svg>
                        自�?                    </button>
                    <button class="hidden md:block p-2 text-gray-500 hover:text-gray-700" onclick="if(window.toggleAboutModal) window.toggleAboutModal()">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </button>
                </div>
            </header>
        `;

        // 绑定搜索事件
        bindSearchEvents(searchMode, onSearch);
    }

    // 搜索事件绑定
    function bindSearchEvents(searchMode, onSearch) {
        const searchInput = document.getElementById('global-search');
        const searchBtn = document.getElementById('search-btn');
        const dropdown = document.getElementById('search-dropdown');

        if (!searchInput) return;

        function doSearch() {
            const val = searchInput.value.trim();
            if (searchMode === 'table-filter' && onSearch) {
                // 页面内过滤模�?                onSearch(val);
                hideDropdown();
            } else {
                // 全局下拉跳转模式
                if (val) {
                    showDropdown(val);
                } else {
                    hideDropdown();
                }
            }
        }

        // input 事件（防抖）
        searchInput.addEventListener('input', debounce((e) => {
            if (searchMode === 'table-filter' && onSearch) {
                onSearch(e.target.value.trim());
            } else {
                const val = e.target.value.trim();
                if (val) showDropdown(val);
                else hideDropdown();
            }
        }, 300));

        // 回车�?        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                if (searchMode === 'global-dropdown') {
                    // 回车时跳转到市场页并搜索
                    const val = searchInput.value.trim();
                    if (val) {
                        window.location.href = `./market.html?search=${encodeURIComponent(val)}`;
                    }
                } else if (onSearch) {
                    onSearch(searchInput.value.trim());
                }
            }
        });

        // 搜索按钮
        if (searchBtn) {
            searchBtn.addEventListener('click', doSearch);
        }

        // 点击外部关闭下拉
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
                hideDropdown();
            }
        });
    }

    // 显示搜索下拉
    function showDropdown(keyword) {
        const dropdown = document.getElementById('search-dropdown');
        if (!dropdown) return;

        const ALL_FUNDS = window.ALL_FUNDS || (window.REITS && window.REITS.ALL_FUNDS) || [];
        const kw = keyword.toLowerCase();
        const matches = ALL_FUNDS.filter(f => {
            const code = (f.code || '').toLowerCase();
            const name = (f.name || '').toLowerCase();
            return code.includes(kw) || name.includes(kw);
        }).slice(0, 8);

        if (matches.length === 0) {
            dropdown.innerHTML = '<div class="px-4 py-3 text-sm text-gray-400">无匹配结�?/div>';
        } else {
            dropdown.innerHTML = matches.map(f => {
                const sector = SECTOR_CONFIG[f.sector] || { name: '其他', icon: '📌' };
                return `
                    <a href="./fund-detail.html?code=${f.code}" class="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors cursor-pointer">
                        <span class="text-xs text-gray-400 w-14 mono">${f.code}</span>
                        <span class="text-sm text-gray-900 flex-1">${f.name}</span>
                        <span class="text-xs text-gray-500">${sector.icon} ${sector.name}</span>
                    </a>
                `;
            }).join('');
        }

        dropdown.classList.remove('hidden');
    }

    function hideDropdown() {
        const dropdown = document.getElementById('search-dropdown');
        if (dropdown) dropdown.classList.add('hidden');
    }

    // 暴露全局函数
    window.REITS_Header = {
        render: renderHeader,
        getCurrentPageId
    };

    console.log('[REITS Header] component loaded');
})();
