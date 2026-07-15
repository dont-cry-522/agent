"""
Chat REPL — 交互式 RAG 对话（两阶段检索）

用法：
    python scripts/chat.py

流程：
    User 输入 → Hybrid Search (Recall Top 20) → Reranker (Top 5) → PromptBuilder → DeepSeek → Answer
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embedding.provider import get_provider
from src.llm.deepseek import DeepSeekLLM
from src.prompt.builder import PromptBuilder
from src.retriever.retriever import Retriever
from src.retriever.bm25 import BM25Retriever
from src.reranker.reranker import BGEReranker
from src.vectorstore.faiss_store import FAISSVectorStore


TOP_K = 5
RECALL_K = 5


def main():
    # 1. 加载 FAISS 索引
    store = FAISSVectorStore(index_dir="output")
    if not store.load():
        print("[ERR] 索引不存在，请先运行: python scripts/build_index.py")
        sys.exit(1)
    print(f"[load] 已加载 {store.count} 条向量")

    # 2.5 初始化 BM25
    metadata_path = Path("output/metadata.json")
    chunks = json.loads(metadata_path.read_text(encoding="utf-8"))
    bm25 = BM25Retriever(chunks)
    print(f"[BM25] 语料库: {len(chunks)} 条文档\n")

    # 2. 初始化各组件
    provider = get_provider("bge")
    _ = provider.embed_query("warmup")  # 触发 JIT 预热
    retriever = Retriever(store, provider, bm25_retriever=bm25)
    reranker = BGEReranker()
    reranker._load_model()  # 触发 JIT 预热
    prompt_builder = PromptBuilder()
    llm = DeepSeekLLM()

    print("[chat] 输入你的问题，Enter 发送（输入 q 退出）\n")

    while True:
        try:
            user_input = input("User：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "exit"):
            break

        # Step 1: Recall Top 20
        recall_results = retriever.retrieve(user_input, top_k=RECALL_K)

        # Step 2: Rerank Top 5
        reranked = reranker.rerank(user_input, recall_results, top_k=TOP_K)

        print(f"\n======== Recall Top {len(recall_results)} ========")
        for i, r in enumerate(recall_results[:20], 1):
            print(f"[{i:2d}] {r.title[:20]} | Vec:{r.score:.3f} BM25:{r.bm25_score:.3f} RRF:{r.fusion_score:.4f}")

        print(f"\n======== Rerank Top {len(reranked)} ========")
        for i, r in enumerate(reranked, 1):
            print(f"[{i}] 标题：{r.title}")
            print(f"    路径：{r.path}")
            print(f"    Rerank：{r.rerank_score:.4f}  (Vec:{r.score:.3f} BM25:{r.bm25_score:.3f} RRF:{r.fusion_score:.4f})")
            print(f"    内容：{r.summary}")
            print()

        if not reranked:
            print("未找到相关参考资料。")
            print()
            continue

        # Step 3: 构建 Prompt
        messages = prompt_builder.build(user_input, reranked)

        # Step 3: 调用 LLM
        print("======== LLM Answer ========")
        try:
            answer = llm.chat(messages["system"], messages["user"])
            print(answer)
        except Exception as e:
            print(f"[ERR] LLM 调用失败: {e}")
        print()

    print("[bye] 再见！")


if __name__ == "__main__":
    main()
