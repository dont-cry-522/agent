"""API schemas — Pydantic models for request/response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    conversation_id: str = Field(default="", description="对话 ID，空则自动创建")
    rerank: bool = Field(default=True, description="是否启用 Reranker")


class SearchResultItem(BaseModel):
    title: str
    path: str
    score: float
    bm25_score: float
    fusion_score: float
    rerank_score: float
    content: str
    heading: str = ""
    doc_title: str = ""


class ChatResponse(BaseModel):
    question: str
    answer: str
    conversation_id: str = ""
    rewritten_query: str = ""
    citations: list[SearchResultItem] = Field(default_factory=list)
    retrieval_ms: float = 0.0
    error: str | None = None


# ── Conversations ──────────────────────────────

class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: str = ""


class ConversationItem(BaseModel):
    id: str
    title: str
    message_count: int = 0
    updated_at: str = ""


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: list[MessageItem] = Field(default_factory=list)
    updated_at: str = ""


# ── Documents ─────────────────────────────────

class DocumentItem(BaseModel):
    id: str
    filename: str
    original_name: str
    format: str
    file_size: int
    chunk_count: int
    status: str
    error: str = ""
    created_at: str = ""


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class UploadResponse(BaseModel):
    document: DocumentItem
    message: str


class RebuildResponse(BaseModel):
    document_count: int
    chunk_count: int
    message: str


class StatsResponse(BaseModel):
    document_count: int
    chunk_count: int
    total_size: int
    index_size_bytes: int = 0
