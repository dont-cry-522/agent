"""
Markdown 数据摄入入口脚本

扫描 knowledge/ 目录下所有 .md 文件，
调用 MarkdownImporter 封装为统一 Document 对象

用法：
    python scripts/import_markdown.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.importers.markdown_importer import MarkdownImporter


def format_timestamp(ts: object) -> str:
    """将时间戳或时间字符串转为可读格式"""
    if ts is None:
        return ""

    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(ts, str):
        value = ts.strip()
        if not value:
            return ""

        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

    return str(ts)


def main():
    root_dir = Path("knowledge")
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    importer = MarkdownImporter(root_dir=root_dir)

    # 1. 统计
    file_count = importer.file_count
    print(f"📁 扫描目录: {root_dir.resolve()}")
    print(f"📄 共发现 {file_count} 个 Markdown 文件\n")

    if file_count == 0:
        print("💡 提示：请将 .md 文件放入 knowledge/ 目录，支持子目录递归扫描")
        return

    # 2. 导入
    documents = importer.load_documents()

    # 3. 输出统计
    print(f"✅ 成功导入 {len(documents)} 篇文档\n")

    for doc in documents[:5]:  # 预览前5篇
        print(f"   📝 {doc.title}")
        print(f"      路径: {doc.path}")
        print(f"      来源: {doc.source}")
        print(f"      更新: {format_timestamp(doc.updated_at)}")
        print(f"      大小: {len(doc.content)} 字符")
        print()

    if len(documents) > 5:
        print(f"   ... 还有 {len(documents) - 5} 篇文档")

    # 4. 导出 JSON（便于后续处理）
    output_path = output_dir / "documents.json"
    output_path.write_text(
        json.dumps(
            [doc.to_dict() for doc in documents],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n💾 已导出 -> {output_path}")


if __name__ == "__main__":
    main()
