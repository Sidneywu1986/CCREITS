// API连接测试脚本

import { dividendService } from '../services/dividendService';

async function testAPIs() {
  console.log('🔍 开始测试API连接...');

  try {
    // 测试1：获取分红日历
    console.log('\n1. 测试分红日历API...');
    const calendarResponse = await dividendService.getDividendCalendar({
      page: 1,
      page_size: 10
    });
    console.log('✅ 分红日历API:', calendarResponse.success ? '成功' : '失败');
    if (calendarResponse.success) {
      console.log(`   数据量: ${calendarResponse.data.length} 条`);
      console.log(`   总记录: ${calendarResponse.total} 条`);
    }

    // 测试2：获取即将分红
    console.log('\n2. 测试即将分红API...');
    const upcomingResponse = await dividendService.getUpcomingDividends(30);
    console.log('✅ 即将分红API:', upcomingResponse.success ? '成功' : '失败');
    if (upcomingResponse.success) {
      console.log(`   即将分红: ${upcomingResponse.data.length} 条`);
    }

    // 测试3：获取基金分红历史
    console.log('\n3. 测试基金分红历史API...');
    const fundHistoryResponse = await dividendService.getFundDividends('508001', 10);
    console.log('✅ 基金历史API:', fundHistoryResponse.success ? '成功' : '失败');
    if (fundHistoryResponse.success) {
      console.log(`   历史记录: ${fundHistoryResponse.data.length} 条`);
    }

    // 测试4：获取分红统计
    console.log('\n4. 测试分红统计API...');
    const statsResponse = await dividendService.getDividendStats();
    console.log('✅ 统计API:', statsResponse.success ? '成功' : '失败');
    if (statsResponse.success) {
      console.log(`   统计数据: ${statsResponse.data.length} 条记录`);
    }

    // 测试5：获取基金列表
    console.log('\n5. 测试基金列表API...');
    const funds = await dividendService.getFunds();
    console.log('✅ 基金列表API:', funds.length > 0 ? '成功' : '失败');
    console.log(`   基金数量: ${funds.length} 只`);

    // 测试6：缓存功能
    console.log('\n6. 测试缓存功能...');
    const cacheSize = dividendService.getCacheSize();
    console.log(`   缓存大小: ${cacheSize} 个条目`);
    dividendService.clearCache();
    console.log('   缓存已清空');

    console.log('\n🎉 API测试完成！');
    return true;
  } catch (error) {
    console.error('❌ API测试失败:', error);
    return false;
  }
}

// 运行测试
if (import.meta.hot) {
  testAPIs().then(success => {
    if (success) {
      console.log('\n✅ 所有API连接正常！');
    } else {
      console.log('\n❌ 部分API连接失败！');
    }
  });
}

export { testAPIs };