"""
语雀 API 客户端（异步）
封装语雀开放 API v2，用于拉取知识库和文档内容

API 文档: https://www.yuque.com/yuque/developer/api
"""

from __future__ import annotations
from typing import Optional
import httpx
from dataclasses import dataclass, field
from src.config import settings


# ── 数据模型 ─────────────────────────────────────────


@dataclass
class Repo:
    """语雀知识库"""
    id: int
    slug: str
    name: str
    namespace: str          # 格式: owner_login/repo_slug
    description: str = ""


@dataclass
class DocSummary:
    """语雀文档摘要（列表中的一项）"""
    id: int
    slug: str
    title: str
    updated_at: str


@dataclass
class Doc:
    """语雀文档完整内容"""
    id: int
    slug: str
    title: str
    body: str               # Markdown 格式正文
    updated_at: str


# ── 客户端 ───────────────────────────────────────────


class YuqueClient:
    """语雀 API 异步客户端"""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.token = token or settings.yuque_token
        self.base_url = (base_url or settings.yuque_base_url).rstrip("/")
        self._headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json",
            "User-Agent": "DocAgent/2.0",
        }

    # ── 内部工具方法 ─────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """发送 GET 请求并返回 JSON data 字段"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("data", payload)

    # ── 公开方法 ─────────────────────────────────

    async def get_user(self) -> dict:
        """获取当前用户信息，验证 token 是否有效"""
        return await self._get("/user")

    async def list_repos(self, login: Optional[str] = None) -> list[Repo]:
        """获取指定用户/团队下的所有知识库列表"""
        user = await self.get_user()
        login = login or user.get("login", "")
        data = await self._get(f"/users/{login}/repos")
        repos = []
        for item in data:
            repos.append(Repo(
                id=item["id"],
                slug=item["slug"],
                name=item["name"],
                namespace=item.get("namespace", ""),
                description=item.get("description", ""),
            ))
        return repos

    async def list_docs(
        self, repo_namespace: str, offset: int = 0
    ) -> list[DocSummary]:
        """分页获取知识库中的文档列表（每页最多 100 条）"""
        data = await self._get(
            f"/repos/{repo_namespace}/docs",
            params={"offset": offset},
        )
        summaries = []
        for item in data:
            summaries.append(DocSummary(
                id=item["id"],
                slug=item["slug"],
                title=item["title"],
                updated_at=item.get("updated_at", ""),
            ))
        return summaries

    async def get_doc(
        self, repo_namespace: str, doc_slug: str
    ) -> Doc:
        """获取单篇文档完整内容（包含 Markdown body）"""
        item = await self._get(f"/repos/{repo_namespace}/docs/{doc_slug}")
        return Doc(
            id=item["id"],
            slug=item["slug"],
            title=item["title"],
            body=item.get("body", ""),
            updated_at=item.get("updated_at", ""),
        )

    async def fetch_all_docs(self) -> list[tuple[Repo, Doc]]:
        """一键拉取所有知识库的全部文档"""
        repos = await self.list_repos()
        result = []
        for repo in repos:
            offset = 0
            while True:
                summaries = await self.list_docs(repo.namespace, offset=offset)
                if not summaries:
                    break
                for s in summaries:
                    doc = await self.get_doc(repo.namespace, s.slug)
                    result.append((repo, doc))
                offset += len(summaries)
                if len(summaries) < 100:
                    break
        return result
