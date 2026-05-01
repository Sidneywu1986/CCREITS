#!/usr/bin/env python3
"""
Agents 剧场秀 API
前端读取剧场秀内容展示
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import date
import logging

from core.db import get_conn

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
logger = logging.getLogger(__name__)


@router.get("/shows")
def get_shows(show_date: Optional[str] = None):
    """查询某天所有剧场秀"""
    target_date = show_date or date.today().isoformat()
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT slot_id, slot_name, content, created_at
                FROM business.agent_shows
                WHERE show_date = %s
                ORDER BY created_at DESC
            ''', (target_date,))
            rows = [dict(r) for r in cur.fetchall()]
        return {
            "date": target_date,
            "total": len(rows),
            "shows": rows
        }
    except psycopg2.Error as e:
        logger.error(f"Get shows failed: {e}")
        return {"date": target_date, "total": 0, "shows": [], "error": "获取节目列表失败"}


@router.get("/shows/latest")
def get_latest_show(slot_id: Optional[str] = None):
    """查询最新剧场秀"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            if slot_id:
                cur.execute('''
                    SELECT slot_id, slot_name, content, created_at, show_date
                    FROM business.agent_shows
                    WHERE slot_id = %s
                    ORDER BY show_date DESC, created_at DESC
                    LIMIT 1
                ''', (slot_id,))
            else:
                cur.execute('''
                    SELECT slot_id, slot_name, content, created_at, show_date
                    FROM business.agent_shows
                    ORDER BY show_date DESC, created_at DESC
                    LIMIT 1
                ''')
            row = cur.fetchone()
            if row:
                return dict(row)
            return {"message": "No show found"}
    except psycopg2.Error as e:
        logger.error(f"Get latest show failed: {e}")
        return {"error": "获取最新节目失败"}
