# -*- coding: utf-8 -*-
import akshare as ak
import sys

# 找派息率/股息率相关接口
tests = [
    ("fund_etf_spot", lambda: ak.fund_etf_spot()),
    ("fund_etf_spot_em", lambda: ak.fund_etf_spot_em()),
    ("fund_hk_spot", lambda: ak.fund_hk_spot()),
    ("fund_lof_spot", lambda: ak.fund_lof_spot()),
]

for name, fn in tests:
    try:
        print(f"=== {name} ===")
        df = fn()
        cols = [c for c in df.columns if any(k in str(c) for k in ['息','红','年化','yield','rate','dvd','per'])]
        print(f"分红相关列: {cols}")
        print(df.head(2).to_string() if not df.empty else "empty")
        print()
    except (RuntimeError, ValueError) as e:
        print(f"失败: {e}\n")
