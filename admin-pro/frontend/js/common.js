// 板块配置(2个板块) - 已移除文旅和城市更新
const SECTOR_CONFIG = {
    'transport': { name: '交通基础设施', icon: '🛣', tagClass: 'sector-transport', color: 'green' },
    'logistics': { name: '仓储物流', icon: '📦', tagClass: 'sector-logistics', color: 'blue' },
    'industrial': { name: '产业园区', icon: '🏭', tagClass: 'sector-industrial', color: 'indigo' },
    'consumer': { name: '消费基础设施', icon: '🛒', tagClass: 'sector-consumer', color: 'pink' },
    'energy': { name: '能源基础设施', icon: '⚡', tagClass: 'sector-energy', color: 'yellow' },
    'housing': { name: '租赁住房', icon: '🏠', tagClass: 'sector-housing', color: 'purple' },
    'eco': { name: '生态环保', icon: '🌿', tagClass: 'sector-eco', color: 'emerald' },
    'water': { name: '水利设施', icon: '💧', tagClass: 'sector-water', color: 'cyan' },
    'municipal': { name: '市政设施', icon: '🏛', tagClass: 'sector-municipal', color: 'gray' },
    'datacenter': { name: '数据中心', icon: '🖥', tagClass: 'sector-datacenter', color: 'orange' },
    'commercial': { name: '商业办公', icon: '🏢', tagClass: 'sector-commercial', color: 'slate' },
    'elderly': { name: '养老设施', icon: '👴', tagClass: 'sector-elderly', color: 'rose' },
    'other': { name: '其他', icon: '📌', tagClass: 'sector-other', color: 'gray' }
};

// 81只REITs完整数据（基于Excel导入的真实数据）
const ALL_FUNDS = [
    { code: "180101", name: "博时蛇口产园 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "180102", name: "华夏合肥高新 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "180103", name: "华夏和达高科 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "180105", name: "易方达广开产园 RE", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "180106", name: "广发成都高投产业", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "180201", name: "平安广州广河 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "180202", name: "华夏越秀高速 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "180203", name: "招商高速公路 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "180301", name: "红土创新盐田港 RE", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "180302", name: "华夏深国际 REIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "180303", name: "华泰宝湾物流 REIREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "180305", name: "南方顺丰物流 REIREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "180306", name: "华夏安博仓储 REIREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "180401", name: "鹏华深圳能源 REIREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "180402", name: "工银蒙能清洁能源 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "180501", name: "红土创新深圳安居 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "180502", name: "招商基金蛇口租赁 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "180601", name: "华夏华润商业 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180602", name: "中金印力消费 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180603", name: "华夏大悦城商业 REREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180605", name: "易方达华威市场 REREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180606", name: "中金中国绿发商业 RREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180607", name: "华夏中海商业 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "180701", name: "银华绍兴原水水利 RREIT", sector: "water", sectorName: "水利设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "水利设施", listingDate: "", remainingYears: "" },
    { code: "180801", name: "中航首钢绿能 REIREIT", sector: "eco", sectorName: "生态环保", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "生态环保", listingDate: "", remainingYears: "" },
    { code: "180901", name: "南方润泽科技数据 RREIT", sector: "datacenter", sectorName: "数据中心", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "数据中心", listingDate: "", remainingYears: "" },
    { code: "180503", name: "中航北京昌保租赁 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508000", name: "华安张江产业园 RE", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508001", name: "浙商沪杭甬 REIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508002", name: "华安百联消费 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508003", name: "中金联东科创 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508005", name: "华夏首创奥莱 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508006", name: "富国首创水务 REIREIT", sector: "eco", sectorName: "生态环保", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "生态环保", listingDate: "", remainingYears: "" },
    { code: "508007", name: "中金山东高速 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508008", name: "国金中国铁建 REIREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508009", name: "中金安徽交控 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508010", name: "中金重庆两江 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508011", name: "嘉实物美消费 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508012", name: "招商科创 REIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508015", name: "中信建投明阳智能 EREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508016", name: "华夏华电清洁能源REREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508017", name: "华夏金茂商业 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508018", name: "华夏中国交建 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508019", name: "中金湖北科投光谷 RREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508021", name: "国泰海通临港创新 RREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508022", name: "博时津开产园 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508026", name: "嘉实中国电建清洁 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508027", name: "东吴苏园产业 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508028", name: "中信建投国家电投 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508029", name: "中信建投沈阳国际 RREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508031", name: "国泰海通城投宽庭 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508033", name: "易方达深高速 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508036", name: "平安宁波交投 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508039", name: "创金合信首农 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508048", name: "华安外高桥 REIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508050", name: "华夏中核清洁能源 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508055", name: "汇添富上海地产租 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508056", name: "中金普洛斯 REIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508058", name: "中金厦门安居 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508060", name: "南方万国数据中心 RREIT", sector: "datacenter", sectorName: "数据中心", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "数据中心", listingDate: "", remainingYears: "" },
    { code: "508066", name: "华泰江苏交控 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508068", name: "华夏北京保障房 RE", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508069", name: "华夏南京交通高速 RREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508077", name: "华夏基金华润有巢 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508078", name: "中航易商仓储物流 RREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508080", name: "中金亦庄产业园 RE", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508082", name: "中金唯品会奥莱 RE", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508084", name: "汇添富九州通医药 RREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508085", name: "华泰苏州恒泰租赁 RREIT", sector: "other", sectorName: "租赁住房", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "其他", listingDate: "", remainingYears: "" },
    { code: "508086", name: "工银河北高速 REIREIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
    { code: "508087", name: "国泰海通济南能源 RREIT", sector: "municipal", sectorName: "市政设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "市政设施", listingDate: "", remainingYears: "" },
    { code: "508088", name: "国泰海通东久新经 RREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508089", name: "华夏特变电工新能 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508090", name: "中银中外运仓储物 RREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508091", name: "华夏凯德商业 REIREIT", sector: "consumer", sectorName: "消费基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "购物中心", listingDate: "", remainingYears: "" },
    { code: "508092", name: "华夏金隅智造工场 RREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508096", name: "中航京能国际能源 RREIT", sector: "energy", sectorName: "能源基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "能源设施", listingDate: "", remainingYears: "" },
    { code: "508097", name: "华泰南京建邺 REIREIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508098", name: "嘉实京东仓储基础 RREIT", sector: "logistics", sectorName: "仓储物流", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "仓储物流", listingDate: "", remainingYears: "" },
    { code: "508099", name: "建信中关村 REIT", sector: "industrial", sectorName: "产业园区", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "产业园", listingDate: "", remainingYears: "" },
    { code: "508020", name: "隧道 REIT", sector: "transport", sectorName: "交通基础设施", price: 1.0, change: 0.0, premium: 0.0, yield: 0.0, debt: 0, volume: 0, nav: 0.0, scale: 0.0, marketCap: 0.0, propertyType: "收费公路", listingDate: "", remainingYears: "" },
];

// 全局搜索下拉框初始化（所有页面共用）
function initGlobalSearchDropdown() {
    const searchInput = document.getElementById('global-search');
    if (!searchInput) return;

    // 创建下拉框容器    let dropdown = document.getElementById('global-search-dropdown');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'global-search-dropdown';
        dropdown.className = 'absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-xl mt-1 shadow-lg z-50 hidden max-h-60 overflow-y-auto';
        searchInput.parentElement.style.position = 'relative';
        searchInput.parentElement.appendChild(dropdown);
    }

    function doSearch(keyword) {
        if (!keyword || typeof ALL_FUNDS === 'undefined') return [];
        const kw = keyword.toLowerCase();
        return ALL_FUNDS.filter(f => {
            const codeMatch = f.code && f.code.toLowerCase().includes(kw);
            const nameMatch = f.name && f.name.toLowerCase().includes(kw);
            const sectorMatch = f.sectorName && f.sectorName.toLowerCase().includes(kw);
            return codeMatch || nameMatch || sectorMatch;
        }).slice(0, 8);
    }

    function renderDropdown(results) {
        if (!results.length) {
            dropdown.classList.add('hidden');
            return;
        }
        dropdown.innerHTML = results.map(f => `
            <div class="px-4 py-2 hover:bg-gray-50 cursor-pointer flex items-center justify-between" onclick="window.location.href='./fund-detail.html?code=${f.code}'">
                <div class="flex items-center gap-2">
                    <span class="mono text-blue-600 text-sm">${f.code}</span>
                    <span class="text-sm text-gray-800">${f.name}</span>
                </div>
                <span class="text-xs text-gray-400">${f.sectorName || ''}</span>
            </div>
        `).join('');
        dropdown.classList.remove('hidden');
    }

    let timer = null;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(timer);
        const keyword = e.target.value.trim();
        if (!keyword) {
            dropdown.classList.add('hidden');
            return;
        }
        timer = setTimeout(() => {
            renderDropdown(doSearch(keyword));
        }, 200);
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const keyword = searchInput.value.trim();
            if (keyword) {
                window.location.href = `./market.html?search=${encodeURIComponent(keyword)}`;
            }
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('#global-search') && !e.target.closest('#global-search-dropdown')) {
            dropdown.classList.add('hidden');
        }
    });
}

// initGlobalSearchDropdown 由需要下拉搜索的页面手动调用
