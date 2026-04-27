from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    logs = []
    errors = []
    page.on('console', lambda msg: logs.append(f'[{msg.type}] {msg.text}'))
    page.on('pageerror', lambda err: errors.append(str(err)))
    
    print("=== 测试 market.html ===")
    page.goto('http://localhost:5173/market.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    # 检查搜索框是否存在
    search_input = page.query_selector('#global-search')
    print(f'搜索框存在: {search_input is not None}')
    
    # 检查输入事件监听器数量
    listener_count = page.evaluate("""
        (() => {
            const el = document.getElementById('global-search');
            if (!el) return -1;
            // 获取事件监听器数量（仅开发工具可用，JS中无法直接获取）
            return el ? 1 : 0;
        })()
    """)
    print(f'搜索框元素存在: {listener_count >= 0}')
    
    # 获取初始表格行数
    rows_before = page.query_selector_all('#fund-list tr')
    print(f'初始表格行数: {len(rows_before)}')
    
    # 获取 allFundsData
    funds_count = page.evaluate("typeof allFundsData !== 'undefined' ? allFundsData.length : -1")
    print(f'allFundsData 长度: {funds_count}')
    
    # 获取 searchKeyword
    kw = page.evaluate("typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined'")
    print(f'初始 searchKeyword: "{kw}"')
    
    # 输入搜索关键词
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        
        # 再次检查 searchKeyword
        kw_after = page.evaluate("typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined'")
        print(f'输入后 searchKeyword: "{kw_after}"')
        
        # 获取表格行数
        rows_after = page.query_selector_all('#fund-list tr')
        print(f'搜索后表格行数: {len(rows_after)}')
        
        # 获取前3行内容
        for row in rows_after[:3]:
            code_el = row.query_selector('td:first-child')
            name_el = row.query_selector('td:nth-child(2)')
            if code_el and name_el:
                print(f'  行: {code_el.inner_text().strip()} - {name_el.inner_text().strip()}')
    
    print('\n=== Console Logs ===')
    for log in logs[-30:]:
        print(log)
    
    if errors:
        print('\n=== JavaScript Errors ===')
        for err in errors:
            print(err)
    
    browser.close()
