"""
FAISSVectorStore — FAISS 向量索引管理（支持增量删除）

职责：
  - 创建 / 加载 / 保存 FAISS 索引
  - Top-K 相似检索（内积 = 余弦相似度）
  - 增量增删向量（IndexIDMap + remove_ids）
  - 管理与 FAISS 索引对应的 metadata

设计要点：
  - IndexIDMap(IndexFlatIP)：支持 add_with_ids / remove_ids
  - 每个 vector 分配一个整数 ID，对应 metadata 中的位置
  - 删除后 metadata 不留空洞，compact 后 ID 重新对齐
  - 纯 CPU 运行，无需 GPU
"""

from __future__ import annotations

import json
import uuid as _uuid
from pathlib import Path
from typing import Optional

import faiss
import numpy as np


class FAISSVectorStore:
    """FAISS 向量存储，管理索引和元数据（支持增量删除）"""

    def __init__(self, index_dir: str | Path = "output"):
        self.index_dir = Path(index_dir)
        self._index: Optional[faiss.Index] = None
        self._metadata: list[dict] = []
        self._next_id: int = 0

    # ── 路径 ─────────────────────────────────

    @property
    def index_path(self) -> Path:
        return self.index_dir / "index.faiss"

    @property
    def metadata_path(self) -> Path:
        return self.index_dir / "metadata.json"

    # ── 创建索引 ─────────────────────────────

    def build(
        self,
        embeddings: list[list[float]],
        metadata: list[dict],
    ) -> None:
        if not embeddings:
            raise ValueError("embeddings 不能为空")
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"embeddings 数量 ({len(embeddings)}) 与 "
                f"metadata 数量 ({len(metadata)}) 不匹配"
            )

        dim = len(embeddings[0])
        vectors = np.array(embeddings, dtype=np.float32)
        ids = np.arange(len(vectors), dtype=np.int64)

        base_index = faiss.IndexFlatIP(dim)
        self._index = faiss.IndexIDMap(base_index)
        self._index.add_with_ids(vectors, ids)
        self._metadata = list(metadata)
        self._next_id = len(metadata)

    # ── 检索 ─────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[dict, float]]:
        if self._index is None or self._index.ntotal == 0:
            return []

        vector = np.array([query_embedding], dtype=np.float32)
        scores, indices = self._index.search(vector, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            # idx 是 add_with_ids 时分配的整数 ID
            if 0 <= int(idx) < len(self._metadata):
                results.append((self._metadata[int(idx)], float(score)))
        return results

    # ── 持久化 ───────────────────────────────

    def save(self) -> None:
        if self._index is None:
            return

        self.index_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(self.index_path))
        self.index_path.chmod(0o644)

        self.metadata_path.write_text(
            json.dumps(self._metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[save] 已保存: {self._index.ntotal} 条向量 -> {self.index_path}")
        print(f"[save] 已保存: {len(self._metadata)} 条元数据 -> {self.metadata_path}")

    def load(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False

        index = faiss.read_index(str(self.index_path))
        self._metadata = json.loads(
            self.metadata_path.read_text(encoding="utf-8")
        )

        # 向后兼容：旧版 IndexFlatIP → 新版 IndexIDMap
        if not isinstance(index, faiss.IndexIDMap):
            dim = index.d
            n = index.ntotal
            vectors = np.zeros((n, dim), dtype=np.float32)
            for i in range(n):
                vectors[i] = index.reconstruct(i)
            ids = np.arange(n, dtype=np.int64)
            new_index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
            new_index.add_with_ids(vectors, ids)
            self._index = new_index
        else:
            self._index = index

        self._next_id = len(self._metadata)

        print(f"[load] 已加载: {self._index.ntotal} 条向量 <- {self.index_path}")
        return True

    # ── 增量追加 ─────────────────────────────

    def add_vectors(
        self,
        embeddings: list[list[float]],
        metadata: list[dict],
    ) -> None:
        if not embeddings:
            return
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"embeddings 数量 ({len(embeddings)}) 与 "
                f"metadata 数量 ({len(metadata)}) 不匹配"
            )

        vectors = np.array(embeddings, dtype=np.float32)
        ids = np.arange(self._next_id, self._next_id + len(vectors), dtype=np.int64)

        self._index.add_with_ids(vectors, ids)
        self._metadata.extend(metadata)
        self._next_id += len(vectors)

    # ── 增量删除 ─────────────────────────────

    def remove_vectors(self, ids: list[int]) -> int:
        """按 FAISS 内部 ID 删除向量，同时清理 metadata

        Returns:
            删除的向量数
        """
        if self._index is None or not ids:
            return 0

        remove_arr = np.array(ids, dtype=np.int64)
        before = self._index.ntotal
        self._index.remove_ids(remove_arr)
        removed = before - self._index.ntotal

        # 标记 metadata 中的对应条目为 None（compact 时跳过）
        for idx in ids:
            if 0 <= idx < len(self._metadata):
                self._metadata[idx] = None  # type: ignore

        return removed

    def remove_by_document_id(self, document_id: str) -> int:
        """按 document_id 删除所有相关向量（增量式，不重建）

        Returns:
            删除的 chunk 数量
        """
        if self._index is None:
            return 0

        ids_to_remove: list[int] = []
        for i, meta in enumerate(self._metadata):
            if meta is not None and meta.get("document_id") == document_id:
                ids_to_remove.append(i)

        return self.remove_vectors(ids_to_remove)

    # ── 全量重建 ─────────────────────────────

    def rebuild_from_metadata(
        self,
        provider,  # EmbeddingProvider
    ) -> int:
        """从 metadata 全量重建 FAISS 索引。compact 删除后的空洞。

        Returns:
            重建后的向量总数
        """
        compact = [m for m in self._metadata if m is not None]
        if not compact:
            self._index = None
            self._metadata = []
            self._next_id = 0
            return 0

        texts = [m["chunk_content"] for m in compact]
        embeddings = provider.embed_documents(texts)
        self.build(embeddings, compact)
        return self._index.ntotal

    # ── 属性 ─────────────────────────────────

    @property
    def metadata(self) -> list[dict]:
        """返回元数据列表（只读）"""
        return list(self._metadata)

    @property
    def count(self) -> int:
        """返回索引中的向量总数"""
        return self._index.ntotal if self._index else 0
