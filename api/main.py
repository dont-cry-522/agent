"""
FastAPI 服务 — Agent Runtime 入口
================================

提供端点：
  POST /api/chat              — Agent 查询
  POST /api/documents/upload   — 上传 Markdown 文档
  GET  /api/documents          — 文档列表
  DELETE /api/documents/{id}   — 删除文档
  POST /api/index/rebuild      — 重建全部索引
  GET  /api/stats              — 系统统计
  GET  /api/health             — 健康检查

Agent Runtime 不变：所有核心逻辑复用现有模块。
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.document_manager import DocumentManager
from api.schemas import (
    ChatRequest, ChatResponse, SearchResultItem,
    DocumentItem, DocumentListResponse, UploadResponse,
    RebuildResponse, StatsResponse,
)
from src.agent.agent import Agent
from src.agent.memory import ConversationMemory
from src.agent.planner import RuleBasedPlanner
from src.agent.query_rewriter import QueryRewriter
from src.agent.tool import SearchKnowledgeTool, ToolManager
from src.embedding.provider import get_provider
from src.llm.deepseek import DeepSeekLLM
from src.retriever.bm25 import BM25Retriever
from src.retriever.retriever import Retriever, SearchResult
from src.reranker.reranker import BGEReranker
from src.vectorstore.faiss_store import FAISSVectorStore

# ── 模块级全局（供所有路由共享）────────────────

agent: Agent | None = None
_store: FAISSVectorStore | None = None
_bm25: BM25Retriever | None = None
_provider = None
_doc_manager: DocumentManager | None = None


def _init_agent():
    global agent, _store, _bm25, _provider, _doc_manager

    _store = FAISSVectorStore(index_dir="output")
    loaded = _store.load()
    if not loaded:
        import numpy as np
        print("[boot] 索引为空，创建空索引（云端首次部署）")
        _store.build([[0.0] * 512], [{"chunk_id": "__init__", "document_id": "", "title": "", "path": "", "source": "", "chunk_index": 0, "chunk_content": "", "context_heading": "", "context_doc_title": "", "context_prev_chunk": "", "context_next_chunk": "", "context_full_path": ""}])
        _store.save()

    metadata_path = Path("output/metadata.json")
    if metadata_path.exists():
        chunks = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        chunks = []
    _bm25 = BM25Retriever(chunks)
    print(f"[BM25] 语料库: {len(chunks)} 条文档")

    _provider = get_provider("bge")
    _ = _provider.embed_query("warmup")
    retriever = Retriever(_store, _provider, bm25_retriever=_bm25)

    import os
    disable_rerank = os.getenv("DISABLE_RERANKER", "").lower() in ("1", "true", "yes")
    if disable_rerank:
        print("[boot] Reranker 已禁用（DISABLE_RERANKER=1）")
        reranker = None
    else:
        try:
            reranker = BGEReranker()
            reranker._load_model()
        except Exception as e:
            print(f"[boot] Reranker 加载失败（内存不足？），已禁用: {e}")
            reranker = None

    llm = DeepSeekLLM()
    query_rewriter = QueryRewriter(llm)

    knowledge_tool = SearchKnowledgeTool(
        retriever=retriever, reranker=reranker, query_rewriter=query_rewriter
    )
    tool_manager = ToolManager()
    tool_manager.register(knowledge_tool)

    agent = Agent(
        memory=ConversationMemory(max_messages=20),
        planner=RuleBasedPlanner(),
        tool_manager=tool_manager,
        llm=llm,
    )

    _doc_manager = DocumentManager(_store, _bm25, _provider)
    print("[OK] Agent 初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[boot] 加载模型并初始化 Agent...")
    _init_agent()
    yield
    print("[shutdown] 服务关闭")


app = FastAPI(title="yuque-agent", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 辅助函数 ──────────────────────────────────

def _extract_search_results(agent: Agent):
    state = agent._last_state
    if state is None or not state.observations:
        return [], [], ""

    for obs in state.observations:
        if obs.tool_name != "search_knowledge":
            continue
        result = obs.result
        if not result.success:
            return [], [], ""

        recall_raw = result.metadata.get("recall", [])
        reranked_raw = result.data if isinstance(result.data, list) else []
        rewritten_query = result.metadata.get("rewritten_query", "")

        recall = [_format_search_result(r) for r in recall_raw]
        reranked = [_format_search_result(r) for r in reranked_raw]
        return recall, reranked, rewritten_query

    return [], [], ""


def _format_search_result(r: SearchResult) -> dict:
    return {
        "title": r.title,
        "path": r.path,
        "score": round(r.score, 4),
        "bm25_score": r.bm25_score,
        "fusion_score": r.fusion_score,
        "rerank_score": r.rerank_score if r.rerank_score else 0.0,
        "content": r.chunk_content,
        "heading": r.context_heading,
        "doc_title": r.context_doc_title,
    }


def _require_agent():
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent 尚未初始化")


# ── Chat ──────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    _require_agent()

    t0 = time.perf_counter()

    try:
        answer = agent.run(request.question)
    except Exception as exc:
        return ChatResponse(
            question=request.question,
            answer="",
            error=f"Agent 执行失败: {exc}",
        )

    retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)
    _, reranked, rewritten_query = _extract_search_results(agent)

    return ChatResponse(
        question=request.question,
        answer=answer,
        rewritten_query=rewritten_query,
        citations=[SearchResultItem(**item) for item in reranked],
        retrieval_ms=retrieval_ms,
        error=None,
    )


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    """SSE 流式对话端点"""
    _require_agent()

    def generate():
        t0 = time.perf_counter()
        answer = ""
        usage = {}

        try:
            for event in agent.run_stream(request.question):
                if event["type"] == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "token":
                    answer += event["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "finish":
                    usage = event.get("usage", {})
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    return
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
            return

        retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)
        _, reranked, rewritten_query = _extract_search_results(agent)

        citations = [
            {
                "title": r.get("title", ""),
                "path": r.get("path", ""),
                "score": r.get("score", 0),
                "bm25_score": r.get("bm25_score", 0),
                "fusion_score": r.get("fusion_score", 0),
                "rerank_score": r.get("rerank_score", 0),
                "content": r.get("content", ""),
                "heading": r.get("heading", ""),
                "doc_title": r.get("doc_title", ""),
            }
            for r in reranked
        ]

        yield f"data: {json.dumps({'type': 'done', 'answer': answer, 'citations': citations, 'rewritten_query': rewritten_query, 'retrieval_ms': retrieval_ms, 'usage': usage}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Documents ─────────────────────────────────

@app.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    _require_agent()

    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="仅支持 .md 文件")

    try:
        content = await file.read()
        record = _doc_manager.upload(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")

    return UploadResponse(
        document=DocumentItem(
            id=record.id,
            filename=record.filename,
            original_name=record.original_name,
            format=record.format,
            file_size=record.file_size,
            chunk_count=record.chunk_count,
            status=record.status,
            error=record.error,
            created_at=record.created_at,
        ),
        message=f"已索引 {record.chunk_count} 个 Chunk",
    )


@app.get("/api/documents", response_model=DocumentListResponse)
def list_documents():
    _require_agent()

    records = _doc_manager.list_documents()
    items = [
        DocumentItem(
            id=r.id,
            filename=r.filename,
            original_name=r.original_name,
            format=r.format,
            file_size=r.file_size,
            chunk_count=r.chunk_count,
            status=r.status,
            error=r.error,
            created_at=r.created_at,
        )
        for r in records
    ]
    return DocumentListResponse(documents=items)


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    _require_agent()

    ok = _doc_manager.delete(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")

    return {"message": "已删除", "id": doc_id}


@app.post("/api/index/rebuild", response_model=RebuildResponse)
def rebuild_index():
    _require_agent()

    try:
        result = _doc_manager.rebuild_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建失败: {e}")

    return RebuildResponse(
        document_count=result["document_count"],
        chunk_count=result["chunk_count"],
        message=f"重建完成: {result['document_count']} 篇文档, {result['chunk_count']} 个 Chunk",
    )


# ── System ────────────────────────────────────

@app.get("/api/stats", response_model=StatsResponse)
def stats():
    _require_agent()

    s = _doc_manager.stats()
    return StatsResponse(
        document_count=s["document_count"],
        chunk_count=s["chunk_count"],
        total_size=s["total_size"],
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "agent_ready": agent is not None}


# ── 前端静态文件（生产模式）────────────────────
# API 路由优先匹配，未匹配的走 SPA

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="static")
