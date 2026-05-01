#!/bin/bash
# =============================================================================
# CCREITS 云服务器部署脚本 (2核4G Ubuntu 22.04+)
# TF-IDF Only 方案 — 无需 GPU，内存占用 ~2.2G
# =============================================================================
set -e

PROJECT_DIR="/opt/ccreits"
DB_NAME="reits"
DB_USER="reits_user"
DB_PASS="reits_pass_2024"

echo "========================================"
echo "CCREITS 云服务器部署 (TF-IDF Only)"
echo "========================================"

# -----------------------------------------------------------------------------
# 1. 系统更新 & 安装基础工具
# -----------------------------------------------------------------------------
echo "[1/8] 更新系统..."
apt-get update -y
apt-get install -y curl wget git vim build-essential libpq-dev

# -----------------------------------------------------------------------------
# 2. 安装 PostgreSQL 15
# -----------------------------------------------------------------------------
echo "[2/8] 安装 PostgreSQL 15..."
apt-get install -y postgresql postgresql-contrib
systemctl enable postgresql
systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# -----------------------------------------------------------------------------
# 3. 安装 Python 3.11
# -----------------------------------------------------------------------------
echo "[3/8] 安装 Python 3.11..."
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# -----------------------------------------------------------------------------
# 4. 创建项目目录 & 虚拟环境
# -----------------------------------------------------------------------------
echo "[4/8] 创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR
python3.11 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip setuptools wheel

# -----------------------------------------------------------------------------
# 5. 安装 Python 依赖
# -----------------------------------------------------------------------------
echo "[5/8] 安装 Python 依赖..."
pip install -r requirements-prod.txt

# -----------------------------------------------------------------------------
# 6. 数据库初始化
# -----------------------------------------------------------------------------
echo "[6/8] 初始化数据库..."
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cur = conn.cursor()
with open('backend/database/postgres_schema.sql', 'r') as f:
    cur.execute(f.read())
conn.commit()
conn.close()
print('Database initialized')
"

# -----------------------------------------------------------------------------
# 7. 导入基础数据
# -----------------------------------------------------------------------------
echo "[7/8] 导入基础数据..."
cd backend

# 导入基金数据
python3 -c "
import json, psycopg2, os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 从 JSON 导入基金数据
with open('../data/reits_funds.json', 'r', encoding='utf-8') as f:
    funds = json.load(f)

for f in funds:
    cur.execute('''
        INSERT INTO business.funds (fund_code, fund_name, fund_short_name, asset_type, sector, exchange, manager, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (fund_code) DO NOTHING
    ''', (f.get('fund_code'), f.get('fund_name'), f.get('fund_short_name'), 
          f.get('asset_type'), f.get('sector'), f.get('exchange'), 
          f.get('manager'), 'active'))

conn.commit()
cur.execute('SELECT COUNT(*) FROM business.funds')
print(f'Imported {cur.fetchone()[0]} funds')
conn.close()
"

cd ..

# -----------------------------------------------------------------------------
# 8. 创建 Systemd 服务
# -----------------------------------------------------------------------------
echo "[8/8] 创建 Systemd 服务..."

# API 服务
cat > /etc/systemd/system/ccreits-api.service <<EOF
[Unit]
Description=CCREITS API Service
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
Environment=DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
Environment=DB_TYPE=postgres
Environment=PYTHONPATH=$PROJECT_DIR/backend
ExecStart=$PROJECT_DIR/venv/bin/python api_adapter.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 调度器服务
cat > /etc/systemd/system/ccreits-scheduler.service <<EOF
[Unit]
Description=CCREITS Scheduler
After=network.target postgresql.service ccreits-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
Environment=DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
Environment=DB_TYPE=postgres
Environment=PYTHONPATH=$PROJECT_DIR/backend
ExecStart=$PROJECT_DIR/venv/bin/python run_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 前端服务 (Python http.server)
cat > /etc/systemd/system/ccreits-frontend.service <<EOF
[Unit]
Description=CCREITS Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python -m http.server 5176
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ccreits-api ccreits-scheduler ccreits-frontend

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 上传代码到 $PROJECT_DIR"
echo "  2. 上传预保存模型: scp models/tfidf_*.pkl server:$PROJECT_DIR/backend/models/"
echo "  3. 配置环境变量: vim $PROJECT_DIR/backend/.env"
echo "  4. 启动服务: systemctl start ccreits-api ccreits-scheduler ccreits-frontend"
echo ""
echo "数据库连接: postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
echo "API 端口: 5074"
echo "前端端口: 5176"
