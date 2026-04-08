#!/bin/bash

echo "检查 AKShare 安装状态..."
echo

if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[X] Python 未安装"
    echo "请安装 Python 3.8+"
    exit 1
fi

echo "[OK] Python 版本:"
python3 --version 2>/dev/null || python --version
echo

echo "检查 AKShare..."
if python3 -c "import akshare; print(f'[OK] AKShare 版本: {akshare.__version__}')" 2>/dev/null || \
   python -c "import akshare; print(f'[OK] AKShare 版本: {akshare.__version__}')" 2>/dev/null; then
    echo
    echo "AKShare 检查完成！"
else
    echo "[X] AKShare 未安装"
    echo "正在安装 AKShare..."
    cd backend
    pip3 install -r requirements.txt || pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] AKShare 安装失败"
        exit 1
    fi
    cd ..
    echo
    echo "AKShare 安装完成！"
fi
