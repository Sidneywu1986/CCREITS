import asyncio
from playwright.async_api import async_playwright

async def test_portfolio():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()

        console_errors = []
        console_logs = []
        page_errors = []

        def handle_console(msg):
            entry = f"[{msg.type}] {msg.text}"
            console_logs.append(entry)
            if msg.type == 'error':
                console_errors.append(entry)
            # Also capture warnings that might indicate issues
            if 'debounce' in msg.text.lower() or 'is not defined' in msg.text.lower():
                console_errors.append(entry)

        def handle_page_error(err):
            page_errors.append(str(err))

        page.on('console', handle_console)
        page.on('pageerror', handle_page_error)

        # Clear localStorage before navigation
        await context.clear_cookies()
        # We need to navigate first to have origin, then clear storage
        await page.goto('http://localhost:5173/portfolio.html', wait_until='networkidle', timeout=15000)
        await page.evaluate("""() => {
            localStorage.clear();
            sessionStorage.clear();
        }""")

        # Reload with clean localStorage (no watchlist)
        await page.reload(wait_until='networkidle', timeout=15000)

        # Wait a bit for async scripts
        await page.wait_for_timeout(3000)

        # Take screenshot
        await page.screenshot(path='portfolio_test_screenshot.png', full_page=True)

        # Check page content
        html = await page.content()
        text = await page.inner_text('body')

        # Check for fund rows
        fund_rows = await page.query_selector_all('#fund-list tr.fund-row')
        empty_message = '暂无自选基金' in text
        no_match_message = '未找到匹配基金' in text

        # Check if default 3 funds are present
        has_508056 = '508056' in text
        has_180201 = '180201' in text
        has_508099 = '508099' in text

        # Check stat count
        stat_count = await page.inner_text('#stat-count')
        list_count = await page.inner_text('#list-count')

        # Get localStorage watchlist
        watchlist_storage = await page.evaluate("""() => localStorage.getItem('watchlist')""")

        await browser.close()

        print("=" * 60)
        print("PORTFOLIO PAGE TEST RESULTS")
        print("=" * 60)

        print("\n--- Console Logs ---")
        for log in console_logs:
            try:
                print(log.encode('utf-8', errors='replace').decode('utf-8'))
            except Exception:
                print(log.encode('ascii', errors='replace').decode('ascii'))

        print("\n--- Console/Page Errors ---")
        if console_errors:
            for err in console_errors:
                try:
                    print(err.encode('utf-8', errors='replace').decode('utf-8'))
                except Exception:
                    print(err.encode('ascii', errors='replace').decode('ascii'))
        else:
            print("(none)")
        if page_errors:
            for err in page_errors:
                try:
                    print(f"[PAGE ERROR] {err}".encode('utf-8', errors='replace').decode('utf-8'))
                except Exception:
                    print(f"[PAGE ERROR] {err}".encode('ascii', errors='replace').decode('ascii'))

        print("\n--- Content Checks ---")
        print(f"Empty message ('暂无自选基金'): {empty_message}")
        print(f"No match message ('未找到匹配基金'): {no_match_message}")
        print(f"Fund rows found: {len(fund_rows)}")
        print(f"Has 508056: {has_508056}")
        print(f"Has 180201: {has_180201}")
        print(f"Has 508099: {has_508099}")
        print(f"Stat count text: '{stat_count}'")
        print(f"List count text: '{list_count}'")
        print(f"watchlist in localStorage: {watchlist_storage}")

        # JS syntax check: look for debounce definition issues
        debounce_error = any('debounce is not defined' in e.lower() for e in console_errors + page_errors)
        print(f"\n--- JS Error Checks ---")
        print(f"'debounce is not defined' error: {debounce_error}")

        # Final verdict
        print("\n--- VERDICT ---")
        if debounce_error:
            print("FAIL: debounce is not defined error found")
        elif empty_message and len(fund_rows) == 0:
            print("FAIL: Empty watchlist shows '暂无自选基金' instead of default 3 funds")
        elif len(fund_rows) == 3 and has_508056 and has_180201 and has_508099:
            print("PASS: Default 3 funds displayed correctly with no JS errors")
        else:
            print(f"UNCLEAR: {len(fund_rows)} rows, empty={empty_message}")

        print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test_portfolio())
