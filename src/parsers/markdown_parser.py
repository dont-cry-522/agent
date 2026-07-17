"""
MarkdownParser — Markdown 文件解析（直接读取原始内容）
"""

from pathlib import Path

from src.parsers.base import DocumentParser


class MarkdownParser(DocumentParser):

    @property
    def supported_extensions(self) -> list[str]:
        return ["md", "markdown"]

    def parse(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")
