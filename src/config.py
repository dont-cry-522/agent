"""
统一配置管理模块
使用 pydantic-settings 从 .env 文件加载配置，提供类型安全和校验
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """应用全局配置，所有配置项从环境变量或 .env 文件加载"""

    # ── 语雀 API ──────────────────────────────
    yuque_token: str = Field(
        default="", alias="YUQUE_TOKEN"
    )
    yuque_namespace: str = Field(
        default="", alias="YUQUE_NAMESPACE"
    )
    yuque_base_url: str = Field(
        default="https://www.yuque.com/api/v2", alias="YUQUE_BASE_URL"
    )

    # ── DeepSeek API ───────────────────────────
    deepseek_api_key: str = Field(..., alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )

    # ── Embedding 模型 ─────────────────────────
    embedding_model_name: str = Field(
        default="BAAI/bge-small-zh-v1.5", alias="EMBEDDING_MODEL_NAME"
    )

    # ── Reranker 模型 ──────────────────────────
    reranker_model_name: str = Field(
        default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL_NAME"
    )

    # ── 向量库 ────────────────────────────────
    faiss_index_path: str = Field(default="data/faiss", alias="FAISS_INDEX_PATH")

    # ── 本地文档存储 ───────────────────────────
    markdown_store_path: str = Field(
        default="data/markdown", alias="MARKDOWN_STORE_PATH"
    )

    # ── 服务 ──────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# 全局单例，其他模块直接 import 使用
settings = Settings()
