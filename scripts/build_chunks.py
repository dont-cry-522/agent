"""
知识库预处理：Document → Chunk

读取 knowledge/ 下所有 .md 文件，
导入为 Document → 切片为 Chunk → 保存为 JSON

用法：
    python scripts/build_chunks.py
    python scripts/build_chunks.py --size 800 --overlap 150
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.importers.markdown_importer import MarkdownImporter
from src.ingestion.chunker import DocumentChunker


def parse_args():
    """解析命令行参数：--size 和 --overlap"""
    kwargs = {"chunk_size": 500, "chunk_overlap": 100}
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--size" and i + 1 < len(args):
            kwargs["chunk_size"] = int(args[i + 1])
            i += 2
        elif args[i] == "--overlap" and i + 1 < len(args):
            kwargs["chunk_overlap"] = int(args[i + 1])
            i += 2
        else:
            i += 1
    return kwargs


def main():
    chunk_kwargs = parse_args()

    print(f"[file] Chunk 配置: size={chunk_kwargs['chunk_size']}, "
          f"overlap={chunk_kwargs['chunk_overlap']}")
    print()

    # 1. 导入 Document
    importer = MarkdownImporter(root_dir="knowledge")
    if importer.file_count == 0:
        print("[tip] knowledge/ 目录为空，请放入 .md 文件")
        return

    documents = importer.load_documents()
    print(f"[load] 导入 {len(documents)} 篇文档")

    # 2. 切片
    chunker = DocumentChunker(**chunk_kwargs)
    chunks = chunker.split_documents(documents)
    print(f"[chop]  切片为 {len(chunks)} 个 Chunk\n")

    # 3. 预览
    for c in chunks:
        print(f"   [{c.chunk_index:02d}] {c.title}")
        print(f"        id: {c.chunk_id[:8]}... ← doc: {c.document_id[:8]}...")
        print(f"        size: {len(c.chunk_content)} 字符")
        preview = c.chunk_content[:80].replace("\n", " ")
        print(f"        content: {preview}...")
        print()

    # 4. 保存
    output_path = Path("output") / "chunks.json"
    output_path.write_text(
        json.dumps(
            [c.to_dict() for c in chunks],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[save] 已保存 {len(chunks)} 个 Chunk -> {output_path}")


if __name__ == "__main__":
    main()
