"""
models — ORM 数据模型
====================

Conversation: 对话容器
Message:     对话中的单条消息
DocumentRecord: 知识库文档
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid4().hex[:12]
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="新对话"
    )
    knowledge_base_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id!r} title={self.title!r}>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid4().hex[:12]
    )
    conversation_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id!r} role={self.role!r}>"


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid4().hex[:12]
    )
    filename: Mapped[str] = mapped_column(
        String(300), nullable=False
    )
    original_name: Mapped[str] = mapped_column(
        String(300), nullable=False
    )
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready"
    )
    error: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id!r} name={self.original_name!r}>"
