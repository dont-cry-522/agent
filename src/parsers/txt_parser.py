"""
TxtParser — 纯文本文件解析
"""

from pathlib import Path

from src.parsers.base import DocumentParser


class TxtParser(DocumentParser):

    @property
    def supported_extensions(self) -> list[str]:
        return ["txt"]

    def parse(self, file_path: Path) -> str:
        raw = file_path.read_bytes()
        for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")
