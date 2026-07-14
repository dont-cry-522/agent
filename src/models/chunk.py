"""
Chunk 数据模型
每个 Chunk 代表一篇 Document 的切片片段，保留与原文档的关联
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from uuid import uuid4


@dataclass
class Chunk:
    """文档切片片段

    Attributes:
        chunk_id:           切片唯一标识符
        document_id:        所属文档的 ID，用于回溯原文
        title:              文档标题（冗余存储，方便检索时展示）
        path:                文档路径
        chunk_content:       切片文本内容 ← 只对此字段做 Embedding
        chunk_index:         切片在文档中的序号（从 0 开始）
        source:              数据来源标记
        context_heading:     切片所属的最近标题（Markdown heading）
        context_doc_title:   所属文档标题
        context_prev_chunk:  前一个 Chunk 的末尾摘要
        context_next_chunk:  后一个 Chunk 的开头摘要
        context_full_path:   完整路径
    """

    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    document_id: str = ""
    title: str = ""
    path: str = ""
    chunk_content: str = ""
    chunk_index: int = 0
    source: str = "markdown"
    context_heading: str = ""
    context_doc_title: str = ""
    context_prev_chunk: str = ""
    context_next_chunk: str = ""
    context_full_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
