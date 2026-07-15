"""
语义检索脚本

加载 FAISS 索引 + metadata，对用户查询做语义检索，返回 Top-K 结果

用法：
    python scripts/search.py "你的查询文本"
    python scripts/search.py "Python 异步编程" --top 3
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embedding.provider import get_provider
from src.vectorstore.faiss_store import FAISSVectorStore


def main():
    # 解析参数
    args = sys.argv[1:]
    if not args:
        print("用法: python scripts/search.py \"查询文本\" [--top N]")
        sys.exit(1)

    query = args[0]
    top_k = 5

    # --top 参数
    i = 1
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            i += 2
        else:
            i += 1

    # 1. 加载索引
    store = FAISSVectorStore(index_dir="output")
    if not store.load():
        print("[ERR] 索引不存在，请先运行: python scripts/build_index.py")
        sys.exit(1)

    # 2. 查询向量化
    provider = get_provider("bge")
    query_vec = provider.embed_query(query)

    # 3. 检索
    results = store.search(query_vec, top_k=top_k)

    # 4. 输出
    print(f"\n[search] 查询: \"{query}\"\n")
    print(f"Top-{len(results)} 最相关 Chunk:\n")

    for i, (meta, score) in enumerate(results):
        print(f"── [{i + 1}] 相似度: {score:.4f} ──")
        print(f"    标题: {meta['title']}")
        print(f"    路径: {meta['path']}")
        print(f"    来源: {meta['source']}")
        print(f"    Chunk 序号: {meta['chunk_index']}")
        print(f"    内容: {meta['chunk_content'][:150]}{'...' if len(meta['chunk_content']) > 150 else ''}")
        print()


if __name__ == "__main__":
    main()
