"""
Memory — Agent 对话记忆模块
===========================

架构定位：
  Memory 是 Agent 的"短期记忆"。它只负责存储和检索消息，不参与推理。
  Agent 依赖 Memory(ABC) 接口，不绑定 ConversationMemory 具体实现。

依赖方向（单向）：
  Message ──依赖──→ 无（纯数据，可序列化）
  Memory(ABC) ──依赖──→ Message（抽象接口定义）
  ConversationMemory ──依赖──→ Memory(ABC)（实现抽象）
  MessageFormatter ──依赖──→ Message（只读格式化）
  Agent ──依赖──→ Memory(ABC)（不依赖具体实现）

为什么 Memory 和 Agent 分离：
  1. SRP：Memory 的职责是"存/取/清"，Agent 的职责是"编排流程"
  2. DIP：Agent 依赖接口，换 SummaryMemory / VectorMemory 不动 Agent 代码
  3. 独立测试：滑动窗口行为、消息格式化都可单独验证

为什么 summary() 返回 None：
  这是一个预留扩展点。
  当升级到 SummaryMemory 时，超出窗口的旧消息会被 LLM 摘要压缩，
  summary() 返回压缩文本，PromptBuilder 自动注入 system prompt。
  Agent 和 Memory 外的代码不需要任何改动。

MessageFormatter 为什么独立：
  Memory 返回 list[Message] 原始数据，不负责格式化。
  格式化是 PromptBuilder 的职责范围，MessageFormatter 是它的工具类。
  不同场景需要不同格式：控制台输出 → format()，LLM prompt → format_for_llm()。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ── 消息数据模型 ────────────────────────────────

@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(role=data["role"], content=data["content"])


# ── Memory 抽象接口 ─────────────────────────────
#
# 设计理由：使用 ABC 而非 Protocol。
#   1. isinstance 校验更直观
#   2. 子类可以复用 ConversationMemory 的部分逻辑
#   3. 可以在基类中提供默认实现（如 summary() → None）

class Memory(ABC):

    @abstractmethod
    def add(self, role: str, content: str) -> Message:
        ...

    @abstractmethod
    def get_messages(self) -> list[Message]:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    def summary(self) -> Optional[str]:
        return None


# ── 滑动窗口短期记忆 ─────────────────────────────
#
# 设计理由：最简单的可用实现。
#   不做压缩、不做摘要、不做向量化——只保留最近 max_messages 条消息。
#   这足以支持多轮对话的指代消解：
#     User: "什么是MCP"      → 知识库搜"MCP定义"
#     User: "它和REST的区别"  → 从 history 中找到"它"指代"MCP"，组合搜索
#
# 滑动窗口的选择：
#   - trim 操作发生在 add() 时，get_messages() 无副作用
#   - 切片而非逐条 pop——单次操作 O(n) 但 n 很小（≤20）

class ConversationMemory(Memory):

    def __init__(self, max_messages: int = 20):
        self._messages: list[Message] = []
        self._max_messages = max_messages

    def add(self, role: str, content: str) -> Message:
        msg = Message(role=role, content=content)
        self._messages.append(msg)
        self._trim()
        return msg

    def get_messages(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def summary(self) -> Optional[str]:
        return None

    def _trim(self) -> None:
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return f"ConversationMemory(messages={len(self._messages)}/{self._max_messages})"


# ── 消息格式化器 ────────────────────────────────
#
# 设计理由：格式化逻辑与存储逻辑分离。
#   Memory 负责"有什么消息"，MessageFormatter 负责"怎么呈现消息"。
#   将来 LLM 需要 OpenAI-style messages list 格式，
#   只需加 format_for_openai() 方法，Memory 不变。

class MessageFormatter:

    @staticmethod
    def format(messages: list[Message]) -> str:
        if not messages:
            return ""
        lines = []
        for msg in messages:
            role_label = MessageFormatter._role_label(msg.role)
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def format_for_llm(messages: list[Message]) -> str:
        parts = []
        for msg in messages:
            parts.append(f"[{msg.role.upper()}]\n{msg.content}")
        return "\n\n".join(parts)

    @staticmethod
    def _role_label(role: str) -> str:
        labels = {
            "user": "User",
            "assistant": "Assistant",
            "tool": "Tool",
            "system": "System",
        }
        return labels.get(role, role.capitalize())
