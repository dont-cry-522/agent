"""
一键拉取语雀知识库所有文档并保存为本地 Markdown 文件

用法：
    python scripts/fetch_all.py

首次运行前，请先配置 .env 文件：
    cp .env.example .env
    # 编辑 .env 填入 YUQUE_TOKEN 和 YUQUE_NAMESPACE
"""

import asyncio
import os
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保可以 import src 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.yuque.client import YuqueClient


def sanitize_filename(name: str) -> str:
    """清理文件名，移除不允许的字符"""
    # 替换路径分隔符和换行符
    name = name.replace("/", "-").replace("\\", "-")
    name = "".join(c for c in name if c not in '\n\r\t')
    return name.strip()


async def fetch_and_save():
    client = YuqueClient()

    # 1. 验证 token
    print("[auth] 验证语雀 Token...")
    user = await client.get_user()
    print(f"   登录用户: {user.get('name')} ({user.get('login')})")
    print()

    # 2. 获取知识库列表
    print("[repo] 获取知识库列表...")
    repos = await client.list_repos()
    print(f"   共找到 {len(repos)} 个知识库")
    for r in repos:
        print(f"     - {r.name} (slug: {r.slug})")
    print()

    # 3. 遍历每个知识库，拉取全部文档
    base_dir = Path(settings.markdown_store_path)
    total_docs = 0

    for repo in repos:
        repo_dir = base_dir / repo.slug
        repo_dir.mkdir(parents=True, exist_ok=True)
        print(f"[load] 拉取知识库 [{repo.name}] 的文档...")

        offset = 0
        doc_count = 0
        while True:
            summaries = await client.list_docs(repo.namespace, offset=offset)
            if not summaries:
                break

            for s in summaries:
                doc = await client.get_doc(repo.namespace, s.slug)
                if not doc.body:
                    print(f"   [WARN]  跳过空文档: {doc.title}")
                    continue

                # 保存为 Markdown 文件
                filename = sanitize_filename(doc.title)
                filepath = repo_dir / f"{filename}.md"
                filepath.write_text(doc.body, encoding="utf-8")
                doc_count += 1

            offset += len(summaries)
            if len(summaries) < 100:
                break

        print(f"   [OK] 保存 {doc_count} 篇文档 -> {repo_dir}")
        total_docs += doc_count

    print()
    print(f"[done] 完成！共拉取 {total_docs} 篇文档")


if __name__ == "__main__":
    # 检查 .env 文件是否存在
    if not Path(".env").exists():
        print("[ERR] 未找到 .env 文件，请先配置：")
        print("   cp .env.example .env")
        print("   然后编辑 .env 填入你的 YUQUE_TOKEN")
        sys.exit(1)

    asyncio.run(fetch_and_save())
