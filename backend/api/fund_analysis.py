#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI投研分析接口
为 fund-archive.html 提供结构化投研报告
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import re
import json
import os
from pathlib import Path

from api.search import search_articles_for_rag
from engine.sentiment import get_sentiment_engine
from agents.persona_router import get_persona_router
from core.config import settings
from core.db import get_conn

router = APIRouter(prefix="/api/ai", tags=["AI投研分析"])
logger = logging.getLogger(__name__)


class FundAnalysisRequest(BaseModel):
    """投研分析请求"""
    codes: List[str]          # 基金代码列表，1-5只
    analysis_type: str = "comprehensive"  # comprehensive/value/risk/dividend/compare


class FundAnalysisResponse(BaseModel):
    """投研分析响应"""
    success: bool
    scores: Dict[str, int]           # 六维评分
    metrics: Dict[str, str]          # 综合指标
    conclusion: Dict[str, str]       # 亮点/风险/建议
    sources: List[dict]              # 溯源信息（脱敏）
    message: Optional[str] = None    # 错误或提示信息


# ---------- 数据层 ----------

def _get_fund_profiles(codes: List[str]) -> List[dict]:
    """获取基金完整画像"""
    profiles = []
    with get_conn() as conn:
        cur = conn.cursor()
        for code in codes:
            # 基本信息
            cur.execute(
                """SELECT fund_code, fund_name, full_name, exchange, sector, sector_name,
                          scale, market_cap, nav, dividend_yield, debt_ratio, premium_rate,
                          manager, property_type, remaining_years, listing_date
                   FROM business.funds WHERE fund_code = %s""", (code,)
            )
            row = cur.fetchone()
            if not row:
                continue
            profile = dict(row)

            # 最新价格
            cur.execute(
                """SELECT trade_date, close_price, change_pct, volume, premium_rate, yield
                   FROM business.fund_prices WHERE fund_code = %s ORDER BY trade_date DESC LIMIT 1""", (code,)
            )
            price_row = cur.fetchone()
            if price_row:
                profile["latest_price"] = dict(price_row)
            else:
                profile["latest_price"] = None

            # 最新财务指标
            cur.execute(
                """SELECT report_period, total_revenue, operating_revenue, net_profit,
                          total_assets, net_assets, fund_nav_per_share,
                          distributeable_amount, distribution_per_share
                   FROM business.reit_financial_metrics
                   WHERE fund_code = %s ORDER BY report_period DESC LIMIT 1""", (code,)
            )
            fin_row = cur.fetchone()
            if fin_row:
                profile["financials"] = dict(fin_row)
            else:
                profile["financials"] = None

            # 最近4次分红
            cur.execute(
                """SELECT dividend_date, dividend_amount, record_date, ex_dividend_date
                   FROM business.dividends WHERE fund_code = %s ORDER BY dividend_date DESC LIMIT 4""", (code,)
            )
            div_rows = cur.fetchall()
            profile["dividends"] = [dict(r) for r in div_rows]

            profiles.append(profile)
    return profiles


def _build_fund_context(profiles: List[dict], analysis_type: str) -> str:
    """构建基金数据上下文文本"""
    lines = []
    type_desc = {
        "comprehensive": "综合分析",
        "value": "估值分析",
        "risk": "风险评估",
        "dividend": "分红预测",
        "compare": "横向对比"
    }
    lines.append(f"分析类型：{type_desc.get(analysis_type, '综合分析')}")
    lines.append(f"选中基金数量：{len(profiles)}只\n")

    for i, p in enumerate(profiles, 1):
        lines.append(f"--- 基金{i}：{p['fund_name']} ({p['fund_code']}) ---")
        lines.append(f"板块：{p.get('sector_name', p.get('sector', ''))}")
        lines.append(f"管理人：{p.get('manager', '未知')}")
        lines.append(f"资产类型：{p.get('property_type', '未知')}")
        lines.append(f"规模：{p.get('scale', '未知')}亿元")
        lines.append(f"NAV：{p.get('nav', '未知')}元")
        lines.append(f"股息率：{p.get('dividend_yield', '未知')}%")
        lines.append(f"负债率：{p.get('debt_ratio', '未知')}%")
        lines.append(f"溢价率：{p.get('premium_rate', '未知')}%")

        lp = p.get("latest_price")
        if lp:
            lines.append(f"最新价：{lp.get('close_price', '未知')}元 ({lp.get('change_pct', '未知')}%)")
            lines.append(f"成交量：{lp.get('volume', '未知')}")

        fin = p.get("financials")
        if fin:
            lines.append(f"报告期：{fin.get('report_period', '未知')}")
            lines.append(f"营业收入：{fin.get('operating_revenue', '未知')}万元")
            lines.append(f"净利润：{fin.get('net_profit', '未知')}万元")
            lines.append(f"可供分配金额：{fin.get('distributeable_amount', '未知')}万元")
            lines.append(f"每份分红：{fin.get('distribution_per_share', '未知')}元")

        divs = p.get("dividends", [])
        if divs:
            lines.append(f"最近分红记录：")
            for d in divs:
                lines.append(f"  {d.get('dividend_date', '')}: {d.get('dividend_amount', '')}元/份")
        lines.append("")

    return "\n".join(lines)


# ---------- Prompt & LLM ----------

ANALYSIS_SYSTEM_PROMPT = """你是一位资深 REITs 投研分析师，拥有10年以上公募REITs研究经验。
请基于提供的基金数据和参考资料，给出专业、客观、可落地的投研分析报告。

【分析原则】
1. 评分必须基于真实数据，不能编造。数据缺失时给出保守评分并说明原因。
2. 六维评分标准：
   - 估值与回报：看股息率、溢价率、NAV折价/溢价水平
   - 运营质量：看营收稳定性、出租率、租金增长率（如有数据）
   - 财务健康：看负债率、现金流、可供分配金额
   - 资产质量：看底层资产类型、地段、剩余年限、管理人能力
   - 成长潜力：看板块前景、扩募能力、运营改善空间
   - 市场与流动性：看市值规模、成交量、机构持仓（如有）
3. 风险等级划分：低(<3%)、中低(3-5%)、中(5-7%)、中高(7-10%)、高(>10%)，基于历史波动率和杠杆水平
4. 分红稳定性：A+(连续4次准时足额)、A(3次)、B+(2次)、B(1次)、C(无记录/不稳定)

【输出格式】
必须严格返回以下 JSON 格式，不要有任何其他文字：
{
  "scores": {
    "估值与回报": 0-100,
    "运营质量": 0-100,
    "财务健康": 0-100,
    "资产质量": 0-100,
    "成长潜力": 0-100,
    "市场与流动性": 0-100
  },
  "metrics": {
    "综合评分": "0-100之间的数字，保留1位小数",
    "预期年化收益": "x.x%（基于股息率+价格变动预期，给出区间中值）",
    "风险等级": "低/中低/中/中高/高",
    "分红稳定性": "A+/A/B+/B/C"
  },
  "conclusion": {
    "highlights": "投资亮点，2-3句话，基于具体数据",
    "risks": "主要风险，2-3句话",
    "suggestion": "操作建议，1-2句话，给出具体可执行的建议"
  }
}"""


def _sanitize_citations(answer: str) -> str:
    """前端展示前脱敏"""
    answer = re.sub(r'《[^》]+》', '相关研究', answer)
    answer = re.sub(r'(?:公众号|微信号|专栏)[""\s]*[^\s，。]{2,20}[""\s]*', '内部研究', answer)
    answer = re.sub(r'\d{4}年\d{1,2}月[^\s，。]{2,15}(?:分析|报告|研报|点评)', '此前分析', answer)
    answer = re.sub(r'\[\d+\]\s*【[^】]+】', '', answer)
    return answer


def _build_public_sources(rag_results, confidence: str) -> List[dict]:
    count = len(rag_results) if rag_results else 0
    if count == 0:
        return []
    return [{
        "type": "internal_research",
        "confidence": confidence,
        "description": "基于内部研究资料",
        "count": count,
    }]


def _parse_llm_json(raw: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(raw)
    except Exception:
        pass
    # 尝试提取 ```json ... ``` 代码块
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 尝试提取最外层 { ... }
    m = re.search(r'(\{.*\})', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def _default_scores() -> Dict[str, int]:
    return {
        "估值与回报": 70, "运营质量": 70, "财务健康": 70,
        "资产质量": 70, "成长潜力": 70, "市场与流动性": 70,
    }


def _default_metrics() -> Dict[str, str]:
    return {
        "综合评分": "70.0",
        "预期年化收益": "5.0%",
        "风险等级": "中",
        "分红稳定性": "B+",
    }


def _default_conclusion() -> Dict[str, str]:
    return {
        "highlights": "基于现有数据，该基金具备基本投资价值。",
        "risks": "数据有限，建议进一步关注财务报告和运营数据。",
        "suggestion": "建议小额试仓，等待更充分的披露信息后再做决策。",
    }


# ---------- API ----------

@router.post("/analyze-funds", response_model=FundAnalysisResponse)
async def analyze_funds(req: FundAnalysisRequest):
    """
    AI投研分析接口
    根据选中的1-5只基金，返回结构化投研报告
    """
    if not req.codes:
        raise HTTPException(status_code=400, detail="请至少选择1只基金")
    if len(req.codes) > 5:
        raise HTTPException(status_code=400, detail="最多选择5只基金")

    # 1. 获取基金数据
    try:
        profiles = _get_fund_profiles(req.codes)
        if not profiles:
            raise HTTPException(status_code=404, detail="未找到选中的基金数据")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取基金数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据读取失败: {e}")

    # 2. 构建数据上下文
    fund_context = _build_fund_context(profiles, req.analysis_type)

    # 3. RAG 检索
    rag_results = []
    try:
        query = f"{' '.join(p['fund_name'] for p in profiles)} {req.analysis_type}分析"
        rag_results = search_articles_for_rag(query, top_k=5)
    except Exception as e:
        logger.warning(f"RAG检索失败: {e}")

    internal_context = ""
    if rag_results:
        lines = []
        for i, r in enumerate(rag_results[:5]):
            lines.append(f"[内部研究-{i+1}] {r.chunk_text[:400]}")
        internal_context = "\n\n参考信息（内部研究资料）：\n" + "\n\n".join(lines)

    # 4. 检查 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG.get("deepseek", {}).get("api_key", ""))
    if not api_key:
        return FundAnalysisResponse(
            success=False,
            scores=_default_scores(),
            metrics=_default_metrics(),
            conclusion=_default_conclusion(),
            sources=[],
            message="AI 分析功能需要配置 DeepSeek API Key。请联系管理员设置 DEEPSEEK_API_KEY 环境变量后重启服务。"
        )

    # 5. 调用 LLM
    try:
        from openai import AsyncOpenAI
        base_url = settings.LLM_CONFIG.get("deepseek_pro", {}).get("base_url", "https://api.deepseek.com")
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60)

        # 构建消息
        system_content = ANALYSIS_SYSTEM_PROMPT + "\n\n【重要】回答时请注意：" + \
            "1. 不要提及任何文章的具体标题（包括书名号《》内的内容）。" + \
            "2. 不要提及任何公众号名称或作者名称。" + \
            "3. 直接给出观点和结论，让用户感受到专业性。"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{fund_context}\n\n{internal_context}\n\n请给出投研分析报告。"}
        ]

        response = await client.chat.completions.create(
            model=settings.LLM_CONFIG.get("deepseek_pro", {}).get("model", "deepseek-v4-pro"),
            messages=messages,
            temperature=0.3,
            max_tokens=3000
        )

        raw_answer = response.choices[0].message.content
        ai_content = _sanitize_citations(raw_answer)

        # 6. 解析 JSON
        parsed = _parse_llm_json(ai_content)
        if parsed:
            scores = parsed.get("scores", _default_scores())
            metrics = parsed.get("metrics", _default_metrics())
            conclusion = parsed.get("conclusion", _default_conclusion())
        else:
            # JSON 解析失败，从文本中提取信息
            logger.warning("LLM 返回非标准 JSON，使用 fallback 解析")
            scores = _default_scores()
            metrics = _default_metrics()
            conclusion = {
                "highlights": ai_content[:300] + "..." if len(ai_content) > 300 else ai_content,
                "risks": "AI返回格式异常，以上为原始分析内容。",
                "suggestion": "建议刷新重试或联系管理员。",
            }

        # 置信度
        avg_score = sum(r.score for r in rag_results) / len(rag_results) if rag_results else 0
        confidence = "high" if avg_score > 0.75 else "medium" if avg_score > 0.6 else "low"
        sources = _build_public_sources(rag_results, confidence)

        return FundAnalysisResponse(
            success=True,
            scores=scores,
            metrics=metrics,
            conclusion=conclusion,
            sources=sources,
            message=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return FundAnalysisResponse(
            success=False,
            scores=_default_scores(),
            metrics=_default_metrics(),
            conclusion=_default_conclusion(),
            sources=[],
            message=f"AI 分析暂时不可用: {str(e)}"
        )
