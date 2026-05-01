#!/bin/bash
# =============================================================================
# CCREITS 本地打包脚本 — 准备上传到云服务器
# =============================================================================
set -e

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)
OUTPUT="$PROJECT_ROOT/ccreits-deploy.tar.gz"

echo "========================================"
echo "CCREITS 部署包打包"
echo "========================================"

# 检查预保存模型
if [ ! -f "backend/models/tfidf_vectorizer.pkl" ] || [ ! -f "backend/models/tfidf_svd.pkl" ]; then
    echo "错误: 预保存 TF-IDF 模型不存在"
    echo "请先在本地运行: cd backend && python3 scripts/vectorize_articles.py"
    exit 1
fi

echo "打包中..."
tar czvf "$OUTPUT" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='backend/milvus_reits.db*' \
    --exclude='backend/.milvus_reits.db*' \
    --exclude='backend/.omc' \
    --exclude='backend/logs/*.log' \
    --exclude='*.log' \
    backend/ \
    data/ \
    deploy/

echo ""
echo "========================================"
echo "打包完成: $OUTPUT"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 上传: scp $OUTPUT root@服务器IP:/root/"
echo "  2. SSH:  ssh root@服务器IP"
echo "  3. 执行: bash /root/ccreits/deploy/setup-server.sh"
