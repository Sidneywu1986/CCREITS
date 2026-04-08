#!/bin/bash

# REITs数据平台 - 生产环境部署脚本
# 支持 Ubuntu/CentOS/Debian

set -e

APP_NAME="reits-platform"
APP_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

echo "=========================================="
echo "   REITs数据平台 - 生产环境部署"
echo "=========================================="
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 安装 Node.js
echo "[1/5] 安装 Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi
echo "Node.js 版本: $(node --version)"

# 安装 PM2
echo ""
echo "[2/5] 安装 PM2..."
npm install -g pm2

# 创建应用目录
echo ""
echo "[3/5] 创建应用目录..."
mkdir -p $APP_DIR
cp -r backend $APP_DIR/
cp -r frontend $APP_DIR/

# 安装依赖
echo ""
echo "[4/5] 安装依赖..."
cd $APP_DIR/backend
npm install --production

# 初始化数据库
node -e "
const {initDatabase} = require('./database/db');
initDatabase()
  .then(() => { console.log('数据库初始化成功'); process.exit(0); })
  .catch(e => { console.error('数据库初始化失败:', e); process.exit(1); });
"

# 创建 systemd 服务
echo ""
echo "[5/5] 创建系统服务..."
cat > $SERVICE_FILE << EOF
[Unit]
Description=REITs Data Platform
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$APP_DIR/backend
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=PORT=3001

[Install]
WantedBy=multi-user.target
EOF

# 设置权限
chown -R www-data:www-data $APP_DIR
chmod +x $APP_DIR

# 启动服务
systemctl daemon-reload
systemctl enable $APP_NAME
systemctl start $APP_NAME

echo ""
echo "=========================================="
echo "   部署完成！"
echo "=========================================="
echo ""
echo "服务地址: http://$(hostname -I | awk '{print $1}'):3001"
echo ""
echo "常用命令:"
echo "  查看状态: systemctl status $APP_NAME"
echo "  查看日志: journalctl -u $APP_NAME -f"
echo "  重启服务: systemctl restart $APP_NAME"
echo "  停止服务: systemctl stop $APP_NAME"
echo ""
