@echo off
chcp 65001 >nul
echo ==========================================
echo   启动服务并获取81只REITs行情
echo ==========================================
echo.

cd /d "D:\tools\消费看板5（前端）\backend"

echo [1/2] 启动后端服务...
start cmd /k "node server.js"

echo.
echo [2/2] 等待5秒后获取实时行情...
timeout /t 5 /nobreak >nul

echo [*] 正在获取81只基金实时行情...
node crawlers/akshare.js spot

echo.
echo ==========================================
echo   操作完成
echo ==========================================
echo.
echo 现在可以访问: http://localhost:3001
echo 查看81只REITs数据和行情
pause
