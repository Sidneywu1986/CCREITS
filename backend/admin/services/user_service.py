"""
User business logic — extracted from routes/users.py / routes/funds.py
"""
from typing import List, Optional, Dict
import asyncpg


class UserService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def list_users(self, page: int = 1, limit: int = 20) -> Dict:
        conn = await asyncpg.connect(self.db_url)
        try:
            offset = (page - 1) * limit
            total = await conn.fetchval("SELECT COUNT(*) FROM admin.users")
            rows = await conn.fetch(
                "SELECT id, username, email, is_active, is_superuser, created_at FROM admin.users ORDER BY id LIMIT $1 OFFSET $2",
                limit, offset
            )
            return {"total": total, "page": page, "limit": limit, "items": [dict(r) for r in rows]}
        finally:
            await conn.close()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        conn = await asyncpg.connect(self.db_url)
        try:
            row = await conn.fetchrow(
                "SELECT id, username, email, is_active, is_superuser, created_at FROM admin.users WHERE id = $1",
                user_id
            )
            return dict(row) if row else None
        finally:
            await conn.close()

    async def create_user(self, username: str, email: str, password_hash: str, is_superuser: bool = False) -> int:
        conn = await asyncpg.connect(self.db_url)
        try:
            user_id = await conn.fetchval(
                "INSERT INTO admin.users (username, email, password_hash, is_active, is_superuser) VALUES ($1, $2, $3, true, $4) RETURNING id",
                username, email, password_hash, is_superuser
            )
            return user_id
        finally:
            await conn.close()

    async def update_user(self, user_id: int, data: Dict) -> bool:
        conn = await asyncpg.connect(self.db_url)
        try:
            sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(data.keys()))
            sql = f"UPDATE admin.users SET {sets} WHERE id = $1"
            result = await conn.execute(sql, user_id, *data.values())
            return "UPDATE 1" in result
        finally:
            await conn.close()

    async def delete_user(self, user_id: int) -> bool:
        conn = await asyncpg.connect(self.db_url)
        try:
            result = await conn.execute("DELETE FROM admin.users WHERE id = $1", user_id)
            return "DELETE 1" in result
        finally:
            await conn.close()
