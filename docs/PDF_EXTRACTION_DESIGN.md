# REIT公告PDF高精度提取与多AI验证方案

## 一、工具选型对比

| 工具 | 综合准确率 | 表格识别 | 速度 | 部署方式 | 适用场景 |
|------|-----------|---------|------|---------|---------|
| **MinerU** | 90.7% | ⭐⭐⭐⭐⭐ | 慢(2页/s) | 本地GPU/云端 | 复杂版面、高精度需求 |
| **PyMuPDF+OCR** | 75-82% | ⭐⭐⭐ | 快(50+页/s) | 本地CPU | 简单PDF、批量处理 |
| **Unstructured** | ~68% | ⭐⭐⭐⭐ | 中等 | 本地/云端 | 通用文档 |
| **LlamaParse** | ~76% | ⭐⭐⭐⭐ | 依赖网络 | 云端API | 快速原型 |

**推荐方案**: 
- **主引擎**: MinerU (VLM模式，版面恢复+表格识别)
- **备用引擎**: PyMuPDF+PaddleOCR (处理MinerU失败的文件)

---

## 二、多AI交叉验证架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PDF Input (公告PDF)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 1: PDF预处理 & 版面分析                     │
│         (MinerU / PyMuPDF → Markdown + 结构化数据)           │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Extractor 1  │   │  Extractor 2  │   │  Extractor 3  │
│  基础信息提取  │   │  财务数据提取  │   │  运营数据提取  │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ • 公告标题    │   │ • 分红金额    │   │ • 出租率      │
│ • 公告日期    │   │ • 每份分红    │   │ • 租金水平    │
│ • 公告类型    │   │ • 权益登记日  │   │ • 客流量      │
│ • 基金管理人  │   │ • 除息日      │   │ • 收入情况    │
│ • 基金代码    │   │ • 收益分配基准│   │ • 成本数据    │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 2: 数据融合 & 冲突检测                     │
│         (对比3个Extractor的输出，标记差异字段)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 3: AI Validator 交叉验证                   │
│    (专门用于验证冲突字段，给出置信度评分和最终判定)             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 4: 人工审核队列 (可选)                      │
│         (置信度<80%或关键字段冲突时进入人工审核)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 5: 数据入库 & 版本管理                      │
│         (存储提取结果、置信度、AI模型版本、原始PDF链接)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、三AI分工设计

### Extractor 1: 基础信息提取员
**职责**: 提取公告的元数据
```python
{
    "公告标题": "华安张江光大园REIT 2024年度第一次收益分配公告",
    "基金代码": "508000",
    "基金管理人": "华安基金管理有限公司",
    "公告日期": "2024-06-15",
    "公告类型": "分红公告",  # 枚举: 分红/运营/财务/询价/其他
    "PDF页数": 5,
    "文件大小": "2.3MB"
}
```
**Prompt策略**: 
- 角色: "你是专业的REIT公告阅读助手，擅长快速识别公告的基础信息"
- 输出: 严格的JSON格式
- 约束: "如果某字段不确定，使用null而不是猜测"

### Extractor 2: 财务数据提取员
**职责**: 提取分红、财务相关数据
```python
{
    "分红方案": {
        "每10份分红金额": 2.5,
        "分红总金额": 12500000.00,
        "单位": "元"
    },
    "权益登记日": "2024-06-20",
    "除息日": "2024-06-21",
    "分红发放日": "2024-06-28",
    "收益分配基准日": "2024-03-31",
    "应分配金额": 12500000.00,
    "分红比例": "99.5%"
}
```
**Prompt策略**:
- 角色: "你是注册会计师，擅长从公告中提取精确的财务数据"
- 特殊处理: 识别多种金额写法（"人民币贰仟伍佰万元整" → 25000000）
- 验证: "确保日期逻辑正确（权益登记日 < 除息日 < 发放日）"

### Extractor 3: 运营数据提取员
**职责**: 提取底层资产的运营指标
```python
{
    "底层资产": "张江光大园",
    "资产类型": "产业园区",
    "报告期": "2024年Q1",
    "出租率": "95.8%",
    "有效租金单价": "5.8元/平方米/天",
    "租金收缴率": "98.5%",
    "租户数量": 32,
    "前十大租户占比": "62.3%",
    "加权平均剩余租期": "3.2年",
    "客流量": null  # 仅仓储物流/商业REIT
}
```
**Prompt策略**:
- 角色: "你是REIT行业分析师，擅长提取底层资产的运营指标"
- 注意: "不同REIT类型关注不同指标（产业园vs高速公路vs仓储物流）"

### Validator: 交叉验证员
**职责**: 验证三个Extractor的结果一致性
```python
{
    "验证结果": {
        "基金代码": {
            "Extractor1": "508000",
            "Extractor2": "508000", 
            "Extractor3": "508000",
            "一致性": true,
            "置信度": 99,
            "最终值": "508000"
        },
        "分红金额": {
            "Extractor1": null,
            "Extractor2": "12500000",
            "Extractor3": null,
            "一致性": "单源",
            "置信度": 85,
            "最终值": "12500000",
            "备注": "仅在Extractor2中出现，需确认"
        },
        "出租率": {
            "Extractor1": null,
            "Extractor2": "95%",
            "Extractor3": "95.8%",
            "一致性": false,
            "置信度": 70,
            "最终值": "95.8%",
            "备注": "Extractor2和Extractor3不一致，取Extractor3（专业运营提取员）"
        }
    },
    "整体置信度": 87,
    "建议操作": "通过"  # 通过/人工审核/拒识
}
```

---

## 四、技术实现方案

### 4.1 工具链
```bash
# 核心依赖
pip install magic-pdf[full]       # MinerU - 版面恢复
pip install pdfplumber            # 表格提取备用
pip install PyMuPDF               # 快速文本提取
pip install paddleocr             # OCR识别

# AI模型 (三AI)
pip install openai                # GPT-4o / Claude
pip install anthropic             # Claude 3.5 Sonnet (推荐)
```

### 4.2 数据表设计
```sql
-- PDF提取结果表
CREATE TABLE pdf_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,
    pdf_url TEXT NOT NULL,
    
    -- 提取结果
    extracted_data JSON,           -- 合并后的最终数据
    extractor1_data JSON,          -- 基础信息提取结果
    extractor2_data JSON,          -- 财务数据提取结果
    extractor3_data JSON,          -- 运营数据提取结果
    validation_result JSON,        -- 验证结果
    
    -- 置信度
    overall_confidence REAL,       -- 整体置信度 0-100
    field_confidence JSON,         -- 各字段置信度
    
    -- 元数据
    extraction_model TEXT,         -- 使用的模型版本
    extraction_time DATETIME,      -- 提取时间
    processing_status TEXT,        -- pending/processing/completed/failed
    retry_count INTEGER DEFAULT 0, -- 重试次数
    
    -- 人工审核
    review_status TEXT,            -- pending/auto_pass/manual_review
    reviewed_by TEXT,              -- 审核人
    reviewed_at DATETIME,          -- 审核时间
    review_comments TEXT,          -- 审核意见
    
    FOREIGN KEY (announcement_id) REFERENCES announcements(id)
);

-- 提取历史表 (用于追踪同一PDF多次提取的结果)
CREATE TABLE extraction_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id INTEGER,
    version INTEGER,
    extracted_data JSON,
    confidence REAL,
    model_version TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES pdf_extractions(id)
);
```

### 4.3 处理流程

```python
class PDFExtractionPipeline:
    """
    PDF高精度提取流水线
    """
    
    def __init__(self):
        self.mineru = MinerUClient()  # 版面恢复
        self.extractor1 = BaseInfoExtractor(model="claude-3-5-sonnet")
        self.extractor2 = FinancialExtractor(model="claude-3-5-sonnet")
        self.extractor3 = OperationalExtractor(model="claude-3-5-sonnet")
        self.validator = CrossValidator(model="claude-3-5-sonnet")
    
    async def process(self, pdf_url: str, announcement_id: int):
        # Step 1: PDF下载 & 版面恢复
        pdf_bytes = await download_pdf(pdf_url)
        markdown, tables = self.mineru.extract(pdf_bytes)
        
        # Step 2: 三AI并行提取
        results = await asyncio.gather(
            self.extractor1.extract(markdown, tables),
            self.extractor2.extract(markdown, tables),
            self.extractor3.extract(markdown, tables)
        )
        
        # Step 3: 交叉验证
        validation = await self.validator.validate(results)
        
        # Step 4: 决策
        if validation['overall_confidence'] >= 90:
            status = 'auto_pass'
        elif validation['overall_confidence'] >= 70:
            status = 'manual_review'
        else:
            status = 'failed'
        
        # Step 5: 入库
        await self.save_extraction(
            announcement_id=announcement_id,
            pdf_url=pdf_url,
            results=results,
            validation=validation,
            status=status
        )
        
        return validation
```

---

## 五、成本与性能估算

### 5.1 处理成本 (按1000份公告计算)

| 方案 | 版面恢复 | AI调用 | 总成本 | 准确率 |
|------|---------|--------|--------|--------|
| **方案A: 全Claude** | MinerU本地免费 | 4次/公告 × $0.008 | ~$32 | 90%+ |
| **方案B: 混合** | MinerU本地免费 | GPT-3.5(3次) + GPT-4(1次验证) | ~$18 | 85%+ |
| **方案C: 经济** | PyMuPDF免费 | GPT-3.5(4次) | ~$12 | 75%+ |

### 5.2 处理速度

| 步骤 | 耗时 | 说明 |
|------|------|------|
| PDF下载 | 1-3s | 取决于网络 |
| MinerU版面恢复 | 3-10s | GPU模式，20页PDF |
| 三AI并行提取 | 5-15s | 取决于API响应 |
| 交叉验证 | 2-5s | |
| **总计** | **15-35s/公告** | |

---

## 六、实施建议

### Phase 1: MVP (2周)
1. 部署MinerU本地版
2. 实现单AI提取 + 简单验证
3. 处理100份历史公告测试

### Phase 2: 三AI验证 (2周)
1. 实现三AI并行提取
2. 实现交叉验证逻辑
3. 人工审核后台

### Phase 3: 自动化 (1周)
1. 集成到定时任务
2. 新公告自动触发提取
3. 低置信度自动告警

### 关键技术决策
1. **AI模型选择**: Claude 3.5 Sonnet (比GPT-4便宜50%，中文理解好)
2. **版面恢复**: MinerU本地部署 (避免云端费用)
3. **冲突解决**: 置信度加权投票 + 专业领域优先级

---

## 七、风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|---------|
| MinerU处理扫描件失败 | 中 | 降级到PaddleOCR |
| AI API限流 | 高 | 实现队列 + 指数退避 |
| 三AI结果严重冲突 | 中 | 强制人工审核 |
| 成本超支 | 低 | 设置月度预算上限 |
| 数据隐私 | 中 | 敏感PDF使用本地模型 |

---

**下一步**: 是否需要我开始实现 Phase 1 (MinerU部署 + 单AI提取原型)？