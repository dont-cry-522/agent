"""
DocxParser — Word 文档解析（基于 python-docx）
"""

from pathlib import Path

from src.parsers.base import DocumentParser


class DocxParser(DocumentParser):

    @property
    def supported_extensions(self) -> list[str]:
        return ["docx"]

    def parse(self, file_path: Path) -> str:
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # 识别标题样式
                if para.style and para.style.name and para.style.name.startswith("Heading"):
                    level = para.style.name.split()[-1]
                    try:
                        level_num = int(level)
                        prefix = "#" * min(level_num, 6) + " "
                        paragraphs.append(f"{prefix}{text}")
                        continue
                    except ValueError:
                        pass
                paragraphs.append(text)
        return "\n\n".join(paragraphs)
