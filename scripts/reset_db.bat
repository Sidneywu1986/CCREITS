@echo off
chcp 65001 >nul
echo ==========================================
echo   重置REITs数据库 - 只保留20只基金
echo ==========================================
echo.

cd /d "%~dp0\..\消费看板5（前端）\backend"

if not exist "node_modules" (
    echo [错误] 请先运行 install.bat 安装依赖
    pause
    exit /b 1
)

echo 正在重置数据库...
node reset_reits_db.js

echo.
pause
