import sqlite3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'database/reits.db'
COMMON_JS_PATH = '../admin-pro/frontend/js/common.js'

def parse_all_funds():
    """逐行解析 common.js 中的 ALL_FUNDS 数组"""
    with open(COMMON_JS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到 ALL_FUNDS = [ ... ]; 之间的内容
    start = content.find('const ALL_FUNDS = [')
    end = content.find('];', start)
    if start == -1 or end == -1:
        raise ValueError("ALL_FUNDS not found")
    
    array_text = content[start:end+1]
    
    # 用正则提取每个 { ... } 对象
    funds = {}
    pattern = re.compile(r'\{([^}]+)\}')
    for match in pattern.finditer(array_text):
        obj_text = match.group(1)
        # 提取 key: value 对
        pairs = {}
        for kv in re.finditer(r'(\w+)\s*:\s*([^,]+)', obj_text):
            key = kv.group(1)
            val = kv.group(2).strip()
            # 去掉引号
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            else:
                # 尝试转为数字
                try:
                    if '.' in val:
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    pass
            pairs[key] = val
        
        code = pairs.get('code')
        if code:
            funds[code] = pairs
    
    return funds

def main():
    mock_data = parse_all_funds()
    print(f"Parsed {len(mock_data)} funds from ALL_FUNDS")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 查看当前 funds 表已有字段
    cursor.execute("PRAGMA table_info(funds)")
    existing_cols = {c[1] for c in cursor.fetchall()}
    print(f"\nExisting columns: {sorted(existing_cols)}")
    
    # 2. 需要添加的字段
    new_columns = [
        ('sector', 'VARCHAR(50)'),
        ('sector_name', 'VARCHAR(50)'),
        ('scale', 'REAL'),
        ('market_cap', 'REAL'),
        ('property_type', 'VARCHAR(50)'),
        ('remaining_years', 'VARCHAR(20)'),
        ('debt_ratio', 'REAL'),
        ('premium_rate', 'REAL'),
        ('listing_date', 'VARCHAR(20)'),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE funds ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name} {col_type}")
        else:
            print(f"  Column already exists: {col_name}")
    
    conn.commit()
    
    # 3. 用 ALL_FUNDS 数据更新 funds 表
    cursor.execute("SELECT fund_code FROM funds")
    db_codes = {r[0] for r in cursor.fetchall()}
    
    updated = 0
    skipped = 0
    for code in db_codes:
        mock = mock_data.get(code)
        if not mock:
            skipped += 1
            continue
        
        cursor.execute("""
            UPDATE funds SET
                sector = ?,
                sector_name = ?,
                scale = ?,
                market_cap = ?,
                property_type = ?,
                remaining_years = ?,
                debt_ratio = ?,
                premium_rate = ?,
                listing_date = ?,
                updated_at = datetime('now')
            WHERE fund_code = ?
        """, (
            mock.get('sector'),
            mock.get('sectorName'),
            mock.get('scale'),
            mock.get('marketCap'),
            mock.get('propertyType'),
            mock.get('remainingYears'),
            mock.get('debt'),
            mock.get('premium'),
            mock.get('listingDate'),
            code
        ))
        updated += 1
    
    conn.commit()
    print(f"\nUpdated {updated} rows, skipped {skipped} rows (no mock data)")
    
    # 4. 验证更新结果
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(sector) as has_sector,
            COUNT(scale) as has_scale,
            COUNT(debt_ratio) as has_debt,
            COUNT(market_cap) as has_mcap
        FROM funds
    """)
    row = cursor.fetchone()
    print(f"\nValidation: total={row[0]}, has_sector={row[1]}, has_scale={row[2]}, has_debt={row[3]}, has_mcap={row[4]}")
    
    # 5. 给 fund_prices 添加联合索引
    cursor.execute("PRAGMA index_list(fund_prices)")
    existing_indexes = {idx[1] for idx in cursor.fetchall()}
    
    if 'idx_fund_prices_code_date' not in existing_indexes:
        cursor.execute("CREATE INDEX idx_fund_prices_code_date ON fund_prices(fund_code, trade_date)")
        print("\nCreated index: idx_fund_prices_code_date ON fund_prices(fund_code, trade_date)")
    else:
        print("\nIndex already exists: idx_fund_prices_code_date")
    
    # 6. 也给 daily_data 和 dividends 加索引（虽然空表，但为后续准备）
    table_idx_map = {'daily_data': 'trade_date', 'dividends': 'dividend_date'}
    for table, date_col in table_idx_map.items():
        cursor.execute(f"PRAGMA index_list({table})")
        idxs = {idx[1] for idx in cursor.fetchall()}
        idx_name = f'idx_{table}_code_date'
        if idx_name not in idxs:
            cursor.execute(f"CREATE INDEX {idx_name} ON {table}(fund_code, {date_col})")
            print(f"Created index: {idx_name} ON {table}(fund_code, {date_col})")
    
    conn.commit()
    conn.close()
    print("\nMigration completed.")

if __name__ == '__main__':
    main()
