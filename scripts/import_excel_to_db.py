#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Excel导入81只REITs基金到数据库
"""

import pandas as pd
import sqlite3
import os

# 路径配置
EXCEL_PATH = r'C:\Users\Administrator\Desktop\中国公募REITs完整分类清单_81只_20260405.xlsx'
DB_PATH = r'D:\tools\消费看板5（前端）\backend\database\reits.db'

def clear_database(conn):
    """清空数据库"""
    cursor = conn.cursor()
    print('[*] 正在清空数据库...')
    
    cursor.execute('DELETE FROM quotes')
    cursor.execute('DELETE FROM price_history')
    cursor.execute('DELETE FROM announcements')
    cursor.execute('DELETE FROM funds')
    
    # 重置自增ID
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements')")
    
    conn.commit()
    print('[OK] 数据库已清空')

def import_from_excel(conn):
    """从Excel导入数据"""
    print(f'[*] 正在读取Excel: {EXCEL_PATH}')
    
    # 读取Excel
    df = pd.read_excel(EXCEL_PATH)
    
    print(f'[OK] 读取成功，共 {len(df)} 只基金')
    print(f'[*] 列名: {list(df.columns)}\n')
    
    cursor = conn.cursor()
    
    # 准备插入数据
    inserted = 0
    for idx, row in df.iterrows():
        try:
            # 根据实际列名调整
            基金代码 = str(row.iloc[1]).strip()  # 第二列：基金代码
            基金名称 = str(row.iloc[2]).strip()  # 第三列：基金名称
            板块分类 = str(row.iloc[3]).strip()  # 第四列：板块分类
            
            # 映射板块到英文代码
            sector_map = {
                '产业园区': 'industrial',
                '交通基础设施': 'transport',
                '仓储物流': 'logistics',
                '能源基础设施': 'energy',
                '租赁住房': 'housing',
                '消费基础设施': 'consumer',
                '生态环保': 'eco',
                '水利设施': 'water',
                '市政设施': 'municipal',
                '数据中心': 'datacenter',
                '文化旅游': 'tourism',
                '商业办公': 'commercial',
                '养老设施': 'elderly',
                '城市更新': 'urban',
                '其他': 'other'
            }
            
            sector = sector_map.get(板块分类, 'other')
            
            cursor.execute('''
                INSERT INTO funds (code, name, sector, sector_name)
                VALUES (?, ?, ?, ?)
            ''', (基金代码, 基金名称, sector, 板块分类))
            
            inserted += 1
            print(f'  [{inserted:2d}] {基金代码} - {基金名称}')
            
        except Exception as e:
            print(f'  [X] 第{idx+1}行导入失败: {e}')
    
    conn.commit()
    return inserted

def show_stats(conn):
    """显示统计信息"""
    cursor = conn.cursor()
    
    print('\n' + '='*60)
    print('导入统计')
    print('='*60)
    
    # 总数
    cursor.execute('SELECT COUNT(*) FROM funds')
    total = cursor.fetchone()[0]
    print(f'\n总计: {total} 只基金')
    
    # 按板块统计
    print('\n按板块分布:')
    cursor.execute('SELECT sector_name, COUNT(*) FROM funds GROUP BY sector_name ORDER BY COUNT(*) DESC')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}只')
    
    # 按交易所统计
    print('\n按交易所分布:')
    cursor.execute("""
        SELECT 
            CASE 
                WHEN code LIKE '180%' THEN '深交所'
                WHEN code LIKE '508%' THEN '上交所'
                ELSE '其他'
            END as exchange,
            COUNT(*) 
        FROM funds 
        GROUP BY exchange
    """)
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}只')
    
    print('\n' + '='*60)

def main():
    print('='*60)
    print('REITs基金数据导入工具')
    print('从Excel导入81只基金到SQLite数据库')
    print('='*60)
    print()
    
    # 检查文件
    if not os.path.exists(EXCEL_PATH):
        print(f'[X] Excel文件不存在: {EXCEL_PATH}')
        return
    
    if not os.path.exists(DB_PATH):
        print(f'[X] 数据库不存在: {DB_PATH}')
        return
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # 1. 清空数据库
        clear_database(conn)
        
        # 2. 导入Excel数据
        count = import_from_excel(conn)
        
        # 3. 显示统计
        show_stats(conn)
        
        print(f'\n[OK] 导入完成！共 {count} 只基金入库')
        
    except Exception as e:
        print(f'\n[X] 导入失败: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    main()
