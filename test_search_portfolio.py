from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    # Test portfolio
    page.goto('http://localhost:5173/portfolio.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    print("=== portfolio.html ===")
    search_input = page.query_selector('#global-search')
    print(f"search_input: {search_input is not None}")
    
    before = page.evaluate("""
        JSON.stringify({
            filteredCount: typeof filteredFunds !== 'undefined' ? filteredFunds.length : -1,
            searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined',
            watchlistLen: typeof watchlist !== 'undefined' ? watchlist.length : -1
        })
    """)
    print(f"Before: {before}")
    
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        
        after = page.evaluate("""
            JSON.stringify({
                filteredCount: typeof filteredFunds !== 'undefined' ? filteredFunds.length : -1,
                searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined'
            })
        """)
        print(f"After '508': {after}")
    
    # Test announcements
    page.goto('http://localhost:5173/announcements.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    print("\n=== announcements.html ===")
    search_input = page.query_selector('#global-search')
    print(f"search_input: {search_input is not None}")
    
    before = page.evaluate("""
        JSON.stringify({
            filteredCount: typeof filteredAnnouncements !== 'undefined' ? filteredAnnouncements.length : -1,
            searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined'
        })
    """)
    print(f"Before: {before}")
    
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        
        after = page.evaluate("""
            JSON.stringify({
                filteredCount: typeof filteredAnnouncements !== 'undefined' ? filteredAnnouncements.length : -1,
                searchKeyword: typeof searchKeyword !== 'undefined' ? searchKeyword : 'undefined'
            })
        """)
        print(f"After '508': {after}")
    
    browser.close()
