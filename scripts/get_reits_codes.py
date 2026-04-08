#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从AKShare获取79只REITs基金代码
使用前请先安装: pip install akshare pandas
"""

import akshare as ak
import pandas as pd
import json

# 你提供的79只基金名称列表
fund_names = [
    "中信建投国家电投",
    "华夏南京交通高速",
    "华夏华电清洁能源",
    "汇添富上海地产租",
    "华夏中国交建REIT",
    "国泰海通东久新经",
    "易方达广开产园RE",
    "国泰海通城投宽庭",
    "嘉实中国电建清洁",
    "中金印力消费REIT",
    "浙商沪杭甬REIT",
    "南方万国数据中心",
    "易方达深高速REIT",
    "中航首钢绿能REIT",
    "广发成都高投产业",
    "中金重庆两江REIT",
    "华夏特变电工新能",
    "中金厦门安居REIT",
    "易方达华威市场RE",
    "中金湖北科投光谷",
    "华夏金隅智造工场",
    "招商基金蛇口租赁",
    "南方润泽科技数据",
    "红土创新深圳安居",
    "工银河北高速REIT",
    "汇添富九州通医药",
    "华安张江产业园RE",
    "博时蛇口产园REIT",
    "招商高速公路REIT",
    "华夏大悦城商业RE",
    "嘉实物美消费REIT",
    "华泰苏州恒泰租赁",
    "华夏越秀高速REIT",
    "中金中国绿发商业",
    "华夏和达高科REIT",
    "中银中外运仓储物",
    "中金联东科创REIT",
    "建信中关村REIT",
    "华夏北京保障房RE",
    "中金安徽交控REIT",
    "华夏中核清洁能源",
    "中金亦庄产业园RE",
    "华夏首创奥莱REIT",
    "华泰宝湾物流REIT",
    "富国首创水务REIT",
    "国金中国铁建REIT",
    "华夏基金华润有巢",
    "华安百联消费REIT",
    "平安广州广河REIT",
    "平安宁波交投REIT",
    "中信建投沈阳国际",
    "招商科创REIT",
    "中航京能国际能源",
    "创金合信首农REIT",
    "华泰南京建邺REIT",
    "华夏合肥高新REIT",
    "华泰江苏交控REIT",
    "国泰海通济南能源",
    "华夏中海商业REIT",
    "南方顺丰物流REIT",
    "工银蒙能清洁能源",
    "中金山东高速REIT",
    "中航易商仓储物流",
    "嘉实京东仓储基础",
    "中信建投明阳智能",
    "银华绍兴原水水利",
    "华夏安博仓储REIT",
    "华夏深国际REIT",
    "华夏金茂商业REIT",
    "国泰海通临港创新",
    "东吴苏园产业REIT",
    "华安外高桥REIT",
    "中金普洛斯REIT",
    "鹏华深圳能源REIT",
    "华夏华润商业REIT",
    "博时津开产园REIT",
    "红土创新盐田港RE",
    "中金唯品会奥莱RE",
    "华夏凯德商业REIT"
]

def get_reits_from_akshare():
    """从AKShare获取REITs列表"""
    try:
        # 获取场内基金实时行情
        df = ak.fund_etf_spot_em()
        
        # 筛选REITs（名称包含REIT）
        reits_df = df[df['名称'].str.contains('REIT', na=False)]
        
        result = []
        for _, row in reits_df.iterrows():
            result.append({
                'code': str(row['代码']),
                'name': row['名称'],
                'price': row['最新价'],
                'change': row['涨跌幅']
            })
        
        return pd.DataFrame(result)
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def match_funds():
    """匹配基金名称和代码"""
    # 获取AKShare数据
    ak_data = get_reits_from_akshare()
    
    if ak_data is None:
        return
    
    print(f"从AKShare获取到 {len(ak_data)} 只REITs\n")
    
    # 保存完整数据
    ak_data.to_csv('reits_from_akshare.csv', index=False, encoding='utf-8-sig')
    print("✓ 已保存完整数据到: reits_from_akshare.csv\n")
    
    # 尝试匹配
    matched = []
    unmatched = []
    
    for name in fund_names:
        # 在AKShare数据中查找匹配
        match = ak_data[ak_data['名称'].str.contains(name.replace('REIT', '').replace('RE', ''), na=False)]
        
        if len(match) > 0:
            matched.append({
                '搜索名称': name,
                '基金代码': match.iloc[0]['code'],
                '完整名称': match.iloc[0]['name']
            })
        else:
            unmatched.append(name)
    
    # 保存匹配结果
    if matched:
        matched_df = pd.DataFrame(matched)
        matched_df.to_csv('reits_matched.csv', index=False, encoding='utf-8-sig')
        print(f"✓ 成功匹配 {len(matched)} 只基金，已保存到: reits_matched.csv")
    
    if unmatched:
        print(f"\n⚠ 未匹配的基金 ({len(unmatched)} 只):")
        for name in unmatched:
            print(f"  - {name}")
        
        # 保存未匹配列表
        with open('reits_unmatched.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(unmatched))
        print(f"\n✓ 未匹配列表已保存到: reits_unmatched.txt")

def main():
    print("=" * 60)
    print("REITs基金代码获取工具")
    print("=" * 60)
    print(f"\n待查询基金数量: {len(fund_names)} 只\n")
    
    match_funds()
    
    print("\n" + "=" * 60)
    print("操作完成！请查看生成的文件。")
    print("=" * 60)

if __name__ == '__main__':
    main()
