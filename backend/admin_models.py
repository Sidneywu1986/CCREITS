"""
FastAPI-Admin 模型配置
Tortoise ORM 模型 - 映射现有数据库表
"""

from tortoise import fields
from tortoise.models import Model


class UserAdmin(Model):
    """用户管理"""
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=100, unique=True)
    password_hash = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    email_verified = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class RoleAdmin(Model):
    """角色管理"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.CharField(max_length=200, null=True)
    is_system = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "roles"


class PermissionAdmin(Model):
    """权限管理"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=100, unique=True)
    category = fields.CharField(max_length=50)
    description = fields.CharField(max_length=200, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "permissions"


class FundAdmin(Model):
    """基金管理"""
    id = fields.IntField(pk=True)
    fund_code = fields.CharField(max_length=10, unique=True)
    fund_name = fields.CharField(max_length=100)
    full_name = fields.CharField(max_length=200, null=True)
    exchange = fields.CharField(max_length=10, null=True)
    ipo_date = fields.CharField(max_length=20, null=True)
    ipo_price = fields.FloatField(null=True)
    total_shares = fields.FloatField(null=True)
    nav = fields.FloatField(null=True)
    manager = fields.CharField(max_length=100, null=True)
    custodian = fields.CharField(max_length=100, null=True)
    asset_type = fields.CharField(max_length=50, null=True)
    underlying_assets = fields.TextField(null=True)
    status = fields.CharField(max_length=20, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "funds"


class AnnouncementAdmin(Model):
    """公告管理"""
    id = fields.IntField(pk=True)
    fund_code = fields.CharField(max_length=10)
    fund_name = fields.CharField(max_length=100, null=True)
    title = fields.CharField(max_length=500)
    content = fields.TextField(null=True)
    source = fields.CharField(max_length=50, null=True)
    source_url = fields.CharField(max_length=500, null=True)
    publish_date = fields.CharField(max_length=20, null=True)
    category = fields.CharField(max_length=50, null=True)
    announcement_type = fields.CharField(max_length=50, null=True)
    pdf_url = fields.CharField(max_length=500, null=True)
    is_processed = fields.BooleanField(default=False)
    is_important = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "announcements"
        indexes = ["fund_code", "publish_date"]


class DailyDataAdmin(Model):
    """日线数据管理"""
    id = fields.IntField(pk=True)
    fund_code = fields.CharField(max_length=20)
    trade_date = fields.DateField()
    open_price = fields.FloatField(null=True)
    close_price = fields.FloatField(null=True)
    high = fields.FloatField(null=True)
    low = fields.FloatField(null=True)
    volume = fields.FloatField(null=True)
    amount = fields.FloatField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "daily_data"


class DividendAdmin(Model):
    """分红管理"""
    id = fields.IntField(pk=True)
    fund_code = fields.CharField(max_length=20)
    dividend_date = fields.DateField()
    dividend_amount = fields.FloatField()
    record_date = fields.DateField(null=True)
    ex_dividend_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dividends"
