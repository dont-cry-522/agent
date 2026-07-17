"""
storage — 持久化层
=================

SQLAlchemy + SQLite，管理 Conversation 和 Message 的存储。

组件：
    database.py   — engine / Session 单例
    models.py     — ORM 模型
    repository.py — CRUD 操作封装
"""

from storage.database import get_session, init_db
from storage.models import Conversation, Message
from storage.repository import ConversationRepository, MessageRepository
