"""
DocumentParser — 文档解析器抽象基类
"""

from abc import ABC, abstractmethod
from pathlib import Path


class DocumentParser(ABC):
    """所有文档解析器的统一接口"""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        ...

    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """解析文件，返回纯文本内容"""
        ...

    @property
    def format_name(self) -> str:
        return self.supported_extensions[0] if self.supported_extensions else "unknown"
