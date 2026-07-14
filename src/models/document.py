"""
统一 Document 数据结构
全项目唯一的数据契约，所有 Importer 的 load_documents() 都返回此类型
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4


@dataclass
class Document:
    """知识库中的一篇文档

    Attributes:
        id:         唯一标识符（UUID）
        title:      文档标题
        path:       文件相对路径（如 "Python/async_basics.md"）
        content:    文档正文（Markdown 原文）
        source:     数据来源标记（如 "markdown", "yuque", "notion"）
        updated_at: 文档最后修改时间（ISO 8601 格式字符串）
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    path: str = ""
    content: str = ""
    source: str = "unknown"
    updated_at: str = ""

    @staticmethod
    def from_markdown_file(filepath: Path, base_dir: Path) -> "Document":
        """从本地 Markdown 文件创建 Document"""
        content = filepath.read_text(encoding="utf-8")
        relative = filepath.relative_to(base_dir)
        stat = filepath.stat()

        return Document(
            title=filepath.stem,
            path=str(relative),
            content=content,
            source="markdown",
            updated_at=datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )

    def to_dict(self) -> dict:
        return asdict(self)
