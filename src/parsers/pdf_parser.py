"""
PdfParser — PDF 文件解析（基于 PyMuPDF）
"""

from pathlib import Path

from src.parsers.base import DocumentParser


class PdfParser(DocumentParser):

    @property
    def supported_extensions(self) -> list[str]:
        return ["pdf"]

    def parse(self, file_path: Path) -> str:
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text.strip())
        doc.close()

        return "\n\n".join(pages)
