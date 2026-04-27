#!/usr/bin/env python3
"""
开机自动同步脚本：从服务器 wemprss PostgreSQL 增量同步文章到本地 PostgreSQL
用法：直接运行，或放入 Windows 开机启动项
"""
import os
import sys
import paramiko
import subprocess
import re
from datetime import datetime
from core.db import get_conn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVER_HOST = '43.134.236.80'
SERVER_USER = 'ubuntu'
KEY_PATH = os.path.expanduser('~/.ssh/id_ed25519')
SERVER_SUDO_PASS = '1032.com'


def get_local_last_sync():
    """获取本地最新同步时间"""
    with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT MAX(published) FROM business.wechat_articles")
            result = c.fetchone()[0]
    return result or "1970-01-01T00:00:00"


def clean_html(raw_html):
    """简单清理 HTML 标签"""
    if not raw_html:
        return ''
    text = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def fetch_new_articles(last_sync_iso):
    """通过 SSH 从服务器 PostgreSQL 查询新文章"""
    try:
        last_sync_dt = datetime.fromisoformat(last_sync_iso.replace('Z', '+00:00'))
    except ValueError:
        last_sync_dt = datetime.strptime(last_sync_iso, '%Y-%m-%dT%H:%M:%S')
    last_sync_unix = int(last_sync_dt.timestamp())

    print(f"[Sync] Query articles after unix={last_sync_unix} ({last_sync_iso})")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_HOST, username=SERVER_USER, key_filename=KEY_PATH, timeout=30)

    query = f"""
    SELECT a.id, a.mp_id, a.title, a.url, a.publish_time,
           COALESCE(a.content, ''), COALESCE(a.content_html, ''),
           COALESCE(f.mp_name, a.mp_id)
    FROM articles a
    LEFT JOIN feeds f ON a.mp_id = f.id
    WHERE a.publish_time > {last_sync_unix}
      AND a.has_content = 1
      AND LENGTH(COALESCE(a.content, a.content_html, '')) > 100
    ORDER BY a.publish_time
    """

    cmd = f"echo {SERVER_SUDO_PASS} | sudo -S docker exec we-mp-rss-db psql -U werss -d werss -t -A -F '|' -c \"{query}\" 2>/dev/null"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    client.close()

    articles = []
    for line in out.strip().split('\n'):
        line = line.strip()
        if not line or line == '(0 rows)':
            continue
        parts = line.split('|')
        if len(parts) < 8:
            continue
        try:
            pub_ts = int(parts[4]) if parts[4] else 0
        except ValueError:
            continue
        articles.append({
            'id': parts[0],
            'mp_id': parts[1],
            'title': parts[2],
            'url': parts[3],
            'publish_time': pub_ts,
            'content': parts[5],
            'content_html': parts[6],
            'source': parts[7] if parts[7] else parts[1],
        })

    return articles


def sync_to_local(articles):
    """写入本地 PostgreSQL"""
    if not articles:
        return 0

    with get_conn() as conn:
            c = conn.cursor()
        
            c.execute("""
                CREATE TABLE IF NOT EXISTS business.wechat_articles (
                    id SERIAL PRIMARY KEY,
                    source TEXT,
                    title TEXT,
                    link TEXT UNIQUE,
                    published TEXT,
                    content TEXT,
                    vectorized INTEGER DEFAULT 0,
                    sentiment_score REAL,
                    emotion_tag TEXT,
                    event_tags TEXT,
                    vector BYTEA
                )
            """)
            conn.commit()
        
            inserted = 0
            skipped = 0
            for a in articles:
                c.execute("SELECT 1 FROM business.wechat_articles WHERE link = %s", (a['url'],))
                if c.fetchone():
                    skipped += 1
                    continue
        
                content = a['content'] if a['content'] else clean_html(a['content_html'])
                if len(content) < 50:
                    skipped += 1
                    continue
        
                pub_dt = datetime.fromtimestamp(a['publish_time'])
                pub_iso = pub_dt.strftime('%Y-%m-%dT%H:%M:%S')
        
                c.execute("""
                    INSERT INTO business.wechat_articles (source, title, link, published, content, vectorized)
                    VALUES (%s, %s, %s, %s, %s, 0)
                """, (a['source'], a['title'], a['url'], pub_iso, content))
                inserted += 1
        
            conn.commit()
    print(f"[Sync] Inserted {inserted}, skipped {skipped}")
    return inserted


def run_script(name):
    """运行本地处理脚本"""
    script_path = os.path.join(BASE_DIR, 'backend', 'scripts', name)
    if os.path.exists(script_path):
        print(f"[Sync] Running {name} ...")
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=os.path.join(BASE_DIR, 'backend'),
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                print(f"[Sync] {name} stderr: {result.stderr[:500]}")
            else:
                print(f"[Sync] {name} done")
        except subprocess.TimeoutExpired:
            print(f"[Sync] {name} timeout")
        except Exception as e:
            print(f"[Sync] {name} error: {e}")
    else:
        print(f"[Sync] Script not found: {script_path}")


def main():
    print("=" * 50)
    print(f"[Sync] Start: {datetime.now().isoformat()}")

    last_sync = get_local_last_sync()
    print(f"[Sync] Local last sync: {last_sync}")

    articles = fetch_new_articles(last_sync)
    print(f"[Sync] Server new articles: {len(articles)}")

    inserted = sync_to_local(articles)

    if inserted > 0:
        run_script('vectorize_articles.py')
        run_script('tag_sentiment.py')
        print(f"[Sync] Complete! Added {inserted} articles.")
    else:
        print("[Sync] No new articles.")

    print(f"[Sync] End: {datetime.now().isoformat()}")
    print("=" * 50)


if __name__ == '__main__':
    main()
