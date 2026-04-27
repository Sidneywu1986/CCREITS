"""
迁移 SQLite 核心数据到 PostgreSQL ai_db
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

SQLITE_DB = 'database/reits.db'
PG_DSN = "host=localhost dbname=ai_db user=postgres password=postgres"

def migrate_wechat_articles(sq_cur, pg_conn):
    print("Migrating wechat_articles...")
    # 先补齐字段
    pg_cur = pg_conn.cursor()
    for col in [
        ("sentiment_score", "REAL"),
        ("emotion_tag", "TEXT"),
        ("asset_tags", "TEXT"),
        ("event_tags", "TEXT"),
    ]:
        pg_cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='wechat_articles' AND column_name='{col[0]}'
                ) THEN
                    ALTER TABLE wechat_articles ADD COLUMN {col[0]} {col[1]};
                END IF;
            END $$;
        """)
    pg_conn.commit()

    # 读取 SQLite 数据
    sq_cur.execute("""
        SELECT id, source, title, link, published, content, raw_content,
               content_length, vectorized, created_at, updated_at,
               sentiment_score, emotion_tag, asset_tags, event_tags
        FROM wechat_articles
    """)
    rows = []
    for row in sq_cur.fetchall():
        row = list(row)
        row[8] = bool(row[8])  # vectorized: int -> bool
        rows.append(tuple(row))

    # 清空并插入
    pg_cur.execute("TRUNCATE TABLE wechat_articles CASCADE")
    cols = "id, source, title, link, published, content, raw_content, content_length, vectorized, created_at, updated_at, sentiment_score, emotion_tag, asset_tags, event_tags"
    template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    execute_values(pg_cur, f"INSERT INTO wechat_articles ({cols}) VALUES %s", rows, template=template)
    pg_conn.commit()
    print(f"  Inserted {len(rows)} rows")

    # 重置序列
    pg_cur.execute("SELECT MAX(id) FROM wechat_articles")
    max_id = pg_cur.fetchone()[0] or 0
    pg_cur.execute(f"ALTER SEQUENCE wechat_articles_id_seq RESTART WITH {max_id + 1}")
    pg_conn.commit()

def migrate_funds(sq_cur, pg_conn):
    print("Migrating funds...")
    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS funds (
            id SERIAL PRIMARY KEY,
            fund_code VARCHAR(10),
            fund_name VARCHAR(100),
            full_name VARCHAR(200),
            exchange VARCHAR(10),
            ipo_date VARCHAR(20),
            ipo_price FLOAT,
            total_shares FLOAT,
            nav FLOAT,
            manager VARCHAR(100),
            custodian VARCHAR(100),
            asset_type VARCHAR(50),
            underlying_assets TEXT,
            status VARCHAR(20),
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            dividend_yield REAL,
            sector VARCHAR(50),
            sector_name VARCHAR(50),
            scale REAL,
            market_cap REAL,
            property_type VARCHAR(50),
            remaining_years VARCHAR(20),
            debt_ratio REAL,
            premium_rate REAL,
            listing_date VARCHAR(20),
            fund_type VARCHAR(20)
        )
    """)
    pg_cur.execute("TRUNCATE TABLE funds CASCADE")
    sq_cur.execute("SELECT * FROM funds")
    rows = sq_cur.fetchall()
    # Convert string 'null' to None for numeric columns
    numeric_cols = {'ipo_price', 'total_shares', 'nav', 'dividend_yield', 'scale', 'market_cap', 'debt_ratio', 'premium_rate'}
    col_names = [d[0] for d in sq_cur.description]
    cleaned = []
    for row in rows:
        new_row = []
        for i, val in enumerate(row):
            if col_names[i] in numeric_cols and isinstance(val, str) and val.lower() == 'null':
                new_row.append(None)
            else:
                new_row.append(val)
        cleaned.append(tuple(new_row))
    rows = cleaned
    cols = ", ".join(col_names)
    template = "(" + ", ".join(["%s"] * len(col_names)) + ")"
    execute_values(pg_cur, f"INSERT INTO funds ({cols}) VALUES %s", rows, template=template)
    pg_conn.commit()
    print(f"  Inserted {len(rows)} rows")
    pg_cur.execute(f"SELECT setval('funds_id_seq', COALESCE((SELECT MAX(id) FROM funds), 1), false)")
    pg_conn.commit()

def migrate_fund_prices(sq_cur, pg_conn):
    print("Migrating fund_prices...")
    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS fund_prices (
            id SERIAL PRIMARY KEY,
            fund_code VARCHAR(10),
            trade_date VARCHAR(10),
            open_price FLOAT,
            close_price FLOAT,
            high_price FLOAT,
            low_price FLOAT,
            volume FLOAT,
            amount FLOAT,
            change_pct FLOAT,
            premium_rate FLOAT,
            created_at TIMESTAMP,
            update_time VARCHAR(30),
            yield REAL
        )
    """)
    pg_cur.execute("TRUNCATE TABLE fund_prices CASCADE")
    sq_cur.execute("SELECT * FROM fund_prices")
    rows = sq_cur.fetchall()
    numeric_cols = {'open_price', 'close_price', 'high_price', 'low_price', 'volume', 'amount', 'change_pct', 'premium_rate', 'yield'}
    col_names = [d[0] for d in sq_cur.description]
    cleaned = []
    for row in rows:
        new_row = []
        for i, val in enumerate(row):
            if col_names[i] in numeric_cols and isinstance(val, str) and val.lower() == 'null':
                new_row.append(None)
            else:
                new_row.append(val)
        cleaned.append(tuple(new_row))
    rows = cleaned
    cols = ", ".join(col_names)
    template = "(" + ", ".join(["%s"] * len(col_names)) + ")"
    # batch insert for large table
    batch_size = 5000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        execute_values(pg_cur, f"INSERT INTO fund_prices ({cols}) VALUES %s", batch, template=template)
        pg_conn.commit()
        print(f"  Batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1} done")
    print(f"  Total inserted {len(rows)} rows")

def migrate_article_fund_tags(sq_cur, pg_conn):
    print("Migrating article_fund_tags...")
    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS article_fund_tags (
            id SERIAL PRIMARY KEY,
            article_id INTEGER NOT NULL,
            fund_code VARCHAR(10) NOT NULL,
            match_type VARCHAR(20) DEFAULT 'code',
            score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(article_id, fund_code, match_type)
        )
    """)
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_aft_article ON article_fund_tags(article_id)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_aft_fund ON article_fund_tags(fund_code)")
    pg_cur.execute("TRUNCATE TABLE article_fund_tags CASCADE")
    sq_cur.execute("SELECT id, article_id, fund_code, match_type, score, created_at FROM article_fund_tags")
    rows = sq_cur.fetchall()
    cols = "id, article_id, fund_code, match_type, score, created_at"
    template = "(%s, %s, %s, %s, %s, %s)"
    execute_values(pg_cur, f"INSERT INTO article_fund_tags ({cols}) VALUES %s", rows, template=template)
    pg_conn.commit()
    print(f"  Inserted {len(rows)} rows")

def main():
    sq_conn = sqlite3.connect(SQLITE_DB)
    sq_cur = sq_conn.cursor()
    pg_conn = psycopg2.connect(PG_DSN)

    try:
        migrate_wechat_articles(sq_cur, pg_conn)
        migrate_funds(sq_cur, pg_conn)
        migrate_fund_prices(sq_cur, pg_conn)
        migrate_article_fund_tags(sq_cur, pg_conn)
        print("\nAll migrations completed!")
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        pg_conn.rollback()
    finally:
        sq_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
