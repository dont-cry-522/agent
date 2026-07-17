"""
DocumentManager — 文档生命周期管理
===================================

编排完整的文档处理管线：
  Upload → Parse → Chunk → Embed → FAISS + BM25 → Save

支持格式: .md .txt .pdf .docx .html

所有操作复用现有模块（Parser / DocumentChunker / BGEProvider /
FAISSVectorStore / BM25Retriever），不重新实现任何核心逻辑。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.ingestion.chunker import DocumentChunker
from src.models.document import Document
from src.parsers.registry import parse_file, get_supported_extensions
from src.retriever.bm25 import BM25Retriever
from src.vectorstore.faiss_store import FAISSVectorStore


UPLOADS_DIR = Path("uploads")
DOCUMENTS_FILE = Path("output/documents.json")

# 拼接 glob 模式: *.md / *.pdf / *.docx / *.txt / *.html
SUPPORTED_GLOB = [f"*.{ext}" for ext in get_supported_extensions() if ext not in ("markdown", "htm")]


@dataclass
class DocRecord:
    """文档元数据记录（不存内容，只存管理信息）"""
    id: str
    filename: str
    original_name: str
    format: str
    file_size: int
    chunk_count: int
    status: str = "ready"
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class DocumentManager:
    """文档管理器：上传、列表、删除、重建索引"""

    def __init__(
        self,
        store: FAISSVectorStore,
        bm25: BM25Retriever,
        provider,  # EmbeddingProvider
        chunker: DocumentChunker | None = None,
    ):
        self._store = store
        self._bm25 = bm25
        self._provider = provider
        self._chunker = chunker or DocumentChunker()

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        DOCUMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # ── 上传文档 ──────────────────────────────

    def upload(self, file_bytes: bytes, filename: str) -> DocRecord:
        """上传文件，自动识别格式 → 解析 → 分块 → 向量化 → 索引

        支持: .md .txt .pdf .docx .html

        Args:
            file_bytes: 文件内容（字节）
            filename:   原始文件名

        Returns:
            DocRecord — 文档元数据记录
        """
        safe_name = self._sanitize_filename(filename)
        doc_id = uuid.uuid4().hex[:12]
        ext = Path(filename).suffix.lower().lstrip(".")

        # 1. 保存原始文件
        upload_path = UPLOADS_DIR / f"{doc_id}_{safe_name}"
        upload_path.write_bytes(file_bytes)

        # 2. 解析为纯文本
        try:
            content = parse_file(upload_path)
        except ValueError as e:
            upload_path.unlink()
            raise ValueError(str(e))
        except Exception as e:
            upload_path.unlink()
            raise ValueError(f"文件解析失败: {e}")

        if not content.strip():
            upload_path.unlink()
            raise ValueError("无法从文件中提取文本内容（可能为扫描件或空文件）")

        document = Document(
            id=doc_id,
            title=Path(filename).stem,
            path=upload_path.name,
            content=content,
            source=ext,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # 3. Chunk 切分
        chunks = self._chunker.split(document)
        if not chunks:
            upload_path.unlink()
            raise ValueError("文档内容为空，无法分块")

        # 4. 构建 chunk metadata
        chunk_dicts = [c.to_dict() for c in chunks]
        chunk_texts = [c.chunk_content for c in chunks]

        # 5. Embedding
        embeddings = self._provider.embed_documents(chunk_texts)

        # 6. 追加到 FAISS
        self._store.add_vectors(embeddings, chunk_dicts)
        self._store.save()

        # 7. 重建 BM25
        self._bm25.rebuild(self._store.metadata)

        # 8. 写入文档记录
        record = DocRecord(
            id=doc_id,
            filename=upload_path.name,
            original_name=filename,
            format=ext,
            file_size=len(file_bytes),
            chunk_count=len(chunks),
        )
        self._save_doc_record(record)

        return record

    # ── 文档列表 ──────────────────────────────

    def list_documents(self) -> list[DocRecord]:
        """返回所有文档记录"""
        return self._load_doc_records()

    # ── 删除文档 ──────────────────────────────

    def delete(self, doc_id: str) -> bool:
        """删除文档：移除文件 + 移除索引 + 移除记录"""
        records = self._load_doc_records()
        target = next((r for r in records if r.id == doc_id), None)
        if target is None:
            return False

        # 1. 删除上传文件
        file_path = UPLOADS_DIR / target.filename
        if file_path.exists():
            file_path.unlink()

        # 2. 从 FAISS metadata 中移除
        removed = self._store.remove_by_document_id(doc_id)
        if removed > 0:
            self._store.rebuild_from_metadata(self._provider)
            self._store.save()
            self._bm25.rebuild(self._store.metadata)

        # 3. 删除记录
        records = [r for r in records if r.id != doc_id]
        self._write_doc_records(records)

        return True

    # ── 重建索引 ──────────────────────────────

    def rebuild_index(self) -> dict:
        """从 uploads/ 目录全量重建索引（支持所有格式）"""
        all_files: list[Path] = []
        for pattern in SUPPORTED_GLOB:
            all_files.extend(UPLOADS_DIR.glob(pattern))
        all_files.sort()

        if not all_files:
            return {"document_count": 0, "chunk_count": 0}

        all_chunks: list[dict] = []
        records: list[DocRecord] = []

        for filepath in all_files:
            ext = filepath.suffix.lower().lstrip(".")
            doc_id = filepath.stem.split("_", 1)[0]

            try:
                content = parse_file(filepath)
            except Exception as e:
                print(f"   [WARN] 跳过无法解析的文件: {filepath.name} -> {e}")
                continue

            if not content.strip():
                continue

            document = Document(
                id=doc_id,
                title=filepath.stem,
                path=filepath.name,
                content=content,
                source=ext,
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            chunks = self._chunker.split(document)
            if not chunks:
                continue

            chunk_dicts = [c.to_dict() for c in chunks]
            chunk_texts = [c.chunk_content for c in chunks]
            embeddings = self._provider.embed_documents(chunk_texts)

            all_chunks.extend(chunk_dicts)
            self._store.build(embeddings, chunk_dicts) if len(records) == 0 else self._store.add_vectors(embeddings, chunk_dicts)

            records.append(DocRecord(
                id=doc_id,
                filename=filepath.name,
                original_name=filepath.name,
                format=ext,
                file_size=filepath.stat().st_size,
                chunk_count=len(chunks),
            ))

        self._store.save()
        self._bm25.rebuild(self._store.metadata)
        self._write_doc_records(records)

        return {
            "document_count": len(records),
            "chunk_count": len(all_chunks),
        }

    # ── 统计 ──────────────────────────────────

    def stats(self) -> dict:
        records = self._load_doc_records()
        return {
            "document_count": len(records),
            "chunk_count": self._store.count,
            "total_size": sum(r.file_size for r in records),
        }

    # ── 内部辅助 ──────────────────────────────

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return Path(name).name

    def _load_doc_records(self) -> list[DocRecord]:
        if not DOCUMENTS_FILE.exists():
            return []
        data = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))
        valid_keys = {"id", "filename", "original_name", "format", "file_size", "chunk_count", "status", "error", "created_at"}
        records = []
        for item in data:
            filtered = {k: v for k, v in item.items() if k in valid_keys}
            if "id" in filtered and "filename" in filtered:
                records.append(DocRecord(**filtered))
        return records

    def _write_doc_records(self, records: list[DocRecord]) -> None:
        DOCUMENTS_FILE.write_text(
            json.dumps([r.__dict__ for r in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_doc_record(self, record: DocRecord) -> None:
        records = self._load_doc_records()
        records.append(record)
        self._write_doc_records(records)
