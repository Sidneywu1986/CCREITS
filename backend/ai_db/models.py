"""
AI Database Models (Tortoise ORM)
PostgreSQL tables for AI chat, research, and content management
"""

from tortoise import fields
from tortoise.models import Model


class AiChatSession(Model):
    """AI聊天会话表"""
    id = fields.IntField(pk=True)
    session_title = fields.CharField(max_length=255, null=True)
    session_type = fields.CharField(max_length=50, default='general')
    user_id = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ai_chat_sessions"


class AiChatMessage(Model):
    """AI聊天消息表"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.AiChatSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    model = fields.CharField(max_length=50, null=True)
    tokens = fields.IntField(null=True)
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ai_chat_messages"


class AiChatAgent(Model):
    """AI智能体配置表"""
    id = fields.IntField(pk=True)
    agent_name = fields.CharField(max_length=100, unique=True)
    agent_desc = fields.TextField(null=True)
    system_prompt = fields.TextField()
    model = fields.CharField(max_length=50, default='deepseek')
    temperature = fields.FloatField(default=0.7)
    max_tokens = fields.IntField(default=2000)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ai_chat_agents"


class AnnouncementChatSession(Model):
    """公告聊天会话表"""
    id = fields.IntField(pk=True)
    session_title = fields.CharField(max_length=255, null=True)
    user_id = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "announcement_chat_sessions"


class AnnouncementChatMessage(Model):
    """公告聊天消息表"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.AnnouncementChatSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "announcement_chat_messages"


class AnnouncementChatContext(Model):
    """公告聊天上下文关联表"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.AnnouncementChatSession", related_name="contexts")
    announcement_id = fields.IntField()
    relevance_score = fields.FloatField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "announcement_chat_contexts"


class ResearchSession(Model):
    """投研会话表"""
    id = fields.IntField(pk=True)
    session_title = fields.CharField(max_length=255, null=True)
    user_id = fields.IntField(null=True)
    status = fields.CharField(max_length=20, default='active')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "research_sessions"


class ResearchMessage(Model):
    """投研消息表"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.ResearchSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_messages"


class ResearchFund(Model):
    """投研基金关联表"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.ResearchSession", related_name="funds")
    fund_code = fields.CharField(max_length=20)
    fund_name = fields.CharField(max_length=100, null=True)
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_funds"


class ResearchResult(Model):
    """投研结果表（结构化分段存储）"""
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("ai_db.ResearchSession", related_name="results")
    analysis_type = fields.CharField(max_length=50)
    conclusion = fields.TextField()
    supporting_data = fields.JSONField(null=True)
    references = fields.JSONField(null=True)
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_results"


class AnnouncementContent(Model):
    """公告内容表（解析后的公告原文）"""
    id = fields.IntField(pk=True)
    announcement_id = fields.IntField(unique=True)
    title = fields.CharField(max_length=500, null=True)
    content = fields.TextField(null=True)
    summary = fields.TextField(null=True)
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "announcement_contents"


class SocialHotspot(Model):
    """社会热点表"""
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    content = fields.TextField(null=True)
    source = fields.CharField(max_length=100, null=True)
    url = fields.CharField(max_length=500, null=True)
    heat_score = fields.IntField(default=0)
    keywords = fields.JSONField(null=True)
    fulltext_vector = fields.JSONField(null=True)
    published_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "social_hotspots"


class Article(Model):
    """公众号/研报文章表"""
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=500)
    content = fields.TextField(null=True)
    author = fields.CharField(max_length=100, null=True)
    source = fields.CharField(max_length=100, null=True)
    article_type = fields.CharField(max_length=50, null=True)
    url = fields.CharField(max_length=500, null=True)
    published_at = fields.DatetimeField(null=True)
    fulltext_vector = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "articles"


class VectorPending(Model):
    """向量待处理队列表"""
    id = fields.IntField(pk=True)
    content_type = fields.CharField(max_length=50)
    content_id = fields.CharField(max_length=100)
    original_content = fields.TextField(null=True)
    status = fields.CharField(max_length=20, default='pending')
    retry_count = fields.IntField(default=0)
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    processed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "vector_pending"


class CrawlErrorLog(Model):
    """爬虫错误日志表"""
    id = fields.IntField(pk=True)
    crawler_name = fields.CharField(max_length=100)
    error_type = fields.CharField(max_length=50, null=True)
    error_message = fields.TextField(null=True)
    url = fields.CharField(max_length=500, null=True)
    stack_trace = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "crawl_error_logs"
