"""
Retriever — 检索模块（支持 Hybrid Search）

职责：
  - 接收用户问题
  - 调用 EmbeddingProvider 向量化 → FAISS 向量检索
  - 调用 BM25Retriever 关键词检索
  - RRF（Reciprocal Rank Fusion）融合两路结果
  - 返回 SearchResult 列表

独立出来的原因：
  - 检索是一个独立职责，不耦合 Prompt 拼接或 LLM 调用
  - 日后替换向量库（如 FAISS → Milvus），只需修改本模块
  - 可独立测试检索质量，不依赖 LLM
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.embedding.provider import EmbeddingProvider
from src.vectorstore.faiss_store import FAISSVectorStore
from src.retriever.bm25 import BM25Retriever


@dataclass
class SearchResult:
    chunk_id: str = ""
    document_id: str = ""
    title: str = ""
    path: str = ""
    chunk_content: str = ""
    chunk_index: int = 0
    source: str = ""
    score: float = 0.0
    bm25_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    context_heading: str = ""
    context_doc_title: str = ""
    context_prev_chunk: str = ""
    context_next_chunk: str = ""
    context_full_path: str = ""

    @classmethod
    def from_metadata(cls, meta: dict, score: float) -> "SearchResult":
        return cls(
            chunk_id=meta.get("chunk_id", ""),
            document_id=meta.get("document_id", ""),
            title=meta.get("title", ""),
            path=meta.get("path", ""),
            chunk_content=meta.get("chunk_content", ""),
            chunk_index=meta.get("chunk_index", 0),
            source=meta.get("source", ""),
            score=score,
            context_heading=meta.get("context_heading", ""),
            context_doc_title=meta.get("context_doc_title", ""),
            context_prev_chunk=meta.get("context_prev_chunk", ""),
            context_next_chunk=meta.get("context_next_chunk", ""),
            context_full_path=meta.get("context_full_path", ""),
        )

    @property
    def summary(self) -> str:
        return self.chunk_content[:200] + ("..." if len(self.chunk_content) > 200 else "")


class Retriever:
    """检索器：embed → [FAISS + BM25] → RRF fusion → results"""

    RRF_K: int = 60

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        embedding_provider: EmbeddingProvider,
        bm25_retriever: Optional[BM25Retriever] = None,
    ):
        self._store = vector_store
        self._provider = embedding_provider
        self._bm25 = bm25_retriever

    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._bm25 is None:
            return self._vector_retrieve(query, top_k)
        return self._hybrid_retrieve(query, top_k)

    # ── 纯向量检索（无 BM25 时回退） ──

    def _vector_retrieve(self, query: str, top_k: int) -> list[SearchResult]:
        query_vec = self._provider.embed_query(query)
        raw_results = self._store.search(query_vec, top_k=top_k)
        return [SearchResult.from_metadata(meta, score) for meta, score in raw_results]

    # ── 混合检索 + RRF ──

    def _hybrid_retrieve(self, query: str, top_k: int) -> list[SearchResult]:
        search_k = max(top_k * 2, 10)

        vec_results = self._vector_retrieve_raw(query, search_k)
        bm25_results = self._bm25.search(query, top_k=search_k)
        return self._rrf_fuse(vec_results, bm25_results, top_k)

    def _vector_retrieve_raw(
        self, query: str, top_k: int
    ) -> list[tuple[dict, float]]:
        query_vec = self._provider.embed_query(query)
        return self._store.search(query_vec, top_k=top_k)

    def _rrf_fuse(
        self,
        vec_results: list[tuple[dict, float]],
        bm25_results: list[tuple[dict, float]],
        top_k: int,
    ) -> list[SearchResult]:
        chunk_map: dict[str, dict] = {}

        for rank, (meta, score) in enumerate(vec_results):
            cid = meta["chunk_id"]
            chunk_map[cid] = {
                "meta": meta,
                "vector_score": score,
                "vector_rank": rank + 1,
                "bm25_score": None,
                "bm25_rank": None,
            }

        for rank, (meta, score) in enumerate(bm25_results):
            cid = meta["chunk_id"]
            if cid in chunk_map:
                chunk_map[cid]["bm25_score"] = score
                chunk_map[cid]["bm25_rank"] = rank + 1
            else:
                chunk_map[cid] = {
                    "meta": meta,
                    "vector_score": None,
                    "vector_rank": None,
                    "bm25_score": score,
                    "bm25_rank": rank + 1,
                }

        fused = []
        for data in chunk_map.values():
            rrf = 0.0
            if data["vector_rank"] is not None:
                rrf += 1.0 / (self.RRF_K + data["vector_rank"])
            if data["bm25_rank"] is not None:
                rrf += 1.0 / (self.RRF_K + data["bm25_rank"])

            result = SearchResult.from_metadata(
                data["meta"], data["vector_score"] or 0.0
            )
            result.bm25_score = round(data["bm25_score"] or 0.0, 4)
            result.fusion_score = round(rrf, 4)
            fused.append(result)

        fused.sort(key=lambda x: x.fusion_score, reverse=True)
        return fused[:top_k]
