"""
QueryRewriter — LLM 查询改写模块
================================

架构定位：
  QueryRewriter 是检索前置处理——在查询进入 Retriever 之前，
  用 LLM 将用户的口语化问题改写为更适合搜索引擎的关键词查询。

依赖方向（单向）：
  QueryRewriter ──依赖──→ DeepSeekLLM（复用现有 LLM 客户端）
  SearchKnowledgeTool ──依赖──→ QueryRewriter（可选注入）
  Agent ──不知道──→ QueryRewriter 的存在（Tool 内部优化）

和 Multi-Query 的区别：
  当前 V1 只生成一条改写查询。Multi-Query（生成多条查询→并行搜索→RRF 合并）
  可提升召回但增加 N 倍搜索延迟，留作 Phase 4.4+。

设计原则（从 DESIGN.md 延续）：
  - 单文件：QueryRewriter 内聚在一个模块中，无子目录
  - DI 注入：构造时传入 LLM 实例，不自建
  - 可选注入：SearchKnowledgeTool 的 query_rewriter 为 Optional
  - 不影响原有逻辑：rewriter 为 None 时行为与 Phase 4.3 完全一致
"""

from __future__ import annotations

from src.llm.deepseek import DeepSeekLLM


REWRITE_SYSTEM_PROMPT = (
    "你是一个搜索查询优化器。将用户的口语化问题改写为更适合知识库搜索引擎的关键词查询。\n\n"
    "改写规则：\n"
    "1. 提取核心概念和专业术语，去除礼貌用语和寒暄\n"
    "2. 展开缩写和简称（如 MCP→Model Context Protocol）\n"
    "3. 补充关键同义词或替代表述，用空格分隔\n"
    "4. 保持查询简洁，聚焦可搜索的关键词\n"
    "5. 保留原始问题意图，不添加无关信息\n"
    "6. 只输出改写后的查询文本，不要加引号、解释或任何前缀"
)


class QueryRewriter:
    """LLM 查询改写器

    构造时注入 LLM 实例，rewrite() 返回改写后的查询字符串。

    使用方式：
        rewriter = QueryRewriter(llm)
        rewritten = rewriter.rewrite("什么是MCP")
        # → "Model Context Protocol MCP 定义 概念 原理 架构"
    """

    def __init__(self, llm: DeepSeekLLM):
        self._llm = llm

    def rewrite(self, query: str) -> str:
        """将原始查询改写为优化后的搜索查询

        Args:
            query: 用户原始问题

        Returns:
            改写后的查询字符串。如果 LLM 调用失败，返回原始 query 作为降级。
        """
        try:
            rewritten = self._llm.chat(
                system_prompt=REWRITE_SYSTEM_PROMPT,
                user_message=query,
                temperature=0.3,
                max_tokens=128,
            )
            rewritten = rewritten.strip()
            if not rewritten or len(rewritten) < 2:
                return query
            return rewritten
        except Exception:
            return query
