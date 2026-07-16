"""
Agent Runtime — Agent 编排核心
==============================

架构定位：
  Agent 是"指挥"。它不搜索、不记忆、不决策、不调用 API——
  它只负责按顺序调用 Planner → Tool → LLM，把各模块串成一条流水线。

依赖方向（单向，全部注入）：
  Agent
  ├── 依赖──→ Memory(ABC)        — 消息存储，不依赖具体实现
  ├── 依赖──→ Planner(ABC)       — 决策接口，不依赖具体策略
  ├── 依赖──→ ToolManager        — 工具注册/执行，不依赖具体工具
  ├── 依赖──→ PromptBuilder      — 上下文拼接（复用现有模块）
  ├── 依赖──→ DeepSeekLLM        — LLM 调用（复用现有模块）
  └── 依赖──→ Observation        — 工具观察数据模型（同文件定义）

  以上所有依赖都是接口/抽象，没有一个是具体实现。
  这是 DIP 的核心：高层模块（Agent）不依赖低层模块（具体实现）。

为什么 Observation 和 AgentState 定义在 agent.py 内：
  它们是 Agent 运行时的内部概念，不由外部模块独立使用。
  Observation 的生命周期绑定在一次 Agent.run() 调用中，
  AgentState 是 Agent 循环内的瞬态快照。
  将它们独立为单独模块是过度设计——在它们被多个模块引用之前，留在 Agent 内更清晰。

为什么不修改已有模块（Retriever / PromptBuilder / LLM）：
  这些模块在 RAG 管道中已稳定运行。
  Agent 是新的消费者，不是改造者。
  Agent 通过 Tool 间接使用 Retriever，
  通过 PromptBuilder 间接拼接上下文，
  通过 DeepSeekLLM 间接生成回答。
  所有已有接口保持不变。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.agent.memory import Memory, ConversationMemory, Message, MessageFormatter
from src.agent.planner import Planner, RuleBasedPlanner, Plan
from src.agent.tool import ToolManager, ToolResult, ToolMetadata
from src.llm.deepseek import DeepSeekLLM
from src.prompt.builder import PromptBuilder
from src.retriever.retriever import SearchResult


# ── 工具观察 ────────────────────────────────────
#
# 设计理由：Observation 是 ToolResult 的"Agent 视角"包装。
#   ToolResult 是工具返回的原始数据（列表、JSON、数字）。
#   Observation 在原始数据之上附加了格式化文本 + 上下文元数据，
#   让 Agent 的 Prompt 构建阶段拿到的是"可直接注入 LLM 的文本块"，
#   而不是需要二次解析的原始对象。
#
# formatted 字段的值来自 tool.format_result(result)：
#   每个 Tool 定义自己的格式化逻辑（SQL → 表格，Knowledge → 文档片段）。
#   Agent 不需要知道如何格式化——它只知道每个 Observation 都有一个 formatted 字段。

@dataclass
class Observation:
    tool_name: str
    result: ToolResult
    formatted: str
    timestamp: float = field(default_factory=time.time)
    trace_id: str = ""


# ── Agent 运行时状态 ─────────────────────────────
#
# 设计理由：为什么需要显式状态对象。
#   没有 AgentState 时，运行状态散落在 Agent.run() 的局部变量中：
#     iteration 在 while 循环头
#     observations 在列表里
#     current_plan 在 if/else 分支里
#   无法序列化、无法恢复、无法传递给外部监控。
#
# 和 LangGraph 的关系：
#   LangGraph 的 Node 函数签名是 (AgentState) → AgentState。
#   有了 AgentState，迁移时只需把 Agent.run() 的步骤拆成 Node 函数，
#   每个 Node 返回修改后的 AgentState。状态对象本身的字段不需要改。

@dataclass
class AgentState:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    observations: list[Observation] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    status: str = "IDLE"
    error: str | None = None
    started_at: float = field(default_factory=time.time)


# ── Agent 核心类 ─────────────────────────────────
#
# 执行流程（Memory → Planner → Tool → Prompt → LLM → Memory → Return）：
#
#   run(query)
#     │
#     ├─ 1. 用户消息写入 Memory
#     │
#     ├─ 2. 创建 AgentState（trace_id + 计数器初始化）
#     │
#     ├─ 3. Planner 决策循环（最多 max_iterations 次）
#     │      ├─ Planner.decide(query, history, tool_metadata)
#     │      ├─ respond → 跳出循环
#     │      └─ call_tool → 执行 → 创建 Observation → 写 Memory → 继续循环
#     │
#     ├─ 4. 构建 Agent Prompt（system + 对话历史 + 工具观察 + 用户问题）
#     │
#     ├─ 5. LLM 生成回答
#     │
#     ├─ 6. 回答写入 Memory
#     │
#     └─ 7. 返回回答文本 + 追踪信息
#
# 设计理由：
#   - 为什么 Agent 不直接调 Retriever：
#     和 DESIGN.md Q3 同一个答案。Agent 的职责是编排，不应该知道什么是 FAISS。
#     通过 SearchKnowledgeTool 间接调用，Agent 只看到 Tool 接口。
#   - 为什么用 while 循环而非递归：
#     循环天然可设 max_iterations 硬上限防止死循环，递归需要额外传 depth 参数。
#   - 为什么 Planner 每次循环都重新 decide：
#     Observation 产生后，新的上下文可能改变决策。
#     例如第一次搜索不满意，Planner 可能决定换个搜索词再搜一次。

class Agent:

    SYSTEM_PROMPT = (
        "你是一个知识库助手。你可以访问用户的本地知识库来回答问题。\n"
        "当工具搜索结果可用时，你会看到搜索到的文档片段。\n"
        "请基于搜索结果和对话历史回答用户问题。\n"
        "如果搜索结果不足以回答问题，请如实说明，不要编造信息。\n"
        "回答时请引用文档来源。"
    )

    def __init__(
        self,
        memory: Memory | None = None,
        planner: Planner | None = None,
        tool_manager: ToolManager | None = None,
        llm: DeepSeekLLM | None = None,
        prompt_builder: PromptBuilder | None = None,
    ):
        self.memory = memory or ConversationMemory()
        self.planner = planner or RuleBasedPlanner()
        self.tool_manager = tool_manager or ToolManager()
        self.llm = llm
        self.prompt_builder = prompt_builder or PromptBuilder()
        self._last_state: AgentState | None = None

    # ── 主入口 ───────────────────────────────

    def run(self, query: str) -> str:
        self._last_state = AgentState()
        state = self._last_state
        state.status = "THINKING"

        self.memory.add("user", query)

        # ── Planner 循环 ──

        while state.iteration < state.max_iterations:
            plan = self.planner.decide(
                query=query,
                history=self.memory.get_messages(),
                available_tools=self.tool_manager.list_metadata(),
            )

            if plan.should_respond:
                break

            self._execute_tool(plan, state)

        # ── 构建 Prompt ──

        system, user_message = self._build_prompt(query, state)

        # ── LLM 生成 ──

        state.status = "RESPONDING"
        try:
            answer = self.llm.chat(system_prompt=system, user_message=user_message)
        except Exception as exc:
            state.status = "ERROR"
            state.error = str(exc)
            answer = f"抱歉，生成回答时出错：{exc}"

        self.memory.add("assistant", answer)
        state.status = "DONE"
        return answer

    def run_stream(self, query: str):
        """流式 Agent 执行：Planner → Tool → LLM (stream)，逐 token 产出

        Yields:
            {"type": "thinking", "content": "..."}
            {"type": "token", "content": "..."}
            {"type": "finish", "usage": {...}}
            {"type": "error", "message": "..."}
        """
        self._last_state = AgentState()
        state = self._last_state
        state.status = "THINKING"
        yield {"type": "thinking", "content": "正在分析问题..."}

        self.memory.add("user", query)

        # ── Planner 循环 ──

        while state.iteration < state.max_iterations:
            plan = self.planner.decide(
                query=query,
                history=self.memory.get_messages(),
                available_tools=self.tool_manager.list_metadata(),
            )

            if plan.should_respond:
                break

            yield {"type": "thinking", "content": "正在检索知识库..."}
            self._execute_tool(plan, state)

        # ── 构建 Prompt ──

        system, user_message = self._build_prompt(query, state)
        state.status = "RESPONDING"

        # ── LLM 流式生成 ──

        full_answer = ""
        try:
            for event in self.llm.chat_stream(system_prompt=system, user_message=user_message):
                if event["type"] == "token":
                    full_answer += event["content"]
                    yield event
                elif event["type"] == "finish":
                    state.status = "DONE"
                    yield event
                elif event["type"] == "error":
                    state.status = "ERROR"
                    state.error = event["message"]
                    yield {"type": "error", "message": f"生成回答时出错：{event['message']}"}
                    return
        except Exception as exc:
            state.status = "ERROR"
            state.error = str(exc)
            yield {"type": "error", "message": f"抱歉，生成回答时出错：{exc}"}
            return

        self.memory.add("assistant", full_answer)
        state.status = "DONE"

    # ── Tool 执行 ────────────────────────────

    def _execute_tool(self, plan: Plan, state: AgentState) -> None:
        state.status = "EXECUTING"

        tool_name = plan.tool_name
        tool_params = plan.tool_params or {}

        # 安全校验：Planner 可能返回不存在的 tool_name
        # 校验失败时推进 iteration，防止 Planner 反复输出无效 Plan 导致死循环
        if not self.tool_manager.has(tool_name):
            state.error = f"Tool not found: {tool_name}"
            state.iteration += 1
            return

        try:
            self.tool_manager.validate_params(tool_name, tool_params)
        except ValueError as exc:
            state.error = str(exc)
            state.iteration += 1
            return

        tool = self.tool_manager.get(tool_name)
        result = tool.execute(**tool_params)

        formatted = tool.format_result(result)
        observation = Observation(
            tool_name=tool_name,
            result=result,
            formatted=formatted,
            trace_id=state.trace_id,
        )

        state.observations.append(observation)
        self.memory.add("tool", formatted)
        state.iteration += 1

    # ── Prompt 构建 ───────────────────────────

    def _build_prompt(self, query: str, state: AgentState) -> tuple[str, str]:
        history_text = self._format_history()
        observations_text = self._format_observations(state)

        user_parts = []

        if history_text:
            user_parts.append(f"## 对话历史\n\n{history_text}")

        if observations_text:
            user_parts.append(f"## 搜索结果\n\n{observations_text}")

        user_parts.append(f"## 用户问题\n\n{query}")

        user_message = "\n\n".join(user_parts)

        return self.SYSTEM_PROMPT, user_message

    def _format_history(self) -> str:
        messages = self.memory.get_messages()
        # 过滤：只保留 user/assistant 消息，排除最后一条 user 消息
        # （最后一条 user 消息是当前轮问题，已在 "用户问题" section 中展示）
        filtered = [m for m in messages if m.role in ("user", "assistant")]
        if filtered:
            filtered = filtered[:-1]
        if not filtered:
            return ""
        return MessageFormatter.format(filtered)

    def _format_observations(self, state: AgentState) -> str:
        if not state.observations:
            return ""
        parts = []
        for obs in state.observations:
            parts.append(obs.formatted)
        return "\n\n".join(parts)

    # ── 辅助方法 ─────────────────────────────

    def run_with_trace(self, query: str) -> dict:
        started = time.perf_counter()
        answer = self.run(query)
        elapsed_ms = (time.perf_counter() - started) * 1000
        state = self._last_state
        return {
            "query": query,
            "answer": answer,
            "elapsed_ms": round(elapsed_ms, 1),
            "trace_id": state.trace_id,
            "iteration_count": state.iteration,
            "observations": [
                {
                    "tool": obs.tool_name,
                    "success": obs.result.success,
                    "latency_ms": obs.result.latency_ms,
                }
                for obs in state.observations
            ],
        }

    def clear_memory(self) -> None:
        self.memory.clear()
