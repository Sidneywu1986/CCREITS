#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据服务
提供REITs数据的RESTful API接口
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.config import settings
from core.database import get_db_context


class FundPrice(BaseModel):
    """基金价格数据模型"""
    fund_code: str
    name: str
    price: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: int
    change_percent: float


class AKShareServer:
    """AKShare数据服务"""

    def __init__(self):
        self.ak = None
        self.init_akshare()

    def init_akshare(self):
        """初始化AKShare"""
        try:
            import akshare as ak
            self.ak = ak
            print("✅ AKShare初始化成功")
        except ImportError as e:
            print(f"❌ AKShare导入失败: {e}")
            raise

    async def get_reits_list(self) -> List[Dict[str, Any]]:
        """获取REITs基金列表"""
        try:
            if not self.ak:
                self.init_akshare()

            # 获取场内基金列表
            df = self.ak.fund_etf_spot_em()

            # 筛选REITs（代码以15、16、18、50、508、509、180开头）
            reits_codes = ['15', '16', '18', '50', '508', '509', '180']
            reits_df = df[df['代码'].astype(str).str.startswith(tuple(reits_codes))]

            # 进一步筛选名称包含REIT的
            reits_df = reits_df[reits_df['名称'].str.contains('REIT|reit', na=False, case=False)]

            results = []
            for _, row in reits_df.iterrows():
                results.append({
                    "code": str(row['代码']),
                    "name": row['名称'],
                    "exchange": "SH" if str(row['代码']).startswith(('5', '50')) else "SZ",
                    "price": float(row['最新价']) if row['最新价'] and str(row['最新价']) != 'nan' else 0,
                    "volume": int(row['成交量']) if row['成交量'] and str(row['成交量']) != 'nan' else 0,
                })

            return results
        except Exception as e:
            print(f"获取REITs列表失败: {e}")
            return []

    async def get_reits_price(self, fund_codes: List[str]) -> List[FundPrice]:
        """获取REITs实时价格"""
        try:
            if not self.ak:
                self.init_akshare()

            results = []
            for code in fund_codes:
                try:
                    # 获取实时行情
                    df = self.ak.stock_zh_a_spot_em()
                    fund_data = df[df['代码'] == code]

                    if not fund_data.empty:
                        row = fund_data.iloc[0]
                        price = float(row['最新价']) if row['最新价'] else 0
                        prev_close = float(row['昨收']) if row['昨收'] else 0

                        results.append(FundPrice(
                            fund_code=code,
                            name=row['名称'],
                            price=price,
                            open=float(row['今开']) if row['今开'] else 0,
                            high=float(row['最高']) if row['最高'] else 0,
                            low=float(row['最低']) if row['最低'] else 0,
                            prev_close=prev_close,
                            volume=int(row['成交量']) if row['成交量'] else 0,
                            change_percent=(price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                        ))
                except Exception as e:
                    print(f"获取基金{code}价格失败: {e}")
                    continue

            return results
        except Exception as e:
            print(f"获取REITs价格失败: {e}")
            return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 AKShare服务正在启动...")
    yield
    print("🛑 AKShare服务正在关闭...")


app = FastAPI(
    title="AKShare REITs数据服务",
    description="提供REITs基金数据",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

akshare_server = AKShareServer()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "akshare"}


@app.get("/api/reits/list")
async def get_reits_list():
    """获取REITs基金列表"""
    try:
        funds = await akshare_server.get_reits_list()
        return {"success": True, "data": funds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reits/price")
async def get_reits_price(codes: str = ""):
    """获取REITs实时价格"""
    try:
        if codes:
            fund_codes = codes.split(',')
        else:
            # 获取所有REITs代码
            funds = await akshare_server.get_reits_list()
            fund_codes = [f["code"] for f in funds]

        prices = await akshare_server.get_reits_price(fund_codes)
        return {"success": True, "data": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fund/detail/{fund_code}")
async def get_fund_detail(fund_code: str):
    """获取基金详情"""
    try:
        if not akshare_server.ak:
            akshare_server.init_akshare()

        # 获取基金详情
        df = akshare_server.ak.fund_etf_hist_em(symbol=fund_code)

        if df.empty:
            raise HTTPException(status_code=404, detail="基金不存在")

        # 获取最新数据
        latest = df.iloc[-1]

        return {
            "success": True,
            "data": {
                "code": fund_code,
                "net_value": float(latest['单位净值']) if '单位净值' in df.columns else 0,
                "nav_date": latest['净值日期'].strftime('%Y-%m-%d') if '净值日期' in df.columns else None,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print(f"🌐 AKShare服务启动在端口 {settings.PORT}")
    uvicorn.run(
        "akshare_server:app",
        host=settings.HOST,
        port=5000,  # 固定使用5000端口
        reload=False,
        log_level="info"
    )