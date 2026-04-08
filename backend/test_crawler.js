const axios = require('axios');
const cheerio = require('cheerio');

async function testSSE() {
    console.log('=== 测试上交所公告页面 ===');
    try {
        const url = 'https://www.sse.com.cn/disclosure/fund/reits/';
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout: 20000
        });
        
        const html = response.data;
        console.log('HTML长度:', html.length);
        
        // 检查关键元素
        console.log('包含 table-list:', html.includes('table-list'));
        console.log('包含 sse_list_t1:', html.includes('sse_list_t1'));
        console.log('包含 article-list:', html.includes('article-list'));
        
        const $ = cheerio.load(html);
        
        // 尝试不同的选择器
        const selectors = [
            '.table-list tbody tr',
            '.sse_list_t1 tbody tr',
            '.article-list .item',
            '.news-list li',
            '.table-data tbody tr',
            'table tbody tr',
            '.list-item',
            'ul li a'
        ];
        
        for (const sel of selectors) {
            const count = $(sel).length;
            if (count > 0) {
                console.log(`选择器 "${sel}": ${count} 个元素`);
                // 输出第一个元素的内容预览
                const first = $(sel).first();
                console.log('  内容预览:', first.text().trim().substring(0, 100));
            }
        }
        
    } catch (e) {
        console.error('错误:', e.message);
    }
}

async function testSZSE() {
    console.log('\n=== 测试深交所公告页面 ===');
    try {
        const url = 'https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html';
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout: 20000
        });
        
        const html = response.data;
        console.log('HTML长度:', html.length);
        
        const $ = cheerio.load(html);
        
        const selectors = [
            '.news-list li',
            '.article-item',
            '.table-data tbody tr',
            'table tbody tr',
            'ul li a'
        ];
        
        for (const sel of selectors) {
            const count = $(sel).length;
            if (count > 0) {
                console.log(`选择器 "${sel}": ${count} 个元素`);
                const first = $(sel).first();
                console.log('  内容预览:', first.text().trim().substring(0, 100));
            }
        }
        
    } catch (e) {
        console.error('错误:', e.message);
    }
}

testSSE().then(() => testSZSE());
