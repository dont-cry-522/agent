"""
Parser registry — 按扩展名分发解析器，懒加载依赖
"""

from pathlib import Path

from src.parsers.base import DocumentParser

# 延迟导入，避免未安装依赖时直接报错
PARSER_REGISTRY: dict[str, type[DocumentParser]] = {}


def _register_builtins():
    from src.parsers.txt_parser import TxtParser
    from src.parsers.markdown_parser import MarkdownParser
    PARSER_REGISTRY.update({
        "txt": TxtParser,
        "md": MarkdownParser,
        "markdown": MarkdownParser,
    })

    try:
        from src.parsers.pdf_parser import PdfParser
        PARSER_REGISTRY["pdf"] = PdfParser
    except ImportError:
        pass

    try:
        from src.parsers.docx_parser import DocxParser
        PARSER_REGISTRY["docx"] = DocxParser
    except ImportError:
        pass

    try:
        from src.parsers.html_parser import HtmlParser
        PARSER_REGISTRY["html"] = HtmlParser
        PARSER_REGISTRY["htm"] = HtmlParser
    except ImportError:
        pass


_register_builtins()


def parse_file(file_path: Path) -> str:
    ext = file_path.suffix.lower().lstrip(".")
    parser_cls = PARSER_REGISTRY.get(ext)
    if parser_cls is None:
        supported = ", ".join(get_supported_extensions())
        raise ValueError(
            f"不支持的文件格式: .{ext}，当前支持: {supported}"
        )
    return parser_cls().parse(file_path)


def get_supported_extensions() -> list[str]:
    return sorted(PARSER_REGISTRY.keys())
