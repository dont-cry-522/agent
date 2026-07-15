"""
构建 FAISS 向量索引

读取 output/chunks.json 中的所有 Chunk，
逐个生成 Embedding 向量，建立 FAISS 索引，
保存 index.faiss + metadata.json

用法：
    python scripts/build_index.py
    python scripts/build_index.py --provider bge
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embedding.provider import get_provider
from src.vectorstore.faiss_store import FAISSVectorStore


def parse_args():
    """解析 --provider 参数"""
    provider_name = "bge"
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1]
    return provider_name


def main():
    provider_name = parse_args()

    chunks_path = Path("output/chunks.json")
    if not chunks_path.exists():
        print("[ERR] 找不到 output/chunks.json")
        print("   请先运行: python scripts/build_chunks.py")
        sys.exit(1)

    # 1. 读取 Chunk
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    print(f"[file] 读取 {len(chunks)} 个 Chunk")

    # 2. 准备 texts 和 metadata
    texts = [c["chunk_content"] for c in chunks]
    metadata = [
        {
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "title": c["title"],
            "path": c["path"],
            "source": c["source"],
            "chunk_index": c["chunk_index"],
            "chunk_content": c["chunk_content"],
            "context_heading": c.get("context_heading", ""),
            "context_doc_title": c.get("context_doc_title", ""),
            "context_prev_chunk": c.get("context_prev_chunk", ""),
            "context_next_chunk": c.get("context_next_chunk", ""),
            "context_full_path": c.get("context_full_path", ""),
        }
        for c in chunks
    ]

    # 3. 生成 Embedding
    provider = get_provider(provider_name)
    print(f"[model] 使用模型: {provider_name}, 维度: {provider.dimension}")
    print(f"[embed] 正在向量化 {len(texts)} 个 Chunk ...")

    embeddings = provider.embed_documents(texts)
    print(f"   [OK] 完成 {len(embeddings)} 条向量")

    # 4. 构建 FAISS 索引
    store = FAISSVectorStore(index_dir="output")
    store.build(embeddings, metadata)
    store.save()

    print(f"\n[done] 索引构建完成！{store.count} 条向量已入库")


if __name__ == "__main__":
    main()
