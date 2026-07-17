"""
DocumentManager — 文档生命周期管理
===================================

编排完整的文档处理管线：
  Upload → Parse → Chunk → Embed → FAISS + BM25 → Save

支持格式: .md .txt .pdf .docx .html

增量更新：通过 SHA256 hash 去重 + IndexIDMap 增量删除，单文档修改不重建全部索引。
"""

from __future__ import annotations

import hashlib
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
SUPPORTED_GLOB = [f"*.{ext}" for ext in get_supported_extensions() if ext not in ("markdown", "htm")]


@dataclass
class DocRecord:
    """文档元数据记录（返回给 API 层使用）"""
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
        get_session=None,  # callable → Session
        chunker: DocumentChunker | None = None,
    ):
        self._store = store
        self._bm25 = bm25
        self._provider = provider
        self._get_session = get_session
        self._chunker = chunker or DocumentChunker()
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self._migrate_json_if_needed()

    # ── JSON → SQLite 迁移 ───────────────────

    def _migrate_json_if_needed(self) -> None:
        json_path = Path("output/documents.json")
        if not json_path.exists() or self._get_session is None:
            return
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if not data:
                return
            from storage.repository import DocumentRepository
            repo = DocumentRepository()
            with self._get_session() as s:
                if repo.count(s) > 0:
                    # 已有 SQLite 记录，且比 JSON 新，跳过
                    json_mtime = json_path.stat().st_mtime
                    latest = repo.list_all(s)
                    if latest and latest[0].created_at.timestamp() > json_mtime:
                        return
                for item in data:
                    doc_id = item.get("id", uuid.uuid4().hex[:12])
                    if repo.get_by_id(s, doc_id):
                        continue
                    repo.create(
                        s,
                        id=doc_id,
                        filename=item.get("filename", ""),
                        original_name=item.get("original_name", ""),
                        format=item.get("format", "unknown"),
                        file_size=item.get("file_size", 0),
                        chunk_count=item.get("chunk_count", 0),
                        status=item.get("status", "ready"),
                        error=item.get("error", ""),
                    )
                print(f"[migrate] {len(data)} 条文档记录已从 JSON 迁移到 SQLite")
                json_path.rename(json_path.with_suffix(".json.bak"))
        except Exception as e:
            print(f"[migrate] 迁移失败（不影响使用）: {e}")

    # ── 上传文档 ──────────────────────────────

    def upload(self, file_bytes: bytes, filename: str) -> DocRecord:
        safe_name = self._sanitize_filename(filename)
        ext = Path(filename).suffix.lower().lstrip(".")
        content_hash = self._compute_hash(file_bytes)

        # 检查是否存在同名文档
        existing = self._find_by_name(filename)
        if existing and existing.get("content_hash") == content_hash:
            return DocRecord(**existing)

        # 如果同名但 hash 不同 → 先删旧的
        if existing:
            old_id = existing["id"]
            self._store.remove_by_document_id(old_id)
            old_file = UPLOADS_DIR / existing.get("filename", "")
            if old_file.exists():
                old_file.unlink()

        doc_id = uuid.uuid4().hex[:12]
        upload_path = UPLOADS_DIR / f"{doc_id}_{safe_name}"
        upload_path.write_bytes(file_bytes)

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

        chunks = self._chunker.split(document)
        if not chunks:
            upload_path.unlink()
            raise ValueError("文档内容为空，无法分块")

        chunk_dicts = [c.to_dict() for c in chunks]
        chunk_texts = [c.chunk_content for c in chunks]
        embeddings = self._provider.embed_documents(chunk_texts)

        self._store.add_vectors(embeddings, chunk_dicts)
        self._store.save()
        self._bm25.rebuild(self._store.metadata)

        record = DocRecord(
            id=doc_id,
            filename=upload_path.name,
            original_name=filename,
            format=ext,
            file_size=len(file_bytes),
            chunk_count=len(chunks),
        )
        self._persist_record(record, content_hash)
        return record

    # ── 文档列表 ──────────────────────────────

    def list_documents(self) -> list[DocRecord]:
        if self._get_session is None:
            return []
        try:
            from storage.repository import DocumentRepository
            repo = DocumentRepository()
            with self._get_session() as s:
                db_docs = repo.list_all(s)
            return [
                DocRecord(
                    id=d.id,
                    filename=d.filename,
                    original_name=d.original_name,
                    format=d.format,
                    file_size=d.file_size,
                    chunk_count=d.chunk_count,
                    status=d.status,
                    error=d.error,
                    created_at=d.created_at.strftime("%Y-%m-%d %H:%M:%S") if d.created_at else "",
                )
                for d in db_docs
            ]
        except Exception:
            return []

    # ── 删除文档 ──────────────────────────────

    def delete(self, doc_id: str) -> bool:
        target_filename = None
        if self._get_session is not None:
            try:
                from storage.repository import DocumentRepository
                repo = DocumentRepository()
                with self._get_session() as s:
                    db_doc = repo.get_by_id(s, doc_id)
                    if db_doc:
                        target_filename = db_doc.filename
                        repo.delete(s, doc_id)
            except Exception:
                pass

        if target_filename:
            file_path = UPLOADS_DIR / target_filename
            if file_path.exists():
                file_path.unlink()
        else:
            for f in UPLOADS_DIR.iterdir():
                if f.name.startswith(doc_id + "_"):
                    target_filename = f.name
                    f.unlink()
                    break
            if not target_filename:
                return False

        # 增量删除：从 FAISS 移除指定 document 的向量
        removed = self._store.remove_by_document_id(doc_id)
        if removed > 0:
            self._store.save()
            # compact metadata → 重建 BM25
            self._bm25.rebuild(self._store.metadata)
        return True

    # ── 重建索引 ──────────────────────────────

    def rebuild_index(self) -> dict:
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

        if self._get_session is not None:
            try:
                from storage.repository import DocumentRepository
                repo = DocumentRepository()
                with self._get_session() as s:
                    for r in records:
                        if not repo.get_by_id(s, r.id):
                            repo.create(s, **r.__dict__)
                        else:
                            repo.update(s, r.id, chunk_count=r.chunk_count, file_size=r.file_size)
            except Exception:
                pass

        return {
            "document_count": len(records),
            "chunk_count": len(all_chunks),
        }

    # ── 统计 ──────────────────────────────────

    def stats(self) -> dict:
        doc_count = 0
        total_size = 0
        if self._get_session is not None:
            try:
                from storage.repository import DocumentRepository
                repo = DocumentRepository()
                with self._get_session() as s:
                    doc_count = repo.count(s)
                    total_size = repo.total_size(s)
            except Exception:
                pass
        return {
            "document_count": doc_count,
            "chunk_count": self._store.count,
            "total_size": total_size,
        }

    # ── 内部辅助 ──────────────────────────────

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return Path(name).name

    @staticmethod
    def _compute_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _find_by_name(self, original_name: str) -> dict | None:
        if self._get_session is None:
            return None
        try:
            from storage.repository import DocumentRepository
            repo = DocumentRepository()
            with self._get_session() as s:
                for doc in repo.list_all(s):
                    if doc.original_name == original_name:
                        return {
                            "id": doc.id,
                            "filename": doc.filename,
                            "original_name": doc.original_name,
                            "format": doc.format,
                            "file_size": doc.file_size,
                            "chunk_count": doc.chunk_count,
                            "status": doc.status,
                            "error": doc.error,
                            "content_hash": doc.content_hash,
                            "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "",
                        }
        except Exception:
            pass
        return None

    def _persist_record(self, record: DocRecord, content_hash: str = "") -> None:
        if self._get_session is None:
            return
        try:
            from storage.repository import DocumentRepository
            repo = DocumentRepository()
            with self._get_session() as s:
                # 删除旧记录（如果同名更新）
                for doc in repo.list_all(s):
                    if doc.original_name == record.original_name and doc.id != record.id:
                        repo.delete(s, doc.id)

                existing = repo.get_by_id(s, record.id)
                if existing:
                    repo.update(s, record.id,
                        chunk_count=record.chunk_count,
                        file_size=record.file_size,
                        content_hash=content_hash,
                        status=record.status)
                else:
                    repo.create(
                        s,
                        id=record.id,
                        filename=record.filename,
                        original_name=record.original_name,
                        format=record.format,
                        file_size=record.file_size,
                        chunk_count=record.chunk_count,
                        status=record.status,
                        error=record.error,
                        content_hash=content_hash,
                    )
        except Exception as e:
            print(f"[doc] 持久化记录失败: {e}")
