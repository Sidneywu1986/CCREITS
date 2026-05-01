# CCREITS 云服务器部署指南 (TF-IDF Only)

> **目标环境**: 2核4G 云服务器 (Ubuntu 22.04 LTS)  
> **部署方案**: TF-IDF Only（BGE-M3 需要 8G+ 内存，4G 不够）  
> **预估内存占用**: ~2.2G / 4G

---

## 一、准备

### 1.1 本地打包

在项目根目录执行：

```bash
# 1. 排除开发文件
cd /Users/apple/Projects/CCREITS

# 2. 确保预保存模型存在
ls backend/models/tfidf_vectorizer.pkl backend/models/tfidf_svd.pkl

# 3. 打包代码（排除 .git, node_modules, venv）
tar czvf ccreits-deploy.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='backend/milvus_reits.db*' \
  --exclude='backend/.milvus_reits.db*' \
  --exclude='backend/.omc' \
  backend/ data/ deploy/ docs/

# 4. 上传到云服务器
scp ccreits-deploy.tar.gz root@your-server:/opt/
```

---

## 二、服务器端部署

### 2.1 一键安装

```bash
ssh root@your-server

# 解压
cd /opt
mkdir -p ccreits
tar xzvf ccreits-deploy.tar.gz -C ccreits/
cd ccreits

# 运行安装脚本
bash deploy/install.sh
```

安装脚本会自动完成：
- 系统更新
- PostgreSQL 15 安装 + 数据库创建
- Python 3.11 + 虚拟环境
- 依赖安装
- 数据库 Schema 初始化
- 基金基础数据导入
- Systemd 服务创建

### 2.2 手动补充配置

```bash
cd /opt/ccreits/backend

# 创建 .env 文件
cat > .env <<EOF
DATABASE_URL=postgresql://reits_user:reits_pass_2024@localhost:5432/reits
DB_TYPE=postgres
DEEPSEEK_API_KEY=your_key_here
MOONSHOT_API_KEY=your_key_here
MILVUS_URI=./milvus_reits.db
EMBEDDING_DIMENSION=256
PORT=5074
HOST=0.0.0.0
EOF

# 确保预保存模型已上传
ls models/tfidf_vectorizer.pkl models/tfidf_svd.pkl
```

### 2.3 启动服务

```bash
# 启动所有服务
systemctl start ccreits-api
systemctl start ccreits-scheduler
systemctl start ccreits-frontend

# 查看状态
systemctl status ccreits-api
systemctl status ccreits-scheduler
systemctl status ccreits-frontend

# 设置开机自启（install.sh 已做）
systemctl enable ccreits-api ccreits-scheduler ccreits-frontend
```

---

## 三、验证

### 3.1 API 健康检查

```bash
curl http://your-server:5074/health
```

应返回：
```json
{"status":"ok","service":"api-adapter","database":"connected","funds_count":81}
```

### 3.2 搜索统计

```bash
curl http://your-server:5074/api/v1/search/stats
```

应返回向量数量：
```json
{"total_vectors":170169,"unique_articles":1002,"embedding_dim":256,"status":"ready"}
```

### 3.3 调度器日志

```bash
tail -f /opt/ccreits/backend/logs/scheduler.log
```

每 30 分钟应看到：
```
[Scheduler] Article sync completed
[Scheduler] LLM incremental tagging: {...}
[Scheduler] TF-IDF vectorization completed
[Scheduler] TF-IDF Milvus sync completed
```

---

## 四、日常维护

### 4.1 查看日志

```bash
# API 日志
journalctl -u ccreits-api -f

# 调度器日志
journalctl -u ccreits-scheduler -f

# 前端日志
journalctl -u ccreits-frontend -f
```

### 4.2 重启服务

```bash
systemctl restart ccreits-api
systemctl restart ccreits-scheduler
```

### 4.3 数据库备份

```bash
# 自动备份脚本 (建议加入 crontab)
pg_dump -U reits_user -d reits > /backup/reits_$(date +%Y%m%d).sql
```

### 4.4 内存监控

```bash
# 检查内存使用（4G 总内存，应留 1G+ 缓冲）
free -h

# 检查各进程内存
ps aux --sort=-%mem | head -10
```

---

## 五、升级 BGE-M3 (未来)

当业务量增长、需要升级服务器时：

1. **升级服务器到 8G+ 内存**
2. 安装 GPU 驱动（如有 NVIDIA 显卡）
3. 在 `requirements-prod.txt` 中添加：
   ```
   torch
   transformers
   modelscope
   FlagEmbedding
   ```
4. 重新部署
5. 运行 BGE-M3 迁移脚本

---

## 六、故障排查

| 问题 | 排查 |
|------|------|
| API 无法启动 | `journalctl -u ccreits-api --no-pager -n 50` |
| 数据库连接失败 | 检查 `DATABASE_URL` 和 PostgreSQL 状态 |
| Milvus 文件锁 | `pkill -f milvus_lite` + 删除 `.milvus_reits.db.lock` |
| TF-IDF 模型缺失 | 确认 `models/tfidf_*.pkl` 已上传 |
| 内存不足 | `free -h` 检查，考虑关闭不必要的服务 |
