#!/usr/bin/env python3
"""
演出时段模式API
供前端轮询当前模式、配额、倒计时
"""

from fastapi import APIRouter
from agents.show_schedule import get_schedule
from agents.butterfly_effect import get_butterfly_trigger

router = APIRouter(prefix="/api/ai", tags=["演出时段"])


@router.get("/current-mode")
async def current_mode():
    """返回当前时段模式（供前端轮询）"""
    schedule = get_schedule()
    butterfly = get_butterfly_trigger()
    slot = schedule.current_slot()
    next_slot = schedule.get_next_slot()
    
    return {
        "mode": slot.mode if slot else "freestyle",
        "slot": {
            "id": slot.slot_id,
            "name": slot.name,
            "start": slot.start.strftime("%H:%M") if hasattr(slot.start, 'strftime') else str(slot.start),
            "end": slot.end.strftime("%H:%M") if hasattr(slot.end, 'strftime') else str(slot.end),
            "user_quota": slot.user_quota,
        } if slot else None,
        "next_slot": {
            "name": next_slot.name,
            "start": next_slot.start.strftime("%H:%M"),
        } if next_slot else None,
        "countdown": schedule.countdown_to_next(),
        "butterfly_rate": round(butterfly.get_current_rate(), 2),
    }
