"""
PromptBuilder — Prompt 构建模块

职责：
  - 将用户问题 + 检索到的 Chunk 拼接为发给 LLM 的 Prompt
  - 模板可配置，方便替换和迭代

独立出来的原因：
  - Prompt 模板是迭代频率最高的部分，应单独管理
  - 修改模板时不影响检索、LLM 调用等其他模块
  - 可支持多种模板策略（默认问答、few-shot、CoT 等），方便 A/B 测试
"""

from __future__ import annotations

from src.retriever.retriever import SearchResult


DEFAULT_SYSTEM_PROMPT = (
    "你是一个知识库助手。请根据提供的参考资料回答用户的问题。"
    "如果参考资料不足以回答问题，请如实说明，不要编造信息。"
    "回答时请引用参考资料的来源。"
)

DEFAULT_USER_TEMPLATE = """## 参考资料

{context}

## 用户问题

{question}

请根据以上参考资料回答问题。"""


class PromptBuilder:
    """Prompt 构建器，使用可配置的模板将检索结果和用户问题组装为 Prompt"""

    def __init__(
        self,
        system_prompt: str | None = None,
        user_template: str | None = None,
    ):
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.user_template = user_template or DEFAULT_USER_TEMPLATE

    def _format_context(self, chunks: list[SearchResult]) -> str:
        """将检索到的 Chunk 列表拼接为上下文文本，包含结构化上下文信息"""
        if not chunks:
            return "（无相关参考资料）"

        parts = []
        for i, chunk in enumerate(chunks, 1):
            lines = [f"[参考 {i}]"]

            if chunk.context_heading:
                lines.append(f"章节: {chunk.context_heading}")
            if chunk.context_doc_title:
                lines.append(f"文档: {chunk.context_doc_title}")
            if chunk.context_full_path:
                lines.append(f"路径: {chunk.context_full_path}")
            if chunk.context_prev_chunk:
                lines.append(f"前文: {chunk.context_prev_chunk}")
            if chunk.context_next_chunk:
                lines.append(f"后文: {chunk.context_next_chunk}")

            lines.append(f"相关内容: {chunk.chunk_content}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def build(
        self,
        question: str,
        chunks: list[SearchResult],
    ) -> dict[str, str]:
        """构建完整 Prompt

        Returns:
            {"system": ..., "user": ...}
        """
        context = self._format_context(chunks)
        user_message = self.user_template.format(question=question, context=context)
        return {
            "system": self.system_prompt,
            "user": user_message,
        }
