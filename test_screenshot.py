from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    # Screenshot 1: market.html initial
    page.goto('http://localhost:5173/market.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    page.screenshot(path='market_before.png')
    print('Saved market_before.png')
    
    # Type "508" in search box
    search_input = page.query_selector('#global-search')
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        page.screenshot(path='market_after_508.png')
        print('Saved market_after_508.png')
        
        # Scroll down to see fund list
        page.evaluate('window.scrollTo(0, 600)')
        time.sleep(1)
        page.screenshot(path='market_after_508_scrolled.png')
        print('Saved market_after_508_scrolled.png')
        
        # Clear and type "中金"
        search_input.fill('')
        time.sleep(0.5)
        search_input.fill('中金')
        time.sleep(2)
        page.evaluate('window.scrollTo(0, 600)')
        time.sleep(1)
        page.screenshot(path='market_after_中金_scrolled.png')
        print('Saved market_after_中金_scrolled.png')
    
    browser.close()
