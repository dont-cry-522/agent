"""
BGEReranker — Cross-encoder 重排序模块

职责：
  - 使用 Cross-encoder 模型对查询-文档对做精细相关性评分
  - 对 Recall 阶段返回的 Top-N 候选重新排序

设计要点：
  - 与 Retriever 完全解耦：Retriever 负责 Recall，Reranker 负责 Ranking
  - 懒加载模型，首次调用时下载
  - 输入 SearchResult 列表，输出带 rerank_score 的 SearchResult 列表

为什么独立：
  - Recall 和 Ranking 是不同的技术策略，不应耦合
  - 日后可替换不同 Reranker 模型（bge-reranker → Cohere Rerank API）
  - 可独立评估 Rerank 质量
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from src.retriever.retriever import SearchResult
from src.config import settings


class BGEReranker:
    """BGE Cross-encoder 重排序器

    默认模型: BAAI/bge-reranker-v2-m3
      - 多语言，中文优化
      - 基于 XLM-RoBERTa，约 2.2GB
    """

    def __init__(
        self,
        model_name: str | None = None,
    ):
        self._model_name = model_name or getattr(
            settings, "reranker_model_name", "BAAI/bge-reranker-v2-m3"
        )
        self._model: CrossEncoder | None = None

    def _load_model(self) -> CrossEncoder:
        if self._model is None:
            print(f"[load] Reranker 模型: {self._model_name} ...")
            self._model = CrossEncoder(self._model_name)
            self._model.predict([("预热", "预热")])
            print("   [OK] Reranker 加载完成")
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """对候选列表重新排序

        Args:
            query: 用户原始问题
            candidates: Recall 阶段返回的候选结果
            top_k: 最终返回数量

        Returns:
            重新排序后的 Top-K SearchResult，每个结果附带 rerank_score
        """
        if not candidates:
            return []

        model = self._load_model()

        pairs = [(query, c.chunk_content) for c in candidates]
        scores = model.predict(pairs)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()

        for i, candidate in enumerate(candidates):
            candidate.rerank_score = round(float(scores[i]), 4)

        candidates.sort(key=lambda x: x.rerank_score, reverse=True)
        return candidates[:top_k]
