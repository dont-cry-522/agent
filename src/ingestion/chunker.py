"""
DocumentChunker — 将 Document 切分为 Chunk 列表

使用 LangChain RecursiveCharacterTextSplitter 做语义切片：
  先按段落（\n\n）切，段落太长按句子（。），还太长按字符切
  重叠窗口保证相邻 Chunk 有上下文衔接，避免关键信息被切断

设计要点：
  - 纯函数设计：不存储状态，输入 Document，输出 Chunk 列表
  - chunk_size / chunk_overlap 可配置，适应不同场景
  - 每个 Chunk 保留与父 Document 的关联（document_id）
  - 上下文增强：自动解析标题、填充前后 Chunk 摘要、完整路径
"""

from __future__ import annotations

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.models.document import Document
from src.models.chunk import Chunk


class DocumentChunker:
    """文档切片器，将 Document 切分为语义完整的 Chunk"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        prev_summary_length: int = 100,
        next_summary_length: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.prev_summary_length = prev_summary_length
        self.next_summary_length = next_summary_length

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",     # 段落
                "\n",       # 换行
                "。",        # 中文句号
                "！",        # 中文感叹号
                "？",        # 中文问号
                ".",        # 英文句号
                "!",
                "?",
                "；",
                ";",
                "，",
                ",",
                " ",
                "",
            ],
            length_function=len,
        )

    def split(self, document: Document) -> list[Chunk]:
        """将单篇 Document 切分为 Chunk 列表，自动填充上下文信息"""
        raw_texts = self._splitter.split_text(document.content)
        if not raw_texts:
            return []

        headings = self._parse_headings(document.content)

        chunks = []
        search_from = 0

        for i, raw_text in enumerate(raw_texts):
            stripped = raw_text.strip()
            if not stripped:
                continue

            pos = self._find_chunk_position(document.content, stripped, search_from)
            search_from = pos + 1 if pos >= 0 else search_from

            context_heading = self._resolve_heading(headings, pos)

            prev_summary = ""
            next_summary = ""
            if i > 0 and raw_texts[i - 1].strip():
                prev_summary = raw_texts[i - 1].strip()[-self.prev_summary_length:]
            if i < len(raw_texts) - 1 and raw_texts[i + 1].strip():
                next_summary = raw_texts[i + 1].strip()[:self.next_summary_length]

            chunks.append(Chunk(
                document_id=document.id,
                title=document.title,
                path=document.path,
                chunk_content=stripped,
                chunk_index=len(chunks),
                source=document.source,
                context_heading=context_heading,
                context_doc_title=document.title,
                context_prev_chunk=prev_summary,
                context_next_chunk=next_summary,
                context_full_path=document.path,
            ))

        return chunks

    def split_documents(self, documents: list[Document]) -> list[Chunk]:
        """批量切分多篇 Document"""
        all_chunks = []
        for doc in documents:
            chunks = self.split(doc)
            all_chunks.extend(chunks)
        return all_chunks

    # ── 内部辅助 ─────────────────────────────

    @staticmethod
    def _parse_headings(content: str) -> list[tuple[int, str]]:
        """解析文档中所有 Markdown 标题，返回 [(位置, 标题文本), ...]"""
        headings = []
        for m in re.finditer(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE):
            headings.append((m.start(), m.group(2).strip()))
        return headings

    @staticmethod
    def _find_chunk_position(content: str, chunk_text: str, search_from: int) -> int:
        """在文档中找到 chunk_text 的起始位置"""
        pos = content.find(chunk_text, search_from)
        if pos == -1:
            pos = content.find(chunk_text)
        return pos

    @staticmethod
    def _resolve_heading(
        headings: list[tuple[int, str]], chunk_pos: int
    ) -> str:
        """找到 chunk 位置之前最近的标题"""
        if chunk_pos < 0:
            return ""
        resolved = ""
        for h_pos, h_text in headings:
            if h_pos < chunk_pos:
                resolved = h_text
            else:
                break
        return resolved
