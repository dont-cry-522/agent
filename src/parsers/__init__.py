"""
Parsers — 多格式文档解析器
==========================

支持的格式：
    .md   — 直接读取原始内容
    .txt  — 纯文本
    .pdf  — PyMuPDF 提取（需 pip install PyMuPDF）
    .docx — python-docx 提取（需 pip install python-docx）
    .html — BeautifulSoup 提取（需 pip install beautifulsoup4）

使用方式：
    from src.parsers import parse_file
    content = parse_file(Path("document.pdf"))  # 返回纯文本
"""

from src.parsers.base import DocumentParser
from src.parsers.registry import parse_file, get_supported_extensions, PARSER_REGISTRY
