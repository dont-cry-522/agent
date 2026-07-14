"""
HTTP API Server — 使用 Python 内置 http.server，无需额外依赖

提供两个端点：
  GET  /          → 返回前端页面
  POST /api/chat  → RAG 查询接口，返回 Recall + Rerank + LLM 回答
"""

from __future__ import annotations

import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.embedding.provider import get_provider
from src.llm.deepseek import DeepSeekLLM
from src.prompt.builder import PromptBuilder
from src.retriever.retriever import Retriever
from src.retriever.bm25 import BM25Retriever
from src.reranker.reranker import BGEReranker
from src.vectorstore.faiss_store import FAISSVectorStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")


class RAGHandler(BaseHTTPRequestHandler):
    retriever: Retriever | None = None
    prompt_builder: PromptBuilder | None = None
    llm: DeepSeekLLM | None = None
    reranker: BGEReranker | None = None
    top_k: int = 5

    def log_message(self, format, *args):
        print(f"[API] {args[0]}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_html()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(INDEX_HTML.encode("utf-8"))

    def _handle_chat(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)
        question = data.get("question", "").strip()

        if not question:
            self._json_response(400, {"error": "question 不能为空"})
            return

        if (
            self.retriever is None
            or self.prompt_builder is None
            or self.llm is None
        ):
            self._json_response(500, {"error": "服务未初始化"})
            return

        t0 = time.perf_counter()

        recall_k = max(self.top_k, 5)
        recall_results = self.retriever.retrieve(question, top_k=recall_k)

        use_rerank = data.get("rerank", True)
        reranked_results = recall_results
        if use_rerank and self.reranker is not None and len(recall_results) > 1:
            reranked_results = self.reranker.rerank(
                question, recall_results, top_k=self.top_k
            )

        retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)

        def format_result(r):
            return {
                "title": r.title,
                "path": r.path,
                "score": round(r.score, 4),
                "bm25_score": r.bm25_score,
                "fusion_score": r.fusion_score,
                "rerank_score": r.rerank_score,
                "content": r.chunk_content[:200] + ("..." if len(r.chunk_content) > 200 else ""),
            }

        recall_list = [format_result(r) for r in recall_results]
        reranked_list = [format_result(r) for r in reranked_results]

        messages = self.prompt_builder.build(question, reranked_results)

        try:
            answer = self.llm.chat(messages["system"], messages["user"])
        except Exception as e:
            answer = None
            error_msg = str(e)

        self._json_response(
            200,
            {
                "question": question,
                "recall": recall_list,
                "reranked": reranked_list,
                "answer": answer,
                "retrieval_ms": retrieval_ms,
                "error": error_msg if answer is None else None,
            },
        )

    def _json_response(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def create_server(host: str = "127.0.0.1", port: int = 8000) -> HTTPServer:
    store = FAISSVectorStore(index_dir="output")
    if not store.load():
        raise RuntimeError("索引不存在，请先运行 python scripts/build_index.py")

    metadata_path = Path("output/metadata.json")
    chunks = json.loads(metadata_path.read_text(encoding="utf-8"))
    bm25 = BM25Retriever(chunks)
    print(f"🔤 BM25 语料库: {len(chunks)} 条文档")

    provider = get_provider("bge")
    _ = provider.embed_query("warmup")  # 触发 JIT 预热，避免首次查询卡顿
    RAGHandler.retriever = Retriever(store, provider, bm25_retriever=bm25)
    RAGHandler.prompt_builder = PromptBuilder()
    RAGHandler.llm = DeepSeekLLM()
    RAGHandler.reranker = BGEReranker()
    RAGHandler.reranker._load_model()  # 触发 JIT 预热

    server = HTTPServer((host, port), RAGHandler)
    return server
