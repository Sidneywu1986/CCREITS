const XLSX = require('xlsx');
const { db } = require('./database/db');

// 读取Excel文件
const workbook = XLSX.readFile('./reits_data.xlsx');
const sheetName = workbook.SheetNames[0];
const worksheet = workbook.Sheets[sheetName];
const data = XLSX.utils.sheet_to_json(worksheet);

console.log('读取到 ' + data.length + ' 条数据');
console.log('列名:', Object.keys(data[0] || {}));
console.log('第一条数据:', data[0]);

// 板块映射
const sectorMap = {
  '交通基础设施': 'transport',
  '仓储物流': 'logistics',
  '产业园区': 'industrial',
  '消费基础设施': 'consumer',
  '能源基础设施': 'energy',
  '租赁住房': 'housing',
  '生态环保': 'eco',
  '水利设施': 'water',
  '市政设施': 'municipal',
  '数据中心': 'datacenter',
  '商业办公': 'commercial',
  '养老设施': 'elderly',
  '文化旅游': 'tourism',
  '城市更新': 'urban'
};

// 更新数据库
let updated = 0;
let inserted = 0;
let errors = 0;

data.forEach((row, index) => {
  try {
    const code = String(row['代码'] || '').trim();
    const name = String(row['基金名称'] || '').trim();
    const sectorName = String(row['板块类型'] || '').trim();
    
    if (!code) {
      console.log(`第${index+1}行: 跳过无效行 (无代码)`);
      return;
    }
    
    const sector = sectorMap[sectorName] || 'other';
    
    // 先检查是否存在
    db.get('SELECT code FROM funds WHERE code = ?', [code], (err, existing) => {
      if (err) {
        console.error(`查询 ${code} 失败:`, err);
        errors++;
        return;
      }
      
      if (existing) {
        // 更新
        db.run(`UPDATE funds SET name = ?, sector = ?, sector_name = ?, updated_at = datetime('now') WHERE code = ?`,
          [name, sector, sectorName, code], (err) => {
            if (err) {
              console.error(`更新 ${code} 失败:`, err);
              errors++;
            } else {
              updated++;
              console.log(`✅ 更新 [${code}] ${name} -> ${sectorName} (${sector})`);
            }
          });
      } else {
        // 插入
        db.run(`INSERT INTO funds (code, name, sector, sector_name, status) VALUES (?, ?, ?, ?, 'listed')`,
          [code, name, sector, sectorName], (err) => {
            if (err) {
              console.error(`插入 ${code} 失败:`, err);
              errors++;
            } else {
              inserted++;
              console.log(`✅ 插入 [${code}] ${name} -> ${sectorName} (${sector})`);
            }
          });
      }
    });
  } catch (e) {
    console.error(`第${index+1}行处理出错:`, e);
    errors++;
  }
});

setTimeout(() => {
  console.log(`\n=================================`);
  console.log(`完成: 更新 ${updated} 条, 插入 ${inserted} 条, 错误 ${errors} 条`);
  console.log(`=================================`);
  process.exit(0);
}, 3000);
