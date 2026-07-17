"""
HtmlParser — HTML 文件解析（基于 BeautifulSoup）
"""

from pathlib import Path

from src.parsers.base import DocumentParser


class HtmlParser(DocumentParser):

    @property
    def supported_extensions(self) -> list[str]:
        return ["html", "htm"]

    def parse(self, file_path: Path) -> str:
        from bs4 import BeautifulSoup

        html = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
