"""
MarkdownImporter — 本地 Markdown 文件导入器

扫描指定目录下所有 .md 文件，递归读取子目录，
每份文件封装为一个 Document 对象。

用法：
    importer = MarkdownImporter(root_dir="knowledge")
    documents = importer.load_documents()
"""

from pathlib import Path
from typing import Optional, Union

from src.importers.base import BaseImporter
from src.models.document import Document


class MarkdownImporter(BaseImporter):
    """本地 Markdown 文件导入器，递归扫描目录"""

    source_name = "markdown"

    def __init__(
        self,
        root_dir: Union[str, Path] = "knowledge",
    ):
        self.root_dir = Path(root_dir)

    def load_documents(self) -> list[Document]:
        """递归扫描所有 .md 文件并封装为 Document 列表"""
        if not self.root_dir.exists():
            raise FileNotFoundError(
                f"知识库目录不存在: {self.root_dir.resolve()}"
            )

        md_files = sorted(self.root_dir.glob("**/*.md"))
        documents = []

        for filepath in md_files:
            try:
                doc = Document.from_markdown_file(filepath, self.root_dir)
                documents.append(doc)
            except Exception as e:
                print(f"   ⚠️  跳过无法读取的文件: {filepath} -> {e}")

        return documents

    @property
    def file_count(self) -> int:
        """统计目录下 .md 文件总数（不读取内容，仅计数）"""
        if not self.root_dir.exists():
            return 0
        return len(list(self.root_dir.glob("**/*.md")))
