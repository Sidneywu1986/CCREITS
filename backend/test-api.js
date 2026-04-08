const http = require('http');

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/funds',
  method: 'GET'
};

const req = http.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => {
    try {
      const json = JSON.parse(data);
      console.log('API状态:', json.success);
      console.log('API返回基金数量:', json.count);
      console.log('\n第一条数据示例:');
      const fund = json.data[0];
      console.log('  代码:', fund.code);
      console.log('  名称:', fund.name);
      console.log('  价格:', fund.price);
      console.log('  change:', fund.change);
      console.log('  changePercent:', fund.changePercent);
      console.log('  change_percent:', fund.change_percent);
      console.log('  板块:', fund.sector, fund.sectorName);
      console.log('  成交量:', fund.volume);
      console.log('  更新时间:', fund.quoteTime);
    } catch (e) {
      console.error('解析失败:', e.message);
    }
    process.exit(0);
  });
});

req.on('error', (e) => {
  console.error('请求失败:', e.message);
  process.exit(1);
});

req.end();
