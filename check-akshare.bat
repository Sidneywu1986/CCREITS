@echo off
chcp 65001 >nul
echo 检查 AKShare 安装状态...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python 未安装
    echo 请安装 Python 3.8+ 并添加到 PATH
    pause
    exit /b 1
)

echo [OK] Python 版本:
python --version
echo.

echo 检查 AKShare...
python -c "import akshare; print('[OK] AKShare 版本:', akshare.__version__)" 2>nul
if errorlevel 1 (
    echo [X] AKShare 未安装
    echo 正在安装 AKShare...
    cd backend
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] AKShare 安装失败
        pause
        exit /b 1
    )
    cd ..
)

echo.
echo AKShare 检查完成！
pause
