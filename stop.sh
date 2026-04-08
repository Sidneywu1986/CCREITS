#!/bin/bash

# REITs数据平台 - 停止脚本

echo "正在停止服务..."
pkill -f "node server.js" 2>/dev/null || true
echo "服务已停止"
