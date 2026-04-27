from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    
    errors = []
    logs = []
    page.on('console', lambda msg: logs.append(msg.text.encode('ascii', 'ignore').decode()))
    page.on('pageerror', lambda err: errors.append(str(err)))
    
    page.goto('http://localhost:5173/market.html', wait_until='domcontentloaded', timeout=15000)
    time.sleep(5)
    
    search_input = page.query_selector('#global-search')
    if search_input:
        search_input.fill('508')
        time.sleep(2)
    
    print(f"Console logs: {len(logs)}")
    for log in logs[-15:]:
        print(f"  {log[:120]}")
    
    print(f"JS Errors: {len(errors)}")
    for err in errors:
        print(f"  {err[:120]}")
    
    rows = page.query_selector_all('#fund-list tr')
    print(f"Table rows: {len(rows)}")
    
    browser.close()
