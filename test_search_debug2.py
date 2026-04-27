from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    logs = []
    page.on('console', lambda msg: logs.append(msg.text))
    
    page.goto('http://localhost:5173/market.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    # 获取过滤前数据
    before = page.evaluate("""
        JSON.stringify({
            fundsCount: typeof allFundsData !== 'undefined' ? allFundsData.length : -1,
            filteredCount: typeof filteredData !== 'undefined' ? filteredData.length : -1,
            searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined',
            sampleCodes: (typeof allFundsData !== 'undefined' ? allFundsData.slice(0,3).map(f => f.code) : [])
        })
    """)
    print(f"Before search: {before}")
    
    # 输入搜索关键词
    search_input = page.query_selector('#global-search')
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        
        after = page.evaluate("""
            JSON.stringify({
                fundsCount: typeof allFundsData !== 'undefined' ? allFundsData.length : -1,
                filteredCount: typeof filteredData !== 'undefined' ? filteredData.length : -1,
                searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined',
                sampleCodes: (typeof filteredData !== 'undefined' ? filteredData.slice(0,5).map(f => f.code) : [])
            })
        """)
        print(f"After search: {after}")
        
        # 检查第一行代码
        first_code = page.evaluate("""
            const row = document.querySelector('#fund-list tr');
            row ? row.querySelector('td')?.textContent?.trim() : 'no row';
        """)
        print(f"First row code: {first_code}")
    else:
        print("Search input NOT FOUND")
    
    browser.close()
