"""
Tool 抽象 — Agent 与外部能力的统一契约
======================================

架构定位：
  Tool 是 Agent 与外部世界的边界。Agent 不直接 import Retriever / SQL / HTTP，
  它只看到 Tool 接口。这种隔离让 Agent 无限扩展能力而不改自身代码。

依赖方向（单向）：
  Tool ──依赖──→ Retriever / Reranker / 外部 API
  ToolMetadata ──依赖──→ 无（纯数据）
  Planner ──依赖──→ ToolMetadata（只读，不看 Tool）
  Agent ──依赖──→ ToolManager + Tool 接口（不看 Tool 内部）
  Retriever ──不知道──→ Tool / Agent / Planner 的存在

核心模块：
  Tool(ABC)      — 所有工具的抽象基类，定义 execute() 契约
  ToolResult     — 统一执行结果，含 trace_id/latency/error_taxonomy
  ToolMetadata   — Planner 可见的只读元数据（ISP：只有描述，没有 execute）
  ToolManager    — 注册/发现/校验/生命周期（SRP：Agent 不管理工具）
  ToolError      — 类型化错误枚举（NETWORK / TIMEOUT / RATE_LIMITED …）
  ToolCategory   — 工具分类（KNOWLEDGE / COMPUTATION / EXTERNAL / SYSTEM）
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from src.retriever.retriever import Retriever, SearchResult


# ── 类型化错误 ──────────────────────────────────
#
# 设计理由：不用裸 str 表示错误。
# Agent 根据错误类型自动决策：
#   NETWORK_ERROR / TIMEOUT → 重试
#   RATE_LIMITED             → 等待后重试
#   AUTH_ERROR               → 不重试，通知用户
#   INVALID_PARAMS           → 不重试，日志告警（Planner 幻觉所致）
#   INTERNAL_ERROR           → 不重试，记录完整堆栈

class ToolError(str, Enum):
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    INVALID_PARAMS = "invalid_params"
    INTERNAL_ERROR = "internal_error"


# ── 工具分类 ────────────────────────────────────
#
# 设计理由：Planner 根据分类做路由策略。
# 例如 LLM Planner 可以按 category 排序：
#   KNOWLEDGE 先搜（本地快），EXTERNAL 后搜（网络慢），SYSTEM 最后（涉及状态变更）

class ToolCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    COMPUTATION = "computation"
    EXTERNAL = "external"
    SYSTEM = "system"


# ── 工具执行结果 ────────────────────────────────
#
# 设计理由：8 个字段覆盖企业可观测性三要素：
#   - 诊断：trace_id → 关联一次 Agent 运行的所有 Tool 调用
#   - 性能：latency_ms → 定位慢工具，驱动优化决策
#   - 审计：input_params → 完整记录调了什么参数
#
# 使用工厂方法 from_success / from_error 而非直接构造：
#   - Tool 作者不需要手动填 timestamp（工厂自动补）
#   - 保证 success=True 时 error 必为 None，反之亦然
#   - 新增字段时只需改工厂方法，Tool 作者无感知

class ToolResult:
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: ToolError | None = None,
        error_message: str = "",
        tool_name: str = "",
        input_params: dict | None = None,
        latency_ms: float = 0.0,
        trace_id: str = "",
        metadata: dict | None = None,
        timestamp: float | None = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_message = error_message
        self.tool_name = tool_name
        self.input_params = input_params or {}
        self.latency_ms = latency_ms
        self.trace_id = trace_id
        self.metadata = metadata or {}
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_success(
        cls,
        data: Any,
        tool_name: str = "",
        input_params: dict | None = None,
        trace_id: str = "",
        metadata: dict | None = None,
        elapsed_ms: float = 0.0,
    ) -> "ToolResult":
        return cls(
            success=True,
            data=data,
            tool_name=tool_name,
            input_params=input_params,
            latency_ms=elapsed_ms,
            trace_id=trace_id,
            metadata=metadata,
        )

    @classmethod
    def from_error(
        cls,
        error: ToolError,
        message: str = "",
        tool_name: str = "",
        input_params: dict | None = None,
        trace_id: str = "",
        metadata: dict | None = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            error=error,
            error_message=message,
            tool_name=tool_name,
            input_params=input_params,
            trace_id=trace_id,
            metadata=metadata,
        )

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL({self.error.value})"
        return f"ToolResult({self.tool_name} {status} {self.latency_ms:.1f}ms)"


# ── 只读元数据（给 Planner 用） ──────────────────
#
# 设计理由：接口隔离原则（ISP）。
# Planner 需要知道"有哪些工具"和"它们能干什么"来做出决策，
# 但 Planner 不应该能调用 tool.execute()。
# ToolMetadata 只暴露描述信息，不暴露执行入口。
# 这是安全边界：Planner 永远不会意外触发工具执行。

class ToolMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        category: ToolCategory = ToolCategory.SYSTEM,
        requires_auth: bool = False,
        avg_latency_ms: int = 100,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.category = category
        self.requires_auth = requires_auth
        self.avg_latency_ms = avg_latency_ms


# ── Tool 抽象基类 ───────────────────────────────
#
# 设计理由：ABC 而非 Protocol。
# Protocol 允许静态鸭子类型，但无法在运行时校验。
# ToolManager.register() 需要 isinstance(tool, Tool) 在注册时拦截错误对象，
# 而不是等到 execute() 调用时才报 AttributeError。
#
# format_result() 放在 Tool 上而非 PromptBuilder：
#   - SQL 工具输出 42 行表格，Calculator 输出一个数字，Knowledge 输出文档片段
#   - 格式化逻辑跟 Tool 强相关，PromptBuilder 不应该认识每种 Tool
#   - SRP：谁产出数据，谁负责格式化

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        ...

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def requires_auth(self) -> bool:
        return False

    @property
    def avg_latency_ms(self) -> int:
        return 100

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        ...

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            category=self.category,
            requires_auth=self.requires_auth,
            avg_latency_ms=self.avg_latency_ms,
        )

    def format_result(self, result: ToolResult) -> str:
        if not result.success:
            return f"[{self.name}] 执行失败: {result.error_message}"
        return str(result.data)

    def __repr__(self) -> str:
        return f"Tool({self.name})"


# ── 工具管理器 ──────────────────────────────────
#
# 设计理由：裸 dict[str, Tool] 不能承载以下职责：
#   1. 注册时校验接口合规（isinstance check）
#   2. 参数校验（防御 Planner 幻觉或恶意输入）
#   3. 未来：生命周期钩子（setup/teardown — 数据库连接、模型预热）
#   4. 未来：访问控制（按用户/会话限制可用工具）
#   5. 未来：速率限制（Rate Limiter 挂在 Manager 层，Tool 无感知）
#
# list_metadata() 返回 ToolMetadata 而非 Tool：
#   Planner 接收元数据列表做决策，永远拿不到 Tool 实例。
#   物理隔绝了 Planner 意外调用 tool.execute() 的可能性。

class ToolManager:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool)}")
        if not tool.name:
            raise ValueError("Tool name must not be empty")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool not found: {name}")
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_metadata(self) -> list[ToolMetadata]:
        return [tool.get_metadata() for tool in self._tools.values()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def validate_params(self, tool_name: str, params: dict) -> None:
        tool = self.get(tool_name)
        required = tool.parameters.get("required", [])
        properties = tool.parameters.get("properties", {})
        for key in required:
            if key not in params:
                raise ValueError(
                    f"Missing required param '{key}' for tool '{tool_name}'"
                )
        for key in params:
            if key not in properties:
                raise ValueError(
                    f"Unknown param '{key}' for tool '{tool_name}'"
                )

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return self.has(name)


# ── SearchKnowledgeTool ─────────────────────────
#
# 设计理由（为什么不直接在 Agent 里调 Retriever）：
#   Agent 只知道 Tool 接口，不知道 Retriever 的存在。
#   如果 Agent 直接 import Retriever：
#     — 换向量库（FAISS → Milvus）→ 改 Agent
#     — 加预处理步骤（query → 改写 → 再搜）→ 改 Agent
#     — 换搜索策略（向量 → Hybrid → 多层 Rerank）→ 改 Agent
#   包在 Tool 里之后：
#     — 以上所有变更只改 SearchKnowledgeTool，Agent 一行不变
#
# 构造时注入 Retriever + 可选 Reranker：
#   DI（依赖注入）而非 Tool 内部创建实例。
#   好处：同一个 Retriever 可以被多个模块共享，模型只加载一次。

class SearchKnowledgeTool(Tool):
    PARAMETERS = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询，自然语言问题",
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量，默认 5，最大 20",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, retriever: Retriever, reranker=None, query_rewriter=None):
        self._retriever = retriever
        self._reranker = reranker
        self._query_rewriter = query_rewriter

    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return (
            "搜索本地知识库，查找与问题相关的文档片段。"
            "适用于：概念解释、技术文档查询、笔记检索。"
            "返回文档标题、路径、相关内容片段及相似度分数。"
        )

    @property
    def parameters(self) -> dict:
        return self.PARAMETERS

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.KNOWLEDGE

    @property
    def avg_latency_ms(self) -> int:
        return 1000

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = int(kwargs.get("top_k", 5))

        start = time.perf_counter()

        rewritten_query = query
        if self._query_rewriter is not None:
            try:
                rewritten_query = self._query_rewriter.rewrite(query)
            except Exception:
                rewritten_query = query

        try:
            candidates = self._retriever.retrieve(rewritten_query, top_k=max(top_k, 20))

            if self._reranker is not None and candidates:
                results = self._reranker.rerank(rewritten_query, candidates, top_k=top_k)
            else:
                results = candidates[:top_k]

            elapsed_ms = (time.perf_counter() - start) * 1000

            return ToolResult.from_success(
                data=results,
                tool_name=self.name,
                input_params={"query": query, "top_k": top_k},
                elapsed_ms=elapsed_ms,
                metadata={
                    "num_results": len(results),
                    "rerank_applied": self._reranker is not None,
                    "num_candidates": len(candidates),
                    "recall": candidates,
                    "original_query": query,
                    "rewritten_query": rewritten_query,
                },
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ToolResult.from_error(
                error=ToolError.INTERNAL_ERROR,
                message=str(exc),
                tool_name=self.name,
                input_params={"query": query, "top_k": top_k},
                metadata={"elapsed_ms": elapsed_ms},
            )

    def format_result(self, result: ToolResult) -> str:
        if not result.success:
            return f"[search_knowledge] 搜索失败: {result.error_message}"

        search_results: list[SearchResult] = result.data
        if not search_results:
            return "[search_knowledge] 未找到相关文档"

        lines = [f"[search_knowledge] 找到 {len(search_results)} 条相关文档:"]
        for i, sr in enumerate(search_results, 1):
            doc_info = f"{sr.context_doc_title or sr.title}"
            path_info = f" ({sr.path})" if sr.path else ""
            score_info = f" [Rerank: {sr.rerank_score:.3f}]" if sr.rerank_score else f" [Score: {sr.score:.3f}]"
            lines.append(f"  {i}. {doc_info}{path_info}{score_info}")
            lines.append(f"     {sr.chunk_content[:150]}{'...' if len(sr.chunk_content) > 150 else ''}")
        return "\n".join(lines)
