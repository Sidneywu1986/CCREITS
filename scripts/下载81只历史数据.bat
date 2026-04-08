@echo off
chcp 65001 >nul
echo ==========================================
echo   下载81只REITs历史日线数据
echo ==========================================
echo.

cd /d "D:\tools\消费看板5（前端）\backend"

echo [*] 开始下载81只基金历史数据（365天）...
echo [*] 预计需要10-20分钟，请耐心等待
echo.

node crawlers/akshare.js history

echo.
echo ==========================================
echo   下载完成
echo ==========================================
pause
