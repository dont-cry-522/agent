"""
Planner — Agent 决策层
======================

架构定位：
  Planner 是"大脑"。它决定下一步做什么，但不动手。
  Agent 是"手脚"。它执行 Planner 的决策，但不动脑。
  这种分工让决策策略和执行机制可以独立演化。

依赖方向（单向）：
  Plan ──依赖──→ 无（纯数据）
  Planner(ABC) ──依赖──→ Plan + Message + ToolMetadata（只读元数据）
  RuleBasedPlanner ──依赖──→ Planner(ABC)（实现抽象）
  Agent ──依赖──→ Planner(ABC)（不依赖具体实现）

为什么 Planner 和 Agent 分离：
  1. 变化频率不同：Planner 策略 V1→V2→V3 变 3 次，Agent 编排不变
  2. 安全边界：Planner 返回"建议"Plan，Agent 执行前校验 tool_name 是否存在
  3. 可测试：纯函数 decide(input) → Plan，不依赖 Memory / Tool / LLM

为什么 Plan 是纯数据类：
  Plan 不包含行为——没有 execute()，没有 apply()。
  Action 在 Agent 里，不在 Plan 里。
  这让 Plan 可序列化、可日志、可在分布式 Agent 中跨进程传递。

如何升级为 LLM Planner：
  LLMPlanner(Planner) 替换 RuleBasedPlanner，Agent 一行代码不变。
  LLMPlanner.decide() 内部：
    1. 把 tool_metadata 注入 system prompt（让 LLM 知道可用工具）
    2. LLM 输出 JSON {"action": "call_tool", "tool_name": "...", ...}
    3. 解析 JSON → Plan
    4. 解析失败则兜底 Plan.respond() 避免 Agent 收到 undefined behavior
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.agent.memory import Message
from src.agent.tool import ToolMetadata


# ── 决策结果 ────────────────────────────────────
#
# 设计理由：三种工厂方法覆盖所有场景。
#   Plan.call_tool()  → Planner 确定要调用某个工具
#   Plan.respond()    → Planner 判断不需要工具，直接回答
#   将来升级多步推理后：
#   Plan.think()      → Planner 需要先思考但还不能决定
#
# should_call_tool / should_respond 属性：
#   让 Agent 的条件分支代码从 if plan.action == "call_tool"
#   变成 if plan.should_call_tool，语义更清晰，魔法字符串不出 Agent。

@dataclass
class Plan:
    action: str
    tool_name: str | None = None
    tool_params: dict | None = field(default_factory=dict)
    reason: str = ""

    @classmethod
    def call_tool(cls, tool_name: str, params: dict | None = None, reason: str = "") -> "Plan":
        return cls(
            action="call_tool",
            tool_name=tool_name,
            tool_params=params or {},
            reason=reason,
        )

    @classmethod
    def respond(cls, reason: str = "") -> "Plan":
        return cls(action="respond", reason=reason)

    @property
    def should_call_tool(self) -> bool:
        return self.action == "call_tool"

    @property
    def should_respond(self) -> bool:
        return self.action == "respond"


# ── Planner 抽象 ────────────────────────────────
#
# 设计理由：available_tools 类型是 list[ToolMetadata] 而非 list[Tool]。
#   这是 ISP（接口隔离）：
#     ToolMetadata 只有 name + description + parameters（描述性字段）
#     Tool 多了一个 execute()（行为能力）
#   Planner 不应该能调用工具，只应该能参考工具的元数据做决策。
#   物理上杜绝"Planner 直接调 tool.execute()"的可能性。

class Planner(ABC):

    @abstractmethod
    def decide(
        self,
        query: str,
        history: list[Message],
        available_tools: list[ToolMetadata],
    ) -> Plan:
        ...


# ── 规则版 Planner ──────────────────────────────
#
# 设计理由：V1 不用 LLM 做规划。
#   1. 成本：每次查询都要调 LLM → 延迟高 + API 费用
#   2. 确定性：正则规则 100% 可预测，LLM 可能有幻觉
#   3. 渐进升级：先用规则跑通全流程，再替换为 LLM Planner 做 A/B 对比
#
# 决策策略（两层过滤）：
#   1. 寒暄过滤 → "你好""谢谢"等直接 respond
#   2. 知识模式匹配 → 17 种中文疑问模式
#   3. 长度兜底 → 即使没匹配模式，≥ 8 字也视为可能的知识问答
#
# 为什么用正则而非关键词匹配：
#   "为什么自研比LangChain更有价值" → 关键词可能漏掉"为什么"
#   正则 /为什么|为何/ → 覆盖所有疑问变体

class RuleBasedPlanner(Planner):

    KNOWLEDGE_PATTERNS: list[str] = [
        r"[是什么|什么是|什么叫|啥是|啥叫]",
        r"如[何|怎么|怎样]",
        r"为[什么|啥|何]",
        r"[讲讲|介绍|说明|解释|阐述|描述]一下",
        r"如何[使用|实现|配置|部署|安装]",
        r"区别|对比|比较|差异",
        r"[总结|概括|归纳]",
        r"[列举|列出|有哪些|哪几个]",
        r"原理|机制|流程|架构",
        r"定义|概念|术语",
        r"[优缺点|优势|劣势|缺点|不足]",
        r"[步骤|方法|做法|方案]",
        r"示例|例子|案例|demo",
        r"最佳实践|推荐做法",
        r"注意事项|坑|常见问题",
        r"源码|代码|实现",
    ]

    CHAT_PATTERNS: list[str] = [
        r"^[你好您好嗨嘿哈嘿哟]{1,4}$",
        r"^[谢谢多谢感谢谢了thankyou]{2,6}$",
        r"^[再见拜拜byebye]{2,8}$",
        r"^[ok好的行可以没问题]{2,6}$",
    ]

    def __init__(self, min_query_length: int = 4):
        self._min_query_length = min_query_length

    def decide(
        self,
        query: str,
        history: list[Message],
        available_tools: list[ToolMetadata],
    ) -> Plan:
        if self._is_chat(query):
            return Plan.respond(reason="寒暄/闲聊")
        # 如果历史中已有搜索结果，不再重复调用工具
        if self._already_searched(history):
            return Plan.respond(reason="已搜索过，直接回答")
        if self._is_knowledge_question(query):
            return self._build_knowledge_plan(query, available_tools)
        return Plan.respond(reason="非知识类问题")

    def _already_searched(self, history: list[Message]) -> bool:
        for msg in history:
            if msg.role == "tool" and "search_knowledge" in msg.content:
                return True
        return False

    def _is_knowledge_question(self, query: str) -> bool:
        stripped = query.strip()
        if len(stripped) < self._min_query_length:
            return False
        for pattern in self.KNOWLEDGE_PATTERNS:
            if re.search(pattern, stripped):
                return True
        return len(stripped) >= 8

    def _is_chat(self, query: str) -> bool:
        stripped = query.strip().lower()
        for pattern in self.CHAT_PATTERNS:
            if re.match(pattern, stripped):
                return True
        return False

    def _build_knowledge_plan(
        self,
        query: str,
        available_tools: list[ToolMetadata],
    ) -> Plan:
        knowledge_tool = None
        for tool in available_tools:
            if tool.name == "search_knowledge":
                knowledge_tool = tool
                break

        if knowledge_tool is None:
            return Plan.respond(reason="知识库工具不可用")

        return Plan.call_tool(
            tool_name="search_knowledge",
            params={"query": query, "top_k": 5},
            reason=f"知识问答，调用 {knowledge_tool.name}",
        )
