#!/usr/bin/env python3
"""
基于 wemprss API 的全量同步脚本
从服务器 wemprss 同步全部文章到本地 PostgreSQL，支持增量更新
"""
import os
import sys
import json
import urllib.request
import subprocess
import re
import time
from datetime import datetime
from core.db import get_conn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_BASE = 'http://43.134.236.80:3000'
USERNAME = 'admin'
PASSWORD = 'admin@123'


class WemprssClient:
    """wemprss API 客户端，自动管理 token"""
    
    def __init__(self):
        self.token = None
        self.token_expires = 0
        
    def login(self):
        """登录获取 token"""
        url = f'{API_BASE}/api/v1/wx/auth/login'
        data = f'username={USERNAME}&password={PASSWORD}'
        req = urllib.request.Request(url, data=data.encode(), 
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        r = urllib.request.urlopen(req, timeout=10)
        resp = json.loads(r.read().decode())
        self.token = resp['data']['access_token']
        
        # 解析 JWT 过期时间
        import base64
        payload = self.token.split('.')[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        jwt = json.loads(base64.urlsafe_b64decode(payload))
        self.token_expires = jwt.get('exp', 0)
        print(f'[API] Logged in, token expires in {(self.token_expires - int(time.time())) // 3600}h')
        return self.token
        
    def _get_token(self):
        """获取有效 token，过期前自动刷新"""
        if not self.token or time.time() > self.token_expires - 300:
            self.login()
        return self.token
        
    def _request(self, path, method='GET', data=None):
        """发送 API 请求"""
        url = f'{API_BASE}{path}'
        headers = {'Authorization': f'Bearer {self._get_token()}'}
        if data:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        r = urllib.request.urlopen(req, timeout=60)
        return json.loads(r.read().decode())
        
    def get_feeds(self, limit=100, offset=0):
        """获取公众号列表"""
        return self._request(f'/api/v1/wx/mps?limit={limit}&offset={offset}')
        
    def get_articles(self, mp_id, limit=100, offset=0):
        """获取文章列表（分页）"""
        return self._request(f'/api/v1/wx/articles?mp_id={mp_id}&limit={limit}&offset={offset}')
        
    def get_article_detail(self, article_id):
        """获取单篇文章详情（含完整 content）"""
        return self._request(f'/api/v1/wx/articles/{article_id}')
        
    def update_mp(self, mp_id, start_page=1, end_page=1):
        """触发公众号历史同步"""
        return self._request(f'/api/v1/wx/mps/update/{mp_id}?start_page={start_page}&end_page={end_page}')


def get_local_last_sync():
    """获取本地最新同步时间"""
    with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT MAX(published) FROM business.wechat_articles")
            row = c.fetchone()
            result = row['max'] if row else None
    return result or "1970-01-01T00:00:00"


def get_local_links():
    """获取本地已存在的文章链接（用于去重）"""
    with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT link FROM business.wechat_articles")
            links = {row['link'] for row in c.fetchall() if row.get('link')}
    return links


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


def ensure_table():
    """确保 wechat_articles 表存在"""
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
                    vectorized BOOLEAN DEFAULT FALSE,
                    sentiment_score REAL,
                    emotion_tag TEXT,
                    event_tags TEXT,
                    vector BYTEA
                )
            """)
            conn.commit()


def sync_articles(client, local_links, dry_run=False):
    """
    同步文章
    :param client: WemprssClient 实例
    :param local_links: 本地已有的链接集合
    :param dry_run: 如果为 True，只统计不写入
    :return: (新增数量, 跳过数量, 错误数量)
    """
    ensure_table()
    
    # 获取公众号列表
    print('[Sync] Fetching feeds list...')
    feeds_resp = client.get_feeds(limit=100, offset=0)
    feeds = feeds_resp.get('data', {}).get('list', []) if isinstance(feeds_resp.get('data'), dict) else []
    print(f'[Sync] Found {len(feeds)} feeds')
    
    new_articles = []
    skipped = 0
    errors = 0
    
    for feed in feeds:
        mp_id = feed.get('id')
        mp_name = feed.get('mp_name', mp_id)
        print(f'[Sync] Processing: {mp_name} ({mp_id})')
        
        # 分页获取文章列表
        offset = 0
        limit = 100
        feed_total = 0
        while True:
            try:
                resp = client.get_articles(mp_id, limit=limit, offset=offset)
                data = resp.get('data', {})
                articles = data.get('list', []) if isinstance(data, dict) else []
                total = data.get('total', 0) if isinstance(data, dict) else 0
                if offset == 0:
                    feed_total = total
                    print(f'  total on server: {total}')
                
                if not articles:
                    break
                    
                for article in articles:
                    url = article.get('url')
                    if not url:
                        continue
                    if url in local_links:
                        skipped += 1
                        continue
                    
                    # 获取单篇详情（含 content）
                    article_id = article.get('id')
                    try:
                        detail_resp = client.get_article_detail(article_id)
                        detail = detail_resp.get('data', {})
                        content = detail.get('content') or clean_html(detail.get('content_html', ''))
                        if not content or len(content) < 50:
                            skipped += 1
                            continue
                            
                        pub_ts = article.get('publish_time', 0)
                        pub_dt = datetime.fromtimestamp(pub_ts) if pub_ts else datetime.now()
                        pub_iso = pub_dt.strftime('%Y-%m-%dT%H:%M:%S')
                        
                        new_articles.append({
                            'source': article.get('mp_name', mp_name),
                            'title': article.get('title', ''),
                            'link': url,
                            'published': pub_iso,
                            'content': content,
                        })
                        local_links.add(url)  # 避免同一批次内重复
                        
                    except Exception as e:
                        print(f'  detail error for {article_id}: {e}')
                        errors += 1
                
                if len(articles) < limit:
                    break
                offset += limit
                
            except Exception as e:
                print(f'  list error: {e}')
                errors += 1
                break
        
        print(f'  -> new so far: {len(new_articles)}, skipped: {skipped}, errors: {errors}')
    
    # 写入数据库
    if not dry_run and new_articles:
        print(f'[Sync] Writing {len(new_articles)} articles to local DB...')
        with get_conn() as conn:
                    c = conn.cursor()
                    inserted = 0
                    for a in new_articles:
                        try:
                            c.execute("""
                                INSERT INTO business.wechat_articles (source, title, link, published, content, vectorized)
                                VALUES (%s, %s, %s, %s, %s, FALSE)
                            """, (a['source'], a['title'], a['link'], a['published'], a['content']))
                            inserted += 1
                        except Exception:  # psycopg2.IntegrityError
                            pass  # 重复，忽略
                    conn.commit()
        print(f'[Sync] Inserted {inserted} articles')
        return inserted, skipped, errors
    elif dry_run:
        print(f'[Sync] DRY RUN: would insert {len(new_articles)} articles')
        return len(new_articles), skipped, errors
    else:
        print('[Sync] No new articles')
        return 0, skipped, errors


def run_script(name):
    """运行本地处理脚本"""
    script_path = os.path.join(BASE_DIR, 'backend', 'scripts', name)
    if os.path.exists(script_path):
        print(f'[Sync] Running {name} ...')
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=os.path.join(BASE_DIR, 'backend'),
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                print(f'[Sync] {name} stderr: {result.stderr[:500]}')
            else:
                print(f'[Sync] {name} done')
        except subprocess.TimeoutExpired:
            print(f'[Sync] {name} timeout')
        except Exception as e:
            print(f'[Sync] {name} error: {e}')
    else:
        print(f'[Sync] Script not found: {script_path}')


def test_update_depth(client, mp_id='MP_WXS_2393306340'):
    """测试 update API 能同步多少页历史文章"""
    print(f'\n[UpdateTest] Testing update depth for {mp_id}')
    
    # 记录当前数量
    before_resp = client.get_articles(mp_id, limit=1, offset=0)
    before_total = before_resp.get('data', {}).get('total', 0) if isinstance(before_resp.get('data'), dict) else 0
    print(f'[UpdateTest] Before update: {before_total} articles')
    
    # 触发同步（1-10 页）
    try:
        update_resp = client.update_mp(mp_id, start_page=1, end_page=10)
        print(f'[UpdateTest] Update response: {json.dumps(update_resp, ensure_ascii=False, indent=2)[:400]}')
    except urllib.error.HTTPError as e:
        print(f'[UpdateTest] Update HTTP error: {e.code}')
        print(f'[UpdateTest] Body: {e.read().decode()[:300]}')
    except Exception as e:
        print(f'[UpdateTest] Update error: {type(e).__name__}: {e}')
    
    return before_total


def main():
    print("=" * 60)
    print(f"[Sync] Start: {datetime.now().isoformat()}")
    
    client = WemprssClient()
    client.login()
    
    # 测试 update 深度（如果用户要求）
    test_update = '--test-update' in sys.argv
    if test_update:
        test_update_depth(client)
        print('[Sync] Update test triggered. Check server later for results.')
        print("=" * 60)
        return
    
    # 常规同步
    local_links = get_local_links()
    print(f'[Sync] Local existing articles: {len(local_links)}')
    
    dry_run = '--dry-run' in sys.argv
    inserted, skipped, errors = sync_articles(client, local_links, dry_run=dry_run)
    
    if inserted > 0 and not dry_run:
        run_script('vectorize_articles.py')
        run_script('tag_sentiment.py')
        print(f'[Sync] Complete! Added {inserted} articles.')
    elif dry_run:
        print(f'[Sync] DRY RUN complete. Would add {inserted} articles.')
    else:
        print('[Sync] No new articles.')
    
    print(f'[Sync] End: {datetime.now().isoformat()}')
    print('=' * 60)


if __name__ == '__main__':
    main()
