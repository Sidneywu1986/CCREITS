"""
Fund business logic — extracted from routes/funds.py
"""
from typing import List, Optional, Dict
import asyncpg


class FundService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def list_funds(
        self,
        page: int = 1,
        limit: int = 20,
        search: str = "",
        exchange: str = "",
        status: str = "",
    ) -> Dict:
        """Paginated fund list with filters."""
        conn = await asyncpg.connect(self.db_url)
        try:
            offset = (page - 1) * limit
            params = []
            conditions = ["1=1"]

            if search:
                conditions.append("(fund_code ILIKE $1 OR fund_name ILIKE $1)")
                params.append(f"%{search}%")
            if exchange:
                conditions.append(f"exchange = ${len(params)+1}")
                params.append(exchange)
            if status:
                conditions.append(f"status = ${len(params)+1}")
                params.append(status)

            where_clause = " AND ".join(conditions)

            # Count
            count_sql = f"SELECT COUNT(*) FROM business.funds WHERE {where_clause}"
            total = await conn.fetchval(count_sql, *params)

            # Data
            data_sql = f"""
                SELECT * FROM business.funds
                WHERE {where_clause}
                ORDER BY fund_code
                LIMIT ${len(params)+1} OFFSET ${len(params)+2}
            """
            params.extend([limit, offset])
            rows = await conn.fetch(data_sql, *params)

            return {
                "total": total,
                "page": page,
                "limit": limit,
                "items": [dict(r) for r in rows],
            }
        finally:
            await conn.close()

    async def get_fund(self, fund_id: int) -> Optional[Dict]:
        """Get single fund by ID."""
        conn = await asyncpg.connect(self.db_url)
        try:
            row = await conn.fetchrow("SELECT * FROM business.funds WHERE id = $1", fund_id)
            return dict(row) if row else None
        finally:
            await conn.close()

    async def create_fund(self, data: Dict) -> int:
        """Create new fund. Returns new fund ID."""
        conn = await asyncpg.connect(self.db_url)
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
            sql = f"INSERT INTO business.funds ({columns}) VALUES ({placeholders}) RETURNING id"
            fund_id = await conn.fetchval(sql, *data.values())
            return fund_id
        finally:
            await conn.close()

    async def update_fund(self, fund_id: int, data: Dict) -> bool:
        """Update fund. Returns True if updated."""
        conn = await asyncpg.connect(self.db_url)
        try:
            sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(data.keys()))
            sql = f"UPDATE business.funds SET {sets} WHERE id = $1"
            result = await conn.execute(sql, fund_id, *data.values())
            return "UPDATE 1" in result
        finally:
            await conn.close()

    async def delete_fund(self, fund_id: int) -> bool:
        """Delete fund. Returns True if deleted."""
        conn = await asyncpg.connect(self.db_url)
        try:
            result = await conn.execute("DELETE FROM business.funds WHERE id = $1", fund_id)
            return "DELETE 1" in result
        finally:
            await conn.close()
