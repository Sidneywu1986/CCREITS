#!/bin/bash
# =============================================================================
# CCREITS 云服务器一键部署脚本
# 使用方法:
#   1. 本地打包: tar czvf ccreits.tar.gz backend/ data/ deploy/
#   2. 上传服务器: scp ccreits.tar.gz root@服务器IP:/root/
#   3. 服务器执行: bash /root/ccreits/deploy/setup-server.sh
# =============================================================================
set -e

PROJECT_DIR="/opt/ccreits"
DB_NAME="reits"
DB_USER="reits_user"
DB_PASS="reits_pass_2024"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# 检查 root 权限
# -----------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行: sudo bash setup-server.sh"
    exit 1
fi

log_info "========================================"
log_info "CCREITS 云服务器部署 (TF-IDF Only)"
log_info "配置: 2核4G / Ubuntu 22.04+"
log_info "========================================"

# -----------------------------------------------------------------------------
# 1. 系统更新 & 安装依赖
# -----------------------------------------------------------------------------
log_info "[1/10] 更新系统..."
apt-get update -y
apt-get install -y curl wget git vim build-essential libpq-dev postgresql postgresql-contrib python3.11 python3.11-venv python3.11-dev python3-pip

# -----------------------------------------------------------------------------
# 2. 创建项目目录
# -----------------------------------------------------------------------------
log_info "[2/10] 创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 如果当前目录有上传的代码，复制过去
if [ -f "/root/ccreits.tar.gz" ]; then
    log_info "发现上传包 /root/ccreits.tar.gz，解压中..."
    tar xzvf /root/ccreits.tar.gz -C /tmp/
    cp -r /tmp/ccreits/backend /tmp/ccreits/data /tmp/ccreits/deploy ./
fi

# 如果没有代码，尝试 git clone（如果有仓库）
if [ ! -d "$PROJECT_DIR/backend" ]; then
    log_warn "未找到项目代码，请确保已上传 ccreits.tar.gz"
    log_warn "本地打包命令: tar czvf ccreits.tar.gz backend/ data/ deploy/"
    exit 1
fi

# -----------------------------------------------------------------------------
# 3. 配置 PostgreSQL
# -----------------------------------------------------------------------------
log_info "[3/10] 配置 PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# 检查用户是否存在
USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "")
if [ -z "$USER_EXISTS" ]; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
fi

# 检查数据库是否存在
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "")
if [ -z "$DB_EXISTS" ]; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# -----------------------------------------------------------------------------
# 4. 创建 Python 虚拟环境
# -----------------------------------------------------------------------------
log_info "[4/10] 创建 Python 虚拟环境..."
cd $PROJECT_DIR
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# -----------------------------------------------------------------------------
# 5. 安装依赖
# -----------------------------------------------------------------------------
log_info "[5/10] 安装 Python 依赖..."
pip install -r deploy/requirements-prod.txt

# 如果有本地包需要安装
if [ -f "$PROJECT_DIR/backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
fi

# -----------------------------------------------------------------------------
# 6. 数据库初始化
# -----------------------------------------------------------------------------
log_info "[6/10] 初始化数据库 Schema..."
export PGUSER=$DB_USER
export PGPASSWORD=$DB_PASS
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=$DB_NAME

# 执行 schema
psql -h localhost -U $DB_USER -d $DB_NAME -f backend/database/postgres_schema.sql

log_info "数据库 Schema 初始化完成"

# -----------------------------------------------------------------------------
# 7. 导入基础数据
# -----------------------------------------------------------------------------
log_info "[7/10] 导入基金基础数据..."
cd $PROJECT_DIR/backend

python3 << 'PYEOF'
import json, psycopg2, os

conn = psycopg2.connect(
    host='localhost', database='reits', user='reits_user', password='reits_pass_2024'
)
cur = conn.cursor()

# 导入基金数据
json_path = '../data/reits_funds.json'
if os.path.exists(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        funds = json.load(f)
    
    for fund in funds:
        cur.execute('''
            INSERT INTO business.funds (fund_code, fund_name, fund_short_name, asset_type, sector, exchange, manager, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fund_code) DO NOTHING
        ''', (
            fund.get('fund_code'), fund.get('fund_name'), fund.get('fund_short_name'),
            fund.get('asset_type'), fund.get('sector'), fund.get('exchange'),
            fund.get('manager'), 'active'
        ))
    
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM business.funds')
    print(f'Imported {cur.fetchone()[0]} funds')
else:
    print('No reits_funds.json found, skipping')

conn.close()
PYEOF

cd $PROJECT_DIR

# -----------------------------------------------------------------------------
# 8. 创建环境配置文件
# -----------------------------------------------------------------------------
log_info "[8/10] 创建环境配置文件..."
cat > backend/.env <<EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
DB_TYPE=postgres
MILVUS_URI=./milvus_reits.db
EMBEDDING_DIMENSION=256
PORT=5074
HOST=0.0.0.0
EOF

# 如果本地有 API key 文件，复制过去
if [ -f "/root/.ccreits_keys" ]; then
    cat /root/.ccreits_keys >> backend/.env
fi

# -----------------------------------------------------------------------------
# 9. 创建 Systemd 服务
# -----------------------------------------------------------------------------
log_info "[9/10] 创建 Systemd 服务..."

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
EnvironmentFile=$PROJECT_DIR/backend/.env
ExecStart=$PROJECT_DIR/venv/bin/python api_adapter.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

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
EnvironmentFile=$PROJECT_DIR/backend/.env
ExecStart=$PROJECT_DIR/venv/bin/python run_scheduler.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

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

# -----------------------------------------------------------------------------
# 10. 启动服务
# -----------------------------------------------------------------------------
log_info "[10/10] 启动服务..."
systemctl start ccreits-api
sleep 3
systemctl start ccreits-scheduler
systemctl start ccreits-frontend

# -----------------------------------------------------------------------------
# 验证
# -----------------------------------------------------------------------------
log_info "========================================"
log_info "部署完成！"
log_info "========================================"

sleep 2

# 检查 API
API_STATUS=$(curl -s --max-time 5 http://localhost:5074/health 2>/dev/null || echo "")
if [ -n "$API_STATUS" ]; then
    log_info "API 健康检查: $API_STATUS"
else
    log_warn "API 健康检查失败，请检查日志: journalctl -u ccreits-api -n 20"
fi

# 检查数据库
cd $PROJECT_DIR/backend
FUND_COUNT=$(python3 -c "import psycopg2; conn=psycopg2.connect('postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM business.funds'); print(cur.fetchone()[0])" 2>/dev/null || echo "0")
log_info "数据库基金数: $FUND_COUNT"

echo ""
log_info "服务状态:"
systemctl status ccreits-api --no-pager | grep "Active:"
systemctl status ccreits-scheduler --no-pager | grep "Active:"
systemctl status ccreits-frontend --no-pager | grep "Active:"

echo ""
log_info "访问地址:"
log_info "  API:    http://服务器IP:5074"
log_info "  前端:   http://服务器IP:5176"
log_info ""
log_info "常用命令:"
log_info "  查看API日志:    journalctl -u ccreits-api -f"
log_info "  查看调度器日志: journalctl -u ccreits-scheduler -f"
log_info "  重启API:        systemctl restart ccreits-api"
log_info "  重启调度器:     systemctl restart ccreits-scheduler"
