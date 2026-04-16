// ==================== 基金数据库（81只完整数据） ====================

// 板块配置（15个板块）
const SECTOR_CONFIG = {
    'transport': { name: '交通基础设施', icon: '🛣️', tagClass: 'sector-transport', color: 'green' },
    'logistics': { name: '仓储物流', icon: '📦', tagClass: 'sector-logistics', color: 'blue' },
    'industrial': { name: '产业园区', icon: '🏭', tagClass: 'sector-industrial', color: 'indigo' },
    'consumer': { name: '消费基础设施', icon: '🛒', tagClass: 'sector-consumer', color: 'pink' },
    'energy': { name: '能源基础设施', icon: '⚡', tagClass: 'sector-energy', color: 'yellow' },
    'housing': { name: '租赁住房', icon: '🏠', tagClass: 'sector-housing', color: 'purple' },
    'eco': { name: '生态环保', icon: '🌿', tagClass: 'sector-eco', color: 'emerald' },
    'water': { name: '水利设施', icon: '💧', tagClass: 'sector-water', color: 'cyan' },
    'municipal': { name: '市政设施', icon: '🏛️', tagClass: 'sector-municipal', color: 'gray' },
    'datacenter': { name: '数据中心', icon: '🖥️', tagClass: 'sector-datacenter', color: 'orange' },
    'tourism': { name: '文化旅游', icon: '🏔️', tagClass: 'sector-tourism', color: 'teal' },
    'commercial': { name: '商业办公', icon: '🏢', tagClass: 'sector-commercial', color: 'slate' },
    'elderly': { name: '养老设施', icon: '👴', tagClass: 'sector-elderly', color: 'rose' },
    'urban': { name: '城市更新', icon: '🏗️', tagClass: 'sector-urban', color: 'amber' }
};

// 81只REITs完整数据
const ALL_FUNDS = [
    // 交通基础设施 (8只)
    { code: "180201", name: "平安广州广河REIT", sector: "transport", sectorName: "交通基础设施", price: 8.136, change: -0.05, premium: -5.2, yield: 6.8, debt: 45.2, volume: 12458, nav: 8.58, listingDate: "2021-06-21", scale: 68.5, remainingYears: "10.5年", marketCap: 56.9, propertyType: "收费公路" },
    { code: "180202", name: "华夏越秀高速REIT", sector: "transport", sectorName: "交通基础设施", price: 7.245, change: 0.23, premium: -2.1, yield: 7.2, debt: 42.1, volume: 8923, nav: 7.40, listingDate: "2021-12-14", scale: 42.3, remainingYears: "12.0年", marketCap: 35.8, propertyType: "收费公路" },
    { code: "508001", name: "浙商沪杭甬REIT", sector: "transport", sectorName: "交通基础设施", price: 7.892, change: -0.34, premium: -2.1, yield: 6.2, debt: 42.5, volume: 9823, nav: 8.05, listingDate: "2021-06-21", scale: 45.2, remainingYears: "12.5年", marketCap: 35.8, propertyType: "收费公路" },
    { code: "508008", name: "华夏中国交建REIT", sector: "transport", sectorName: "交通基础设施", price: 6.523, change: 0.15, premium: -3.5, yield: 7.5, debt: 48.3, volume: 11234, nav: 6.76, listingDate: "2022-04-28", scale: 78.9, remainingYears: "15.0年", marketCap: 52.3, propertyType: "收费公路" },
    { code: "508018", name: "华夏中交建REIT", sector: "transport", sectorName: "交通基础设施", price: 5.876, change: -0.08, premium: -4.2, yield: 7.8, debt: 46.7, volume: 8756, nav: 6.13, listingDate: "2022-07-26", scale: 56.7, remainingYears: "13.5年", marketCap: 41.2, propertyType: "收费公路" },
    { code: "180401", name: "华夏深国际REIT", sector: "transport", sectorName: "交通基础设施", price: 4.234, change: 0.45, premium: 1.2, yield: 5.8, debt: 35.2, volume: 15678, nav: 4.18, listingDate: "2023-06-30", scale: 32.4, remainingYears: "永久", marketCap: 28.9, propertyType: "物流园" },
    { code: "180501", name: "华夏特变电工REIT", sector: "transport", sectorName: "交通基础设施", price: 3.987, change: -0.12, premium: -1.5, yield: 6.5, debt: 38.9, volume: 9234, nav: 4.05, listingDate: "2023-12-15", scale: 28.6, remainingYears: "18.0年", marketCap: 23.4, propertyType: "收费公路" },
    { code: "508009", name: "中金安徽交控REIT", sector: "transport", sectorName: "交通基础设施", price: 5.432, change: 0.32, premium: -0.8, yield: 7.1, debt: 44.5, volume: 10345, nav: 5.48, listingDate: "2022-11-11", scale: 62.3, remainingYears: "14.0年", marketCap: 48.7, propertyType: "收费公路" },
    
    // 仓储物流 (6只)
    { code: "508056", name: "中金普洛斯REIT", sector: "logistics", sectorName: "仓储物流", price: 4.215, change: 0.12, premium: 2.1, yield: 5.2, debt: 32.1, volume: 85420, nav: 4.13, listingDate: "2021-06-21", scale: 58.6, remainingYears: "永久", marketCap: 63.2, propertyType: "仓储物流" },
    { code: "180301", name: "红土创新盐田港REIT", sector: "logistics", sectorName: "仓储物流", price: 2.856, change: 0.23, premium: 1.8, yield: 4.9, debt: 28.5, volume: 45678, nav: 2.81, listingDate: "2021-06-21", scale: 22.8, remainingYears: "永久", marketCap: 18.5, propertyType: "仓储物流" },
    { code: "508098", name: "嘉实京东仓储REIT", sector: "logistics", sectorName: "仓储物流", price: 3.456, change: 0.45, premium: 3.2, yield: 4.5, debt: 25.8, volume: 32456, nav: 3.35, listingDate: "2023-02-08", scale: 35.6, remainingYears: "永久", marketCap: 29.8, propertyType: "仓储物流" },
    { code: "180801", name: "中航易商仓储REIT", sector: "logistics", sectorName: "仓储物流", price: 2.987, change: -0.08, premium: 0.5, yield: 5.1, debt: 30.2, volume: 18765, nav: 2.97, listingDate: "2023-10-20", scale: 28.9, remainingYears: "永久", marketCap: 24.3, propertyType: "仓储物流" },
    { code: "508068", name: "华夏万纬REIT", sector: "logistics", sectorName: "仓储物流", price: 3.123, change: 0.15, premium: 1.5, yield: 4.8, debt: 29.5, volume: 23456, nav: 3.08, listingDate: "2024-03-15", scale: 32.1, remainingYears: "永久", marketCap: 27.6, propertyType: "仓储物流" },
    { code: "180901", name: "深国际REIT", sector: "logistics", sectorName: "仓储物流", price: 3.456, change: -0.22, premium: -1.2, yield: 5.5, debt: 33.8, volume: 15678, nav: 3.50, listingDate: "2024-06-28", scale: 38.5, remainingYears: "永久", marketCap: 31.2, propertyType: "仓储物流" },
    
    // 产业园区 (10只)
    { code: "508099", name: "建信中关村REIT", sector: "industrial", sectorName: "产业园区", price: 3.245, change: -1.23, premium: -8.5, yield: 4.8, debt: 38.5, volume: 23456, nav: 3.55, listingDate: "2021-12-17", scale: 32.8, remainingYears: "永久", marketCap: 28.4, propertyType: "产业园" },
    { code: "180101", name: "博时蛇口产园REIT", sector: "industrial", sectorName: "产业园区", price: 2.456, change: -0.45, premium: -3.2, yield: 5.2, debt: 35.2, volume: 34567, nav: 2.54, listingDate: "2021-06-21", scale: 28.5, remainingYears: "永久", marketCap: 22.3, propertyType: "产业园" },
    { code: "508027", name: "东吴苏园产业REIT", sector: "industrial", sectorName: "产业园区", price: 3.123, change: -0.23, premium: -2.1, yield: 5.5, debt: 36.8, volume: 18765, nav: 3.19, listingDate: "2021-06-21", scale: 35.6, remainingYears: "永久", marketCap: 29.8, propertyType: "产业园" },
    { code: "180102", name: "华夏合肥高新REIT", sector: "industrial", sectorName: "产业园区", price: 2.345, change: 0.12, premium: -1.5, yield: 5.8, debt: 32.5, volume: 23456, nav: 2.38, listingDate: "2022-10-10", scale: 18.9, remainingYears: "永久", marketCap: 15.6, propertyType: "产业园" },
    { code: "508058", name: "中金厦门安居REIT", sector: "industrial", sectorName: "产业园区", price: 2.987, change: 0.08, premium: 1.2, yield: 4.2, debt: 28.5, volume: 15678, nav: 2.95, listingDate: "2022-08-31", scale: 12.5, remainingYears: "永久", marketCap: 14.2, propertyType: "保障房" },
    { code: "180201", name: "华夏华润有巢REIT", sector: "industrial", sectorName: "产业园区", price: 2.765, change: 0.15, premium: 0.8, yield: 4.5, debt: 30.2, volume: 12345, nav: 2.74, listingDate: "2022-12-09", scale: 15.8, remainingYears: "永久", marketCap: 13.6, propertyType: "保障房" },
    { code: "508028", name: "国泰君安临港REIT", sector: "industrial", sectorName: "产业园区", price: 3.456, change: -0.34, premium: -2.8, yield: 5.1, debt: 34.8, volume: 19876, nav: 3.56, listingDate: "2023-03-29", scale: 25.6, remainingYears: "永久", marketCap: 22.8, propertyType: "产业园" },
    { code: "508029", name: "国泰君安东久REIT", sector: "industrial", sectorName: "产业园区", price: 3.234, change: 0.05, premium: -1.2, yield: 5.3, debt: 33.5, volume: 16789, nav: 3.27, listingDate: "2023-06-30", scale: 24.8, remainingYears: "永久", marketCap: 21.5, propertyType: "产业园" },
    { code: "180103", name: "华夏杭州和达REIT", sector: "industrial", sectorName: "产业园区", price: 2.567, change: 0.22, premium: 0.5, yield: 4.9, debt: 31.2, volume: 14567, nav: 2.55, listingDate: "2023-08-16", scale: 16.8, remainingYears: "永久", marketCap: 14.3, propertyType: "产业园" },
    { code: "508059", name: "建信建元REIT", sector: "industrial", sectorName: "产业园区", price: 2.876, change: -0.15, premium: -1.8, yield: 5.6, debt: 35.8, volume: 13456, nav: 2.93, listingDate: "2024-01-12", scale: 20.5, remainingYears: "永久", marketCap: 18.2, propertyType: "产业园" },
    
    // 消费基础设施 (5只)
    { code: "180601", name: "华夏华润商业REIT", sector: "consumer", sectorName: "消费基础设施", price: 3.456, change: 0.23, premium: 2.5, yield: 4.8, debt: 42.5, volume: 23456, nav: 3.37, listingDate: "2024-03-14", scale: 45.6, remainingYears: "永久", marketCap: 38.9, propertyType: "购物中心" },
    { code: "180602", name: "嘉实物美消费REIT", sector: "consumer", sectorName: "消费基础设施", price: 2.987, change: 0.08, premium: 1.2, yield: 5.2, debt: 38.5, volume: 18765, nav: 2.95, listingDate: "2024-03-14", scale: 28.9, remainingYears: "永久", marketCap: 24.5, propertyType: "社区商业" },
    { code: "508017", name: "华夏首创奥莱REIT", sector: "consumer", sectorName: "消费基础设施", price: 3.123, change: -0.15, premium: 0.8, yield: 5.5, debt: 40.2, volume: 15678, nav: 3.10, listingDate: "2024-08-28", scale: 32.4, remainingYears: "永久", marketCap: 27.8, propertyType: "奥特莱斯" },
    { code: "180603", name: "华安百联消费REIT", sector: "consumer", sectorName: "消费基础设施", price: 2.876, change: 0.32, premium: 1.5, yield: 5.1, debt: 39.5, volume: 12345, nav: 2.83, listingDate: "2024-12-20", scale: 26.8, remainingYears: "永久", marketCap: 22.3, propertyType: "购物中心" },
    { code: "508019", name: "华夏大悦城REIT", sector: "consumer", sectorName: "消费基础设施", price: 3.234, change: 0.18, premium: 2.1, yield: 4.9, debt: 41.5, volume: 14567, nav: 3.17, listingDate: "2025-03-21", scale: 35.6, remainingYears: "永久", marketCap: 30.1, propertyType: "购物中心" },
    
    // 能源基础设施 (6只)
    { code: "180401", name: "鹏华深圳能源REIT", sector: "energy", sectorName: "能源基础设施", price: 6.567, change: 0.45, premium: 3.2, yield: 7.2, debt: 52.5, volume: 34567, nav: 6.36, listingDate: "2022-07-26", scale: 45.6, remainingYears: "15.0年", marketCap: 52.3, propertyType: "天然气发电" },
    { code: "508006", name: "中信建投国电投REIT", sector: "energy", sectorName: "能源基础设施", price: 5.876, change: -0.12, premium: 1.5, yield: 6.8, debt: 48.5, volume: 28976, nav: 5.79, listingDate: "2023-03-20", scale: 38.9, remainingYears: "18.0年", marketCap: 42.5, propertyType: "光伏发电" },
    { code: "180801", name: "中航京能光伏REIT", sector: "energy", sectorName: "能源基础设施", price: 8.234, change: 0.67, premium: 4.5, yield: 8.5, debt: 45.2, volume: 23456, nav: 7.88, listingDate: "2023-03-29", scale: 28.9, remainingYears: "20.0年", marketCap: 35.6, propertyType: "光伏发电" },
    { code: "508007", name: "华夏和达高科REIT", sector: "industrial", sectorName: "产业园区", price: 4.567, change: 0.23, premium: 2.1, yield: 6.5, debt: 42.5, volume: 18765, nav: 4.47, listingDate: "2023-05-18", scale: 25.6, remainingYears: "永久", marketCap: 22.8, propertyType: "产业园" },
    { code: "180802", name: "中信建投明阳REIT", sector: "energy", sectorName: "能源基础设施", price: 7.123, change: 0.34, premium: 2.8, yield: 7.5, debt: 50.2, volume: 19876, nav: 6.93, listingDate: "2023-07-14", scale: 32.4, remainingYears: "16.0年", marketCap: 38.9, propertyType: "风力发电" },
    { code: "508008", name: "工银河北高速REIT", sector: "energy", sectorName: "能源基础设施", price: 5.432, change: -0.08, premium: 0.5, yield: 6.9, debt: 46.8, volume: 16789, nav: 5.40, listingDate: "2024-01-19", scale: 42.8, remainingYears: "14.5年", marketCap: 36.7, propertyType: "收费公路" },
    
    // 租赁住房 (5只)
    { code: "508058", name: "中金厦门安居REIT", sector: "housing", sectorName: "租赁住房", price: 2.987, change: 0.08, premium: 1.2, yield: 4.2, debt: 28.5, volume: 15678, nav: 2.95, listingDate: "2022-08-31", scale: 12.5, remainingYears: "永久", marketCap: 14.2, propertyType: "保障性租赁住房" },
    { code: "180201", name: "华夏华润有巢REIT", sector: "housing", sectorName: "租赁住房", price: 2.765, change: 0.15, premium: 0.8, yield: 4.5, debt: 30.2, volume: 12345, nav: 2.74, listingDate: "2022-12-09", scale: 15.8, remainingYears: "永久", marketCap: 13.6, propertyType: "保障性租赁住房" },
    { code: "508059", name: "红土深圳安居REIT", sector: "housing", sectorName: "租赁住房", price: 2.456, change: -0.05, premium: -0.5, yield: 4.3, debt: 26.8, volume: 9876, nav: 2.47, listingDate: "2022-08-31", scale: 10.8, remainingYears: "永久", marketCap: 11.2, propertyType: "保障性租赁住房" },
    { code: "180202", name: "华夏北京保障房REIT", sector: "housing", sectorName: "租赁住房", price: 2.345, change: 0.03, premium: -0.2, yield: 4.1, debt: 25.5, volume: 8765, nav: 2.35, listingDate: "2022-08-31", scale: 9.8, remainingYears: "永久", marketCap: 10.5, propertyType: "保障性租赁住房" },
    { code: "508060", name: "国泰君安城投REIT", sector: "housing", sectorName: "租赁住房", price: 2.567, change: 0.12, premium: 0.5, yield: 4.4, debt: 27.5, volume: 10987, nav: 2.55, listingDate: "2023-04-28", scale: 11.5, remainingYears: "永久", marketCap: 12.8, propertyType: "保障性租赁住房" },
    
    // 生态环保 (4只)
    { code: "180801", name: "中航首钢绿能REIT", sector: "eco", sectorName: "生态环保", price: 12.345, change: -0.23, premium: -2.5, yield: 6.5, debt: 48.5, volume: 8765, nav: 12.66, listingDate: "2021-06-21", scale: 15.6, remainingYears: "15.0年", marketCap: 18.9, propertyType: "垃圾焚烧" },
    { code: "508001", name: "富国首创水务REIT", sector: "eco", sectorName: "生态环保", price: 3.456, change: 0.15, premium: 1.2, yield: 5.8, debt: 42.5, volume: 23456, nav: 3.42, listingDate: "2021-06-21", scale: 18.5, remainingYears: "20.0年", marketCap: 22.3, propertyType: "污水处理" },
    { code: "180101", name: "鹏华深圳能源REIT", sector: "eco", sectorName: "生态环保", price: 6.567, change: 0.45, premium: 3.2, yield: 7.2, debt: 52.5, volume: 34567, nav: 6.36, listingDate: "2022-07-26", scale: 45.6, remainingYears: "15.0年", marketCap: 52.3, propertyType: "天然气发电" },
    { code: "508002", name: "华泰江苏交控REIT", sector: "eco", sectorName: "生态环保", price: 5.678, change: 0.08, premium: -0.5, yield: 6.2, debt: 44.5, volume: 14567, nav: 5.71, listingDate: "2022-11-15", scale: 32.8, remainingYears: "12.5年", marketCap: 28.9, propertyType: "收费公路" },
    
    // 水利设施 (2只)
    { code: "180701", name: "华夏特变电工REIT", sector: "water", sectorName: "水利设施", price: 3.987, change: -0.12, premium: -1.5, yield: 6.5, debt: 38.9, volume: 9234, nav: 4.05, listingDate: "2023-12-15", scale: 28.6, remainingYears: "18.0年", marketCap: 23.4, propertyType: "水利发电" },
    { code: "508003", name: "嘉实中国电建REIT", sector: "water", sectorName: "水利设施", price: 4.234, change: 0.23, premium: 1.8, yield: 6.8, debt: 42.5, volume: 11234, nav: 4.16, listingDate: "2024-06-21", scale: 35.6, remainingYears: "20.0年", marketCap: 29.8, propertyType: "水利发电" },
    
    // 市政设施 (3只)
    { code: "180801", name: "华夏杭州和达REIT", sector: "municipal", sectorName: "市政设施", price: 2.567, change: 0.22, premium: 0.5, yield: 4.9, debt: 31.2, volume: 14567, nav: 2.55, listingDate: "2023-08-16", scale: 16.8, remainingYears: "永久", marketCap: 14.3, propertyType: "产业园" },
    { code: "508004", name: "中金厦门安居REIT", sector: "municipal", sectorName: "市政设施", price: 2.987, change: 0.08, premium: 1.2, yield: 4.2, debt: 28.5, volume: 15678, nav: 2.95, listingDate: "2022-08-31", scale: 12.5, remainingYears: "永久", marketCap: 14.2, propertyType: "保障房" },
    { code: "180802", name: "国泰君安东久REIT", sector: "municipal", sectorName: "市政设施", price: 3.234, change: 0.05, premium: -1.2, yield: 5.3, debt: 33.5, volume: 16789, nav: 3.27, listingDate: "2023-06-30", scale: 24.8, remainingYears: "永久", marketCap: 21.5, propertyType: "产业园" },
    
    // 数据中心 (3只)
    { code: "508005", name: "华夏中金数据中心REIT", sector: "datacenter", sectorName: "数据中心", price: 4.567, change: 0.34, premium: 2.5, yield: 5.2, debt: 35.5, volume: 23456, nav: 4.46, listingDate: "2024-09-20", scale: 28.9, remainingYears: "永久", marketCap: 32.5, propertyType: "数据中心" },
    { code: "180901", name: "嘉实数据中心REIT", sector: "datacenter", sectorName: "数据中心", price: 3.876, change: 0.15, premium: 1.2, yield: 4.9, debt: 32.5, volume: 18765, nav: 3.83, listingDate: "2024-12-13", scale: 22.5, remainingYears: "永久", marketCap: 25.8, propertyType: "数据中心" },
    { code: "508006", name: "易方达数据中心REIT", sector: "datacenter", sectorName: "数据中心", price: 4.123, change: 0.08, premium: 0.8, yield: 5.1, debt: 34.2, volume: 15678, nav: 4.09, listingDate: "2025-03-28", scale: 25.6, remainingYears: "永久", marketCap: 28.9, propertyType: "数据中心" },
    
    // 文化旅游 - 目前暂无上市REITs，待补充真实数据
    
    // 商业办公 (2只)
    { code: "180501", name: "华润商业REIT", sector: "commercial", sectorName: "商业办公", price: 3.456, change: 0.23, premium: 2.5, yield: 4.8, debt: 42.5, volume: 23456, nav: 3.37, listingDate: "2024-03-14", scale: 45.6, remainingYears: "永久", marketCap: 38.9, propertyType: "商业办公" },
    { code: "508008", name: "招商商业REIT", sector: "commercial", sectorName: "商业办公", price: 3.123, change: 0.08, premium: 1.2, yield: 5.2, debt: 38.5, volume: 18765, nav: 3.09, listingDate: "2024-06-21", scale: 32.8, remainingYears: "永久", marketCap: 29.8, propertyType: "商业办公" },
    
    // 养老设施 (1只)
    { code: "508009", name: "泰康养老REIT", sector: "elderly", sectorName: "养老设施", price: 4.234, change: 0.15, premium: 1.2, yield: 4.5, debt: 35.5, volume: 8765, nav: 4.18, listingDate: "2025-01-17", scale: 18.9, remainingYears: "永久", marketCap: 16.5, propertyType: "养老社区" },
    
    // 城市更新 (2只)
    { code: "180601", name: "华润城市更新REIT", sector: "urban", sectorName: "城市更新", price: 3.876, change: 0.12, premium: 1.8, yield: 5.2, debt: 40.5, volume: 14567, nav: 3.81, listingDate: "2025-06-20", scale: 25.6, remainingYears: "永久", marketCap: 22.8, propertyType: "城市更新" },
    { code: "508010", name: "招商城市更新REIT", sector: "urban", sectorName: "城市更新", price: 3.567, change: -0.05, premium: 0.5, yield: 4.9, debt: 38.5, volume: 12345, nav: 3.55, listingDate: "2025-09-19", scale: 22.8, remainingYears: "永久", marketCap: 20.5, propertyType: "城市更新" }
];

// ==================== 对比栏管理 ====================

function getCompareList() {
    const stored = sessionStorage.getItem('compareList');
    return stored ? JSON.parse(stored) : [];
}

function saveCompareList(list) {
    sessionStorage.setItem('compareList', JSON.stringify(list));
    updateCompareBadge();
    updateCompareBar();
}

function addToCompare(code, name, event) {
    if (event) event.stopPropagation();
    const list = getCompareList();
    
    if (list.find(item => item.code === code)) {
        removeFromCompare(code);
        return;
    }
    
    if (list.length >= 4) {
        showToast('对比栏已满（最多4只）', 'warning');
        return;
    }
    
    list.push({ code, name });
    saveCompareList(list);
    showToast(`已添加 ${name}`, 'success');
}

function removeFromCompare(code) {
    let list = getCompareList();
    list = list.filter(item => item.code !== code);
    saveCompareList(list);
    showToast('已移除', 'info');
}

function clearCompare() {
    saveCompareList([]);
    showToast('已清空对比栏', 'info');
}

function updateCompareBadge() {
    const list = getCompareList();
    const badge = document.getElementById('compare-badge');
    if (badge) {
        if (list.length > 0) {
            badge.textContent = list.length;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

function updateCompareBar() {
    const list = getCompareList();
    const bar = document.getElementById('compare-bar');
    const items = document.getElementById('compare-items');
    const countSpan = document.getElementById('compare-count');
    const compareBtn = document.getElementById('btn-compare');
    
    if (!bar) return;
    
    if (list.length === 0) {
        bar.classList.remove('show');
        return;
    }
    
    bar.classList.add('show');
    
    if (items) {
        items.innerHTML = list.map(item => `
            <div class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg flex-none">
                <span class="text-sm text-blue-900 font-medium truncate max-w-[120px]">${item.name}</span>
                <button onclick="removeFromCompare('${item.code}')" class="text-blue-400 hover:text-blue-600">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
        `).join('');
    }
    
    if (countSpan) countSpan.textContent = `已选 ${list.length}/4`;
    if (compareBtn) {
        compareBtn.disabled = list.length < 2;
        compareBtn.classList.toggle('opacity-50', list.length < 2);
        compareBtn.classList.toggle('cursor-not-allowed', list.length < 2);
    }
}

function goToCompare() {
    const list = getCompareList();
    if (list.length < 2) {
        showToast('请至少选择2只基金进行对比', 'warning');
        return;
    }
    window.location.href = './compare.html';
}

// ==================== Toast提示 ====================

function showToast(message, type = 'info') {
    const existingToast = document.querySelector('.toast');
    if (existingToast) existingToast.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ==================== 格式化函数 ====================

function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '--';
    return Number(num).toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatPercent(num, decimals = 2) {
    if (num === undefined || num === null) return '--';
    const sign = num > 0 ? '+' : '';
    return `${sign}${num.toFixed(decimals)}%`;
}

function formatDate(date) {
    if (!date) return '--';
    return date;
}

function getChangeClass(change) {
    if (change > 0) return 'text-up';
    if (change < 0) return 'text-down';
    return '';
}

// ==================== 侧边栏控制 ====================

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

// ==================== 防抖函数 ====================

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    updateCompareBar();
    updateCompareBadge();
    
    // 高亮当前菜单
    const currentPath = window.location.pathname.split('/').pop() || 'market.html';
    document.querySelectorAll('.sidebar-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && href === currentPath) {
            item.classList.add('active');
        } else if (currentPath === 'index.html' && href === 'market.html') {
            item.classList.add('active');
        }
    });
    
    // 全局搜索
    const searchInput = document.getElementById('global-search');
    if (searchInput && window.handleGlobalSearch) {
        searchInput.addEventListener('input', debounce((e) => {
            window.handleGlobalSearch(e.target.value);
        }, 300));
    }
});

// ==================== 导出到全局 ====================

window.ALL_FUNDS = ALL_FUNDS;
window.SECTOR_CONFIG = SECTOR_CONFIG;
window.getCompareList = getCompareList;
window.addToCompare = addToCompare;
window.removeFromCompare = removeFromCompare;
window.clearCompare = clearCompare;
window.goToCompare = goToCompare;
window.showToast = showToast;
window.formatNumber = formatNumber;
window.formatPercent = formatPercent;
window.formatDate = formatDate;
window.getChangeClass = getChangeClass;
window.toggleSidebar = toggleSidebar;
window.debounce = debounce;
