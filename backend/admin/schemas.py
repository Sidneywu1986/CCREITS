"""
Pydantic schemas for admin auth API
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    permissions: List[str] = []


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterResponse(BaseModel):
    code: int = 201
    message: str = "注册成功"
    data: Optional[dict] = None


class RefreshResponse(BaseModel):
    code: int = 200
    message: str = "刷新成功"
    data: Optional[dict] = None


class LogoutResponse(BaseModel):
    code: int = 200
    message: str = "已登出"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class MeResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[UserInfo] = None
