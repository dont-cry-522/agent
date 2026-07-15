"""
HTTP API Server — Agent Runtime 入口

提供两个端点：
  GET  /          → 返回前端页面
  POST /api/chat  → Agent 查询接口，内部走 Planner → Tool → LLM 编排

架构变更（Phase 4.6）：
  旧：server → Retriever → Reranker → PromptBuilder → LLM
  新：server → Agent.run() → [Planner → Tool(search_knowledge) → LLM]

  server.py 不再直接 import Retriever / PromptBuilder / BGEReranker。
  所有检索和生成逻辑由 Agent 编排，server 只负责 HTTP ↔ Agent 的适配。
"""

from __future__ import annotations

import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.agent.agent import Agent
from src.agent.memory import ConversationMemory
from src.agent.planner import RuleBasedPlanner
from src.agent.tool import SearchKnowledgeTool, ToolManager
from src.embedding.provider import get_provider
from src.llm.deepseek import DeepSeekLLM
from src.retriever.bm25 import BM25Retriever
from src.retriever.retriever import Retriever, SearchResult
from src.reranker.reranker import BGEReranker
from src.vectorstore.faiss_store import FAISSVectorStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")


class AgentHandler(BaseHTTPRequestHandler):
    agent: Agent | None = None

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

        if self.agent is None:
            self._json_response(500, {"error": "服务未初始化"})
            return

        t0 = time.perf_counter()
        answer = self.agent.run(question)
        retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)

        recall_list, reranked_list = self._extract_search_results()

        self._json_response(
            200,
            {
                "question": question,
                "recall": recall_list,
                "reranked": reranked_list,
                "answer": answer,
                "retrieval_ms": retrieval_ms,
                "error": None,
            },
        )

    def _extract_search_results(self):
        state = self.agent._last_state
        if state is None or not state.observations:
            return [], []

        for obs in state.observations:
            if obs.tool_name != "search_knowledge":
                continue
            result = obs.result
            if not result.success:
                return [], []

            recall_raw = result.metadata.get("recall", [])
            reranked_raw = result.data if isinstance(result.data, list) else []

            recall = [self._format_search_result(r) for r in recall_raw]
            reranked = [self._format_search_result(r) for r in reranked_raw]
            return recall, reranked

        return [], []

    @staticmethod
    def _format_search_result(r: SearchResult) -> dict:
        return {
            "title": r.title,
            "path": r.path,
            "score": round(r.score, 4),
            "bm25_score": r.bm25_score,
            "fusion_score": r.fusion_score,
            "rerank_score": r.rerank_score,
            "content": r.chunk_content[:200] + ("..." if len(r.chunk_content) > 200 else ""),
        }

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
    print(f"[BM25] 语料库: {len(chunks)} 条文档")

    provider = get_provider("bge")
    _ = provider.embed_query("warmup")
    retriever = Retriever(store, provider, bm25_retriever=bm25)
    reranker = BGEReranker()
    reranker._load_model()

    knowledge_tool = SearchKnowledgeTool(retriever=retriever, reranker=reranker)
    tool_manager = ToolManager()
    tool_manager.register(knowledge_tool)

    agent = Agent(
        memory=ConversationMemory(max_messages=20),
        planner=RuleBasedPlanner(),
        tool_manager=tool_manager,
        llm=DeepSeekLLM(),
    )

    AgentHandler.agent = agent

    server = HTTPServer((host, port), AgentHandler)
    return server
