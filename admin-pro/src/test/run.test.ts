// 简单的API测试运行器
import { testAPIs } from './api.test';

async function runTests() {
  console.log('🚀 启动API连接测试...');
  console.log('API基础URL:', '/api');
  console.log('目标后端:', 'http://localhost:5074');
  console.log('测试时间:', new Date().toLocaleString('zh-CN'));

  try {
    const success = await testAPIs();

    if (success) {
      console.log('\n🎉 所有API测试通过！');
      console.log('✅ 后端连接正常');
      console.log('✅ 数据格式正确');
      console.log('✅ 缓存功能正常');
    } else {
      console.log('\n❌ API测试失败！');
      console.log('⚠️ 请检查后端服务是否运行');
      console.log('⚠️ 检查API地址配置');
      console.log('⚠️ 检查网络连接');
    }

    return success;
  } catch (error) {
    console.error('\n💥 测试运行异常:', error);
    return false;
  }
}

// 直接运行测试
runTests().then(success => {
  process.exit(success ? 0 : 1);
});