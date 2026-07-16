"""
FAISSVectorStore — FAISS 向量索引管理

职责：
  - 创建 / 加载 / 保存 FAISS 索引
  - Top-K 相似检索（内积 = 余弦相似度）
  - 管理与 FAISS 索引对应的 metadata（不在 FAISS 内部存储文本）

FAISS 内部只存 float32 向量数组，通过 search 返回的位置索引
来映射到 metadata 中对应的 Chunk 信息。

设计要点：
  - IndexFlatIP：内积索引，配合 L2-normalized 向量等价于余弦相似度
  - metadata 独立于 FAISS，方便查看、修改、迁移
  - 纯 CPU 运行，无需 GPU
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import faiss
import numpy as np


class FAISSVectorStore:
    """FAISS 向量存储，管理索引和元数据"""

    def __init__(self, index_dir: str | Path = "output"):
        self.index_dir = Path(index_dir)
        self._index: Optional[faiss.IndexFlatIP] = None
        self._metadata: list[dict] = []

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
        """从 embedding 和 metadata 构建 FAISS 索引

        Args:
            embeddings: 向量列表 [N, dim]，每个向量对应一个 Chunk
            metadata:   元数据列表 [N]，与向量一一对应
        """
        if not embeddings:
            raise ValueError("embeddings 不能为空")
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"embeddings 数量 ({len(embeddings)}) 与 "
                f"metadata 数量 ({len(metadata)}) 不匹配"
            )

        dim = len(embeddings[0])
        vectors = np.array(embeddings, dtype=np.float32)

        # 内积索引：向量已 normalize，内积 = 余弦相似度
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(vectors)
        self._metadata = list(metadata)

    # ── 检索 ─────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[dict, float]]:
        """Top-K 相似检索

        Returns:
            [(metadata_dict, score), ...]  按 score 降序排列
            score 为余弦相似度，范围 0～1
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        vector = np.array([query_embedding], dtype=np.float32)
        scores, indices = self._index.search(vector, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self._metadata):
                continue
            results.append((self._metadata[idx], float(score)))
        return results

    # ── 持久化 ───────────────────────────────

    def save(self) -> None:
        """保存 FAISS 索引和 metadata 到磁盘"""
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
        """从磁盘加载 FAISS 索引和 metadata，返回是否加载成功"""
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False

        self._index = faiss.read_index(str(self.index_path))
        self._metadata = json.loads(
            self.metadata_path.read_text(encoding="utf-8")
        )

        print(f"[load] 已加载: {self._index.ntotal} 条向量 <- {self.index_path}")
        return True

    def add_vectors(
        self,
        embeddings: list[list[float]],
        metadata: list[dict],
    ) -> None:
        """增量追加向量和元数据

        Args:
            embeddings: 新向量列表 [M, dim]
            metadata:   新元数据列表 [M]
        """
        if not embeddings:
            return
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"embeddings 数量 ({len(embeddings)}) 与 "
                f"metadata 数量 ({len(metadata)}) 不匹配"
            )

        vectors = np.array(embeddings, dtype=np.float32)
        self._index.add(vectors)
        self._metadata.extend(metadata)

    def rebuild_from_metadata(
        self,
        provider,  # EmbeddingProvider, avoid circular import
    ) -> int:
        """从 metadata 全量重建 FAISS 索引和向量。用于删除操作后的重建。

        Returns:
            重建后的向量总数
        """
        if not self._metadata:
            self._index = None
            return 0

        texts = [m["chunk_content"] for m in self._metadata]
        embeddings = provider.embed_documents(texts)
        self.build(embeddings, self._metadata)
        return self._index.ntotal

    @property
    def metadata(self) -> list[dict]:
        """返回元数据列表（只读）"""
        return list(self._metadata)

    def remove_by_document_id(self, document_id: str) -> int:
        """按 document_id 移除元数据（不立刻重建 FAISS，需后续调用 rebuild_from_metadata）

        Returns:
            移除的 chunk 数量
        """
        before = len(self._metadata)
        self._metadata = [m for m in self._metadata if m.get("document_id") != document_id]
        return before - len(self._metadata)

    @property
    def count(self) -> int:
        """返回索引中的向量总数"""
        return self._index.ntotal if self._index else 0
