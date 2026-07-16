"""
BM25Retriever — BM25 关键词检索器

职责：
  - 基于 rank-bm25 + jieba 分词做关键词检索
  - 初始化时构建语料库（tokenize 所有 Chunk）
  - search() 返回 (metadata, bm25_score) 列表

设计要点：
  - 中文使用 jieba 分词，英文按空格分词
  - BM25Okapi 不依赖训练，天然处理 OOV 词汇
  - 返回格式与 FAISSVectorStore.search() 一致，方便 RRF 融合
"""

from __future__ import annotations

from typing import Optional

import jieba
from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25 关键词检索器"""

    def __init__(self, chunks: list[dict]):
        """
        Args:
            chunks: Chunk 字典列表（与 metadata.json 同结构）
        """
        self._chunks = chunks
        self._corpus_tokens = [self._tokenize(c["chunk_content"]) for c in chunks]
        self._bm25 = self._build_bm25()

    def _build_bm25(self):
        """构建 BM25 索引，空语料时返回 None"""
        valid = [tokens for tokens in self._corpus_tokens if tokens]
        if not valid:
            return None
        try:
            return BM25Okapi(self._corpus_tokens)
        except (ValueError, ZeroDivisionError):
            return None

    def search(self, query: str, top_k: int = 5) -> list[tuple[dict, float]]:
        if self._bm25 is None:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [(self._chunks[idx], float(score)) for idx, score in ranked if score > 0]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        if not text.strip():
            return []
        chinese_words = list(jieba.cut(text))
        result = []
        for word in chinese_words:
            word = word.strip()
            if not word:
                continue
            if any('\u4e00' <= ch <= '\u9fff' for ch in word):
                result.append(word)
            else:
                result.extend(word.split())
        return [t for t in result if t]

    def rebuild(self, chunks: list[dict]) -> None:
        """从 chunk 列表全量重建 BM25 语料库"""
        self._chunks = chunks
        self._corpus_tokens = [self._tokenize(c["chunk_content"]) for c in chunks]
        self._bm25 = self._build_bm25()

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)
