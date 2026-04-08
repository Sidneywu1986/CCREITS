const axios = require('axios');
const iconv = require('iconv-lite');

async function testSina() {
    const codes = ['sh508001', 'sh508018', 'sz180101'];
    const url = `https://hq.sinajs.cn/list=${codes.join(',')}`;
    
    console.log('测试新浪API:', url);
    
    try {
        const response = await axios.get(url, {
            responseType: 'arraybuffer',
            timeout: 10000,
            headers: {
                'Referer': 'https://finance.sina.com.cn'
            }
        });
        
        const data = iconv.decode(response.data, 'gb2312');
        console.log('\n原始数据:');
        console.log(data);
        
        // 解析数据
        console.log('\n解析结果:');
        for (const code of codes) {
            const match = data.match(new RegExp(`var hq_str_${code}="([^"]*)"`));
            if (match && match[1]) {
                const parts = match[1].split(',');
                console.log(`\n${code}:`);
                console.log('  名称:', parts[0]);
                console.log('  开盘:', parts[1]);
                console.log('  昨收:', parts[2]);
                console.log('  当前:', parts[3]);
                console.log('  最高:', parts[4]);
                console.log('  最低:', parts[5]);
                console.log('  成交量:', parts[8]);
                console.log('  原始数据长度:', parts.length);
            } else {
                console.log(`${code}: 无数据`);
            }
        }
    } catch (error) {
        console.error('请求失败:', error.message);
    }
    
    process.exit(0);
}

testSina();
