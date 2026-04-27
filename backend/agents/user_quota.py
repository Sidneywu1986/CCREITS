#!/usr/bin/env python3
"""
用户提问配额器
日盘剧场：每人每场限1问
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from datetime import datetime
import logging

logger = logging.getLogger("user_quota")


@dataclass
class UserSession:
    user_id: str
    slot_id: str      # 当前场次
    questions_used: int = 0
    questions_max: int = 1
    asked_at: list = field(default_factory=list)


class UserQuotaManager:
    """
    管理用户在单场演出中的提问配额
    规则：日盘剧场（上/下午）每人每场限1问
    """
    
    def __init__(self):
        # {user_id: {slot_id: UserSession}}
        self.sessions: Dict[str, Dict[str, UserSession]] = {}
        self.current_slot: str = ""
    
    def update_slot(self, slot_id: str):
        """时段切换时，重置配额"""
        if slot_id != self.current_slot:
            logger.info(f"配额器切换至场次: {slot_id}")
            self.current_slot = slot_id
    
    def can_ask(self, user_id: str, slot_id: str, quota: int = 1) -> bool:
        """检查用户是否还有提问额度"""
        if quota == 0:
            return True  # 不限额时段
        
        if user_id not in self.sessions:
            self.sessions[user_id] = {}
        
        if slot_id not in self.sessions[user_id]:
            self.sessions[user_id][slot_id] = UserSession(
                user_id=user_id,
                slot_id=slot_id,
                questions_max=quota,
            )
        
        session = self.sessions[user_id][slot_id]
        return session.questions_used < session.questions_max
    
    def consume_quota(self, user_id: str, slot_id: str) -> bool:
        """消耗一次提问额度"""
        if not self.can_ask(user_id, slot_id):
            return False
        
        session = self.sessions[user_id][slot_id]
        session.questions_used += 1
        session.asked_at.append(datetime.now().isoformat())
        return True
    
    def remaining_quota(self, user_id: str, slot_id: str) -> int:
        """返回剩余额度"""
        if user_id not in self.sessions or slot_id not in self.sessions[user_id]:
            return 1  # 默认额度
        session = self.sessions[user_id][slot_id]
        return max(0, session.questions_max - session.questions_used)
    
    def get_quota_status(self, user_id: str, slot_id: str) -> Dict:
        """返回配额状态（供前端展示）"""
        remaining = self.remaining_quota(user_id, slot_id)
        return {
            "used": 1 - remaining,
            "total": 1,
            "remaining": remaining,
            "can_ask": remaining > 0,
        }


# 全局单例
_quota_manager: Optional[UserQuotaManager] = None

def get_quota_manager() -> UserQuotaManager:
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = UserQuotaManager()
    return _quota_manager
