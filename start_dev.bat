@echo off
chcp 65001 >nul
title REITs Dev Servers
echo ==========================================
echo   REITs 数据平台 - 开发服务器启动器
echo ==========================================
echo.

set BACKEND_DIR=D:\tools\消费看板5（前端）\backend
set FRONTEND_DIR=D:\tools\消费看板5（前端）\admin-pro\frontend

echo [1/2] 启动后端 API (端口 5074)...
start "Backend API" cmd /k "cd /d %BACKEND_DIR% && python api_adapter.py"
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端页面 (端口 5176)...
start "Frontend Server" cmd /k "cd /d %FRONTEND_DIR% && python -m http.server 5176"
timeout /t 2 /nobreak >nul

echo.
echo ==========================================
echo   服务器已启动！请用浏览器打开：
echo.
echo   AI 聊天：http://localhost:5176/ai-chat.html
echo   市场概览：http://localhost:5176/market.html
echo   基金详情：http://localhost:5176/fund-detail.html?code=508000
echo   API 文档：http://localhost:5074/docs
echo ==========================================
echo.
echo 按任意键关闭此窗口（服务器会继续在后台运行）
pause >nul
