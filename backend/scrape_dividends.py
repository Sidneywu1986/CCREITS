import requests
import re
import json
from time import sleep

fund_codes = [
    '180101', '180102', '180103', '180105', '180106', '180201', '180202', '180203',
    '180301', '180302', '180303', '180305', '180306', '180401', '180402', '180501',
    '180502', '180601', '180602', '180603', '180605', '180606', '180607', '180701',
    '180801', '180901',
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008',
    '508009', '508010', '508011', '508012', '508015', '508016', '508017', '508018',
    '508019', '508021', '508022', '508026', '508027', '508028', '508029', '508031',
    '508033', '508036', '508039', '508048', '508050', '508055', '508056', '508058',
    '508060', '508066', '508068', '508069', '508077', '508078', '508080', '508082',
    '508084', '508085', '508086', '508087', '508088', '508089', '508090', '508091',
    '508092', '508096', '508097', '508098', '508099'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fundf10.eastmoney.com/'
}

results = {}
for i, code in enumerate(fund_codes):
    url = f'https://fundf10.eastmoney.com/fhsp_{code}.html'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        text = r.text
        # Pattern: 每份派现金0.XXXX元
        matches = re.findall(r'每份派现金(\d+\.\d+)元', text)
        if matches:
            # Most recent dividend
            div = float(matches[0])
            print(f'{code}: {matches[0]} (历史共{len(matches)}次分红)')
            results[code] = div
        else:
            print(f'{code}: 未找到分红数据')
            results[code] = None
    except Exception as e:
        print(f'{code}: 错误 - {e}')
        results[code] = None
    if (i + 1) % 20 == 0:
        print(f'进度: {i+1}/{len(fund_codes)}')
    sleep(0.3)

# Output the complete mapping
print('\n\n=== ANNUAL_DIVIDENDS 映射表 ===')
print('const ANNUAL_DIVIDENDS = {')

# Sort: SZSE first (180xxx), then SSE (508xxx)
szse = {k: v for k, v in results.items() if k.startswith('18')}
sse = {k: v for k, v in results.items() if k.startswith('50')}

print('    // 深交所REITs (每份分红,元)')
for k in sorted(szse.keys()):
    v = szse[k]
    val = f'{v:.4f}' if v else '0.0541'
    print(f"    '{k}': {val},", end='')
    if k == '180106':
        print('')
print()
print('    // 上交所REITs')
# Print in rows of 4
items = sorted(sse.items())
for i in range(0, len(items), 4):
    row = items[i:i+4]
    vals = ', '.join([f"'{k}': {v:.4f}" if v else f"'{k}': 0.0541" for k, v in row])
    print(f'    {vals},')
print('};')

print('\n\n=== JSON结果 ===')
print(json.dumps(results, ensure_ascii=False, indent=2))
