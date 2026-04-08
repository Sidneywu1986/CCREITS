#!/bin/bash

echo "=========================================="
echo "  重置REITs数据库 - 只保留20只基金"
echo "=========================================="
echo ""

cd "$(dirname "$0")/../消费看板5（前端）/backend"

if [ ! -d "node_modules" ]; then
    echo "[错误] 请先运行 ./install.sh 安装依赖"
    exit 1
fi

echo "正在重置数据库..."
node reset_reits_db.js

echo ""
read -p "按回车键继续..."
