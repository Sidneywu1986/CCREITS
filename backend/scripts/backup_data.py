#!/usr/bin/env python3
"""
数据备份脚本
- Milvus 数据库文件
- PostgreSQL 关键表
- 保留最近 10 份备份，自动清理旧备份
"""
import os
import sys
import subprocess
import datetime
import glob
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "backups")
MILVUS_DB = os.path.join(os.path.dirname(__file__), "..", "milvus_reits.db")
KEEP_COUNT = 10

TABLES = [
    "business.wechat_articles",
    "business.article_vectors",
    "business.article_tags",
    "business.fund_codes",
]


def backup_milvus():
    if not os.path.exists(MILVUS_DB):
        print("Milvus DB not found, skipping")
        return
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"milvus_reits.db.{ts}")
    shutil.copy2(MILVUS_DB, dst)
    size = os.path.getsize(dst) / 1024 / 1024
    print(f"Milvus: {size:.1f}MB -> {dst}")


def backup_postgres():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for table in TABLES:
        schema, name = table.split(".")
        outfile = os.path.join(BACKUP_DIR, f"{schema}_{name}_{ts}.sql")
        cmd = f"pg_dump -h localhost -p 5432 -U postgres -d reits -t {table} --data-only --inserts > {outfile}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if os.path.exists(outfile):
            size = os.path.getsize(outfile) / 1024 / 1024
            print(f"PG {table}: {size:.1f}MB -> {outfile}")
        else:
            print(f"PG {table}: FAILED - {result.stderr[:200]}")


def cleanup_old():
    """清理旧备份，每类保留最近 KEEP_COUNT 份"""
    patterns = [
        "milvus_reits.db.*",
        "business_wechat_articles_*.sql",
        "business_article_vectors_*.sql",
        "business_article_tags_*.sql",
        "business_fund_codes_*.sql",
    ]
    for pat in patterns:
        files = sorted(glob.glob(os.path.join(BACKUP_DIR, pat)))
        if len(files) > KEEP_COUNT:
            for old in files[:-KEEP_COUNT]:
                os.remove(old)
                print(f"  Removed old: {os.path.basename(old)}")


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"Backup dir: {BACKUP_DIR}")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    backup_milvus()
    backup_postgres()
    print("=" * 50)
    cleanup_old()

    print("Done!")


if __name__ == "__main__":
    main()
