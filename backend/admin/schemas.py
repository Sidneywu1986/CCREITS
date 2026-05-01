"""
Pydantic schemas for admin API
"""

from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
