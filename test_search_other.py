from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    logs = []
    page.on('console', lambda msg: logs.append(msg.text))
    
    pages = [
        'http://localhost:5173/fund-detail.html?code=508000',
        'http://localhost:5173/ai-chat.html',
        'http://localhost:5173/fund-archive.html',
        'http://localhost:5173/dividend-calendar.html',
    ]
    
    for url in pages:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        time.sleep(3)
        
        search_input = page.query_selector('#global-search')
        dropdown = page.query_selector('#global-search-dropdown')
        
        print(f"\n=== {url.split('/')[-1]} ===")
        print(f"  search_input: {search_input is not None}")
        print(f"  dropdown container: {dropdown is not None}")
        
        if search_input:
            search_input.fill('508')
            time.sleep(1)
            
            dropdown_visible = page.evaluate("""
                const d = document.getElementById('global-search-dropdown');
                d ? !d.classList.contains('hidden') : false;
            """)
            print(f"  dropdown visible after '508': {dropdown_visible}")
            
            # Clear input
            search_input.fill('')
            time.sleep(0.5)
    
    browser.close()
