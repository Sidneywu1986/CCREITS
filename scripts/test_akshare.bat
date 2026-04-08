@echo off
chcp 65001 >nul
echo ==========================================
echo   测试 AKShare 配置
echo ==========================================
echo.

cd /d "%~dp0\..\消费看板5（前端）\backend\crawlers"

echo [1/3] 检查 Python...
python --version
if errorlevel 1 (
    echo [错误] Python 未安装
    pause
    exit /b 1
)

echo.
echo [2/3] 检查 AKShare...
python -c "import akshare; print('AKShare版本:', akshare.__version__)"
if errorlevel 1 (
    echo [错误] AKShare 未安装，正在安装...
    pip install akshare pandas -q
)

echo.
echo [3/3] 测试从数据库获取81只基金列表...
python akshare_crawler_v2.py list

echo.
echo ==========================================
echo   测试完成
echo ==========================================
pause
