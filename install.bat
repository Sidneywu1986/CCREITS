@echo off
chcp 65001 >nul
title REITs数据平台 - 安装

echo ==========================================
echo   REITs数据平台 - 开发环境安装
echo ==========================================
echo.

:: 检查 Python
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 Python，AKShare 功能将不可用
    echo 如需使用 AKShare，请安装 Python 3.8+
) else (
    echo [OK] Python 版本:
    python --version
)

:: 检查 Node.js
echo.
echo [2/4] 检查 Node.js 环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js 版本: 
node --version

:: 安装后端依赖
echo.
echo [3/4] 安装后端依赖...
cd backend
call npm install
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
cd ..

:: 安装 Python 依赖
echo.
echo [4/4] 安装 Python 依赖 (AKShare)...
python --version >nul 2>&1
if errorlevel 0 (
    cd backend
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [警告] AKShare 安装失败，可能需要手动安装
        echo 手动安装命令: pip install akshare pandas numpy requests
    )
    cd ..
) else (
    echo [跳过] Python 未安装
)

:: 初始化数据库
echo.
echo 初始化数据库...
cd backend
node -e "const {initDatabase} = require('./database/db'); initDatabase().then(() => { console.log('OK'); setTimeout(() => process.exit(0), 500); }).catch(e => { console.error(e); process.exit(1); })"
if errorlevel 1 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
cd ..

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo 启动服务请运行: start.bat
echo.
pause
