"""
repository — CRUD Repository 层
===============================

封装对 Conversation 和 Message 的数据库操作。

所有方法接收 Session 参数（DI），不持有全局状态。
调用方负责生命周期管理。

用法：
    from storage.database import get_session
    from storage.repository import ConversationRepository

    repo = ConversationRepository()
    with get_session() as session:
        conv = repo.create(session, title="新对话")
        convs = repo.list_all(session)
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from storage.models import Conversation, Message, DocumentRecord


class ConversationRepository:

    # ── 创建 ──

    def create(
        self,
        session: Session,
        *,
        title: str = "新对话",
        knowledge_base_id: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            id=uuid4().hex[:12],
            title=title,
            knowledge_base_id=knowledge_base_id,
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)
        return conv

    # ── 查询 ──

    def get_by_id(
        self, session: Session, conversation_id: str
    ) -> Conversation | None:
        return session.get(Conversation, conversation_id)

    def list_all(
        self, session: Session
    ) -> list[Conversation]:
        return (
            session.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    # ── 更新 ──

    def update_title(
        self, session: Session, conversation_id: str, title: str
    ) -> Conversation | None:
        conv = self.get_by_id(session, conversation_id)
        if conv is None:
            return None
        conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(conv)
        return conv

    def touch(
        self, session: Session, conversation_id: str
    ) -> None:
        conv = self.get_by_id(session, conversation_id)
        if conv is not None:
            conv.updated_at = datetime.now(timezone.utc)
            session.commit()

    # ── 删除 ──

    def delete(
        self, session: Session, conversation_id: str
    ) -> bool:
        conv = self.get_by_id(session, conversation_id)
        if conv is None:
            return False
        session.delete(conv)
        session.commit()
        return True


class MessageRepository:

    # ── 创建 ──

    def save(
        self,
        session: Session,
        *,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        msg = Message(
            id=uuid4().hex[:12],
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        session.add(msg)

        conv = session.get(Conversation, conversation_id)
        if conv is not None:
            conv.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(msg)
        return msg

    # ── 查询 ──

    def get_by_conversation(
        self,
        session: Session,
        conversation_id: str,
        *,
        limit: int | None = 50,
        offset: int = 0,
    ) -> list[Message]:
        q = (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        if limit is not None:
            q = q.limit(limit).offset(offset)
        return q.all()

    def get_recent(
        self,
        session: Session,
        conversation_id: str,
        count: int = 20,
    ) -> list[Message]:
        return (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(count)
            .all()[::-1]  # 升序返回
        )

    # ── 删除 ──

    def delete_by_conversation(
        self, session: Session, conversation_id: str
    ) -> int:
        count = (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .delete()
        )
        session.commit()
        return count


class DocumentRepository:

    def create(
        self,
        session: Session,
        *,
        id: str,
        filename: str,
        original_name: str,
        format: str,
        file_size: int,
        chunk_count: int = 0,
        status: str = "ready",
        error: str = "",
    ) -> DocumentRecord:
        doc = DocumentRecord(
            id=id,
            filename=filename,
            original_name=original_name,
            format=format,
            file_size=file_size,
            chunk_count=chunk_count,
            status=status,
            error=error,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc

    def get_by_id(
        self, session: Session, doc_id: str
    ) -> DocumentRecord | None:
        return session.get(DocumentRecord, doc_id)

    def list_all(
        self, session: Session
    ) -> list[DocumentRecord]:
        return (
            session.query(DocumentRecord)
            .order_by(DocumentRecord.created_at.desc())
            .all()
        )

    def update(
        self,
        session: Session,
        doc_id: str,
        **kwargs,
    ) -> DocumentRecord | None:
        doc = self.get_by_id(session, doc_id)
        if doc is None:
            return None
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        session.commit()
        session.refresh(doc)
        return doc

    def delete(
        self, session: Session, doc_id: str
    ) -> bool:
        doc = self.get_by_id(session, doc_id)
        if doc is None:
            return False
        session.delete(doc)
        session.commit()
        return True

    def count(self, session: Session) -> int:
        return session.query(DocumentRecord).count()

    def total_size(self, session: Session) -> int:
        result = session.query(
            __import__("sqlalchemy").func.sum(DocumentRecord.file_size)
        ).scalar()
        return result or 0
