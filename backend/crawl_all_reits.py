"""批量爬取所有REIT基金公告"""
import sys
sys.path.insert(0, '.')
from backend.crawlers.cninfo_crawler import CNInfoCrawler
import time

def crawl_all():
    crawler = CNInfoCrawler()
    codes = list(crawler.REIT_CODE_MAPPING.keys())
    print(f"共 {len(codes)} 只基金，开始批量爬取...")

    total_inserted = 0
    total_downloaded = 0
    total_found = 0
    total_failed = 0

    for i, code in enumerate(codes):
        try:
            result = crawler.batch_crawl(code, max_count=200)
            stats = result.get('stats', {})
            db_sync = result.get('db_sync', {})
            downloaded = stats.get('downloaded', 0)
            found = stats.get('total_found', 0)
            inserted = db_sync.get('inserted', 0)
            skipped = db_sync.get('skipped', 0)
            err = db_sync.get('error', '')

            total_found += found
            total_downloaded += downloaded
            total_inserted += inserted

            if err:
                print(f"[{i+1}/{len(codes)}] {code}: 失败 {err}")
                total_failed += 1
            else:
                print(f"[{i+1}/{len(codes)}] {code}: 找到{found} | 下载{downloaded} | 新增{inserted} | 跳过{skipped}")

            time.sleep(1)

        except Exception as e:
            print(f"[{i+1}/{len(codes)}] {code}: 异常 {e}")
            total_failed += 1

    print(f"\n=== 批量爬取完成 ===")
    print(f"总新增: {total_inserted} 条")
    print(f"总下载PDF: {total_downloaded} 个")
    print(f"总找到: {total_found} 条")
    print(f"失败: {total_failed} 只基金")

if __name__ == '__main__':
    crawl_all()
