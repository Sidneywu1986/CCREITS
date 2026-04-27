@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  REITs 数据平台 - 启动所有服务
echo ========================================
echo.

:: 启动 API 适配层 (端口 5074)
start "API-5074" cmd /k "cd /d %~dp0backend && python api_adapter.py"
echo [1/3] API 适配层启动中... http://localhost:5074

:: 等待 API 启动
timeout /t 3 /nobreak >nul

:: 启动管理后台 (端口 5075)
start "Admin-5075" cmd /k "cd /d %~dp0backend && python admin_app.py"
echo [2/3] 管理后台启动中... http://localhost:5075

:: 等待后台启动
timeout /t 3 /nobreak >nul

:: 启动前端服务器 (端口 5176)
start "Frontend-5176" cmd /k "cd /d %~dp0admin-pro\frontend && python server.py"
echo [3/3] 前端服务器启动中... http://localhost:5176

echo.
echo ========================================
echo  所有服务已启动！
echo  前端访问: http://localhost:5176/market.html
echo  管理后台: http://localhost:5075/docs
echo  API文档:  http://localhost:5074/docs
echo ========================================
echo.
echo 按任意键关闭本窗口（服务继续在后台运行）
pause >nul
