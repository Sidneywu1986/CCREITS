import requests
import re

url = 'https://fundf10.eastmoney.com/fhsp_508000.html'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fundf10.eastmoney.com/'
}
r = requests.get(url, headers=headers, timeout=10)
text = r.text

# Find dividend data in the page
# Look for the table data
idx = text.find('分红')
print('First 分红 at:', idx)
if idx > -1:
    print(text[idx:idx+500])

# Try to find any API calls
api_matches = re.findall(r'["\']([^"\']*fhsp[^"\']*)["\']', text)
print('\nAPI matches:')
for m in api_matches[:10]:
    print(' ', m)

# Check for embedded data
json_data = re.findall(r'var\s+\w+\s*=\s*(\{.*?\});', text, re.DOTALL)
print('\nJS vars:', len(json_data))
