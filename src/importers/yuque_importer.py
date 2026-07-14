"""
语雀知识库导入器（Wrap 原 YuqueClient）
继承 BaseImporter 接口，内部复用 src.yuque.client.YuqueClient

注意：语雀 OpenAPI 需要会员，当前作为预留扩展，暂不可用
"""

import asyncio
from typing import Optional

from src.importers.base import BaseImporter
from src.models.document import Document
from src.yuque.client import YuqueClient
from src.config import settings


class YuqueImporter(BaseImporter):
    """语雀知识库导入器，调用语雀 API 拉取文档"""

    source_name = "yuque"

    def __init__(
        self,
        token: Optional[str] = None,
        namespace: Optional[str] = None,
    ):
        self.token = token or settings.yuque_token
        self.namespace = namespace or settings.yuque_namespace
        self._client = YuqueClient(token=self.token)

    def load_documents(self) -> list[Document]:
        """同步封装异步方法，拉取所有语雀文档"""
        return asyncio.run(self._load_documents_async())

    async def _load_documents_async(self) -> list[Document]:
        """异步拉取所有知识库文档，转换为统一 Document 列表"""
        documents = []
        repos = await self._client.list_repos()

        for repo in repos:
            offset = 0
            while True:
                summaries = await self._client.list_docs(
                    repo.namespace, offset=offset
                )
                if not summaries:
                    break

                for s in summaries:
                    doc = await self._client.get_doc(repo.namespace, s.slug)
                    if not doc.body:
                        continue

                    documents.append(Document(
                        title=doc.title,
                        path=f"{repo.slug}/{doc.slug}",
                        content=doc.body,
                        source="yuque",
                        updated_at=doc.updated_at,
                    ))

                offset += len(summaries)
                if len(summaries) < 100:
                    break

        return documents
