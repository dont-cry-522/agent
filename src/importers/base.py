"""
数据源导入器抽象基类

所有数据源插件（Markdown、语雀、Notion 等）都继承此类，
实现 load_documents() 方法即可接入系统。
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.models.document import Document


class BaseImporter(ABC):
    """数据源导入器抽象基类

    子类需要实现：
        load_documents() -> list[Document]

    可选覆写：
        source_name: 数据源名称（用于日志和 Document.source 字段标记）
    """

    source_name: str = "unknown"

    @abstractmethod
    def load_documents(self) -> list[Document]:
        """加载该数据源的全部文档，返回统一的 Document 列表"""
        ...

    @classmethod
    def get_source_name(cls) -> str:
        """获取数据源名称，如果实例未设则返回类默认值"""
        instance = cls.__new__(cls)
        return getattr(instance, "source_name", cls.__name__)
