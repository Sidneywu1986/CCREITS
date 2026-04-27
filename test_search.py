from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    
    logs = []
    page.on('console', lambda msg: logs.append(f'[{msg.type}] {msg.text}'))
    
    page.goto('http://localhost:5173/market.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    search_input = page.query_selector('#global-search')
    print('Search input found:', search_input is not None)
    
    if search_input:
        search_input.fill('508')
        time.sleep(2)
        
        rows = page.query_selector_all('#fund-list tr')
        print('Table rows after search:', len(rows))
        
        for row in rows[:5]:
            code_el = row.query_selector('td:first-child')
            name_el = row.query_selector('td:nth-child(2)')
            if code_el and name_el:
                print(f'  {code_el.inner_text().strip()} - {name_el.inner_text().strip()}')
    
    print('\nConsole logs (last 20):')
    for log in logs[-20:]:
        print(log)
    
    browser.close()
