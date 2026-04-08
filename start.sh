#!/bin/bash

# REITs数据平台 - 启动脚本

echo "=========================================="
echo "   REITs数据平台 - 启动服务"
echo "=========================================="
echo ""
echo "服务地址: http://localhost:3001"
echo "按 Ctrl+C 停止服务"
echo ""

cd backend
node server.js
