# Session State — 2026-07-17

## 今日进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 5.6 | 多格式文档上传（PDF/DOCX/TXT/HTML） | ✅ |
| Phase 5.7 | 前端响应式适配 + 引用面板拖拽 | ✅ |
| Phase 6.1 | SQLAlchemy + SQLite 持久化层（Conversation/Message/Document） | ✅ |
| Phase 6.2 | PersistentConversationMemory（滑动窗口 + SQLite） | ✅ |
| Phase 6.3 | Conversation API（创建/列表/详情/删除） | ✅ |
| Phase 6.4 | 前端多会话支持（侧栏对话列表 + 切换/删除） | ✅ |
| Phase 6.5 | RAG Citation — LLM [1][2] 行内引用 + PromptBuilder 结构化上下文 | ✅ |
| Phase 6.6 | 文档管理 SQLite 化（DocumentRecord + DocumentRepository） | ✅ |
| Phase 6.7 | 增量索引 — IndexIDMap + hash 去重 + 单文档更新 | ✅ |
| Phase 6.8 | HuggingFace 镜像 + Reranker 加载容错 | ✅ |
| Phase 6.9 | Agent `or` fallback bug 修复 | ✅ |
| Phase 6.10 | 数据库自动迁移（新列自动 ALTER TABLE） | ✅ |

## 历史已完成

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1-3 | 基础 RAG 管道：Markdown → Chunk → Embedding → FAISS → Search | ✅ |
| Phase 3+ | Retriever + PromptBuilder + DeepSeekLLM + chat.py | ✅ |
| Phase 3++ | Web 前端 + 一键启动 | ✅ |
| Phase 4.1 | Chunk 上下文增强（标题/前后文/路径） | ✅ |
| Phase 4.2 | Hybrid Search（BM25 + jieba + RRF 融合） | ✅ |
| Phase 4.3 | Cross-Encoder Reranking（Recall → Rerank 两阶段） | ✅ |
| Phase 4.4 | Query Rewriting（LLM 查询改写） | ✅ |
| Phase 4.5 | Agent Runtime（Tool / Memory / Planner / Agent 编排） | ✅ |
| Phase 4.6 | Agent 接管系统入口 | ✅ |
| Phase 5 | Web 重构：FastAPI + React + TypeScript + TailwindCSS + SSE 流式 | ✅ |
| Phase 5.1 | 文档管理：上传/列表/删除/索引 | ✅ |
| Phase 5.2 | 聊天优化：Markdown 渲染 + 代码高亮 + Token 统计 | ✅ |
| Phase 5.3 | 部署：Dockerfile + .dockerignore + DEPLOY.md + ngrok | ✅ |
| Phase 5.4 | 项目改名：yuque-agent → DocAgent | ✅ |
| Phase 5.5 | README 完善 | ✅ |

## 下一任务

| 阶段 | 内容 |
|------|------|
| Phase 7 | LLM Planner 升级（替换 RuleBasedPlanner） |
| Phase 8 | 多 Tool 扩展（Calculator / WebSearch / SQL） |
| Phase 9 | RAGAS 质量评估 |
| Phase 10 | 前端多知识库选择 |

## 启动命令

```bash
# 生产模式（一键启动）
python start.py

# 开发模式（热更新）
python start.py --dev
```

## 环境要点

| 项 | 值 |
|----|-----|
| Python | 3.11.15 |
| PyTorch | 2.5.1 |
| DeepSeek API Key | sk-1afc165... (已配置) |
| Embedding | BAAI/bge-small-zh-v1.5 (~100MB) |
| Reranker | BAAI/bge-reranker-v2-m3 (~2.2GB, 可开关) |
| HuggingFace 镜像 | hf-mirror.com |
| 检索耗时 | Hybrid ~500ms, Rerank ~1s, LLM ~2s |
| 前端 | React 19 + Vite + TypeScript + TailwindCSS |
| 后端 | FastAPI + Agent Runtime |
| 数据库 | SQLite (data/docagent.db) |
| 项目名 | DocAgent |
| GitHub | github.com/dont-cry-522/DocAgent |

## 文档索引

| 文件 | 用途 |
|------|------|
| `README.md` | 项目首页 + 技术栈 + 快速开始 |
| `GUIDE.md` | 完整用户手册 |
| `DESIGN.md` | 设计决策 + 优化对比 |
| `PRODUCT_DESIGN.md` | 产品设计方案 |
| `DEPLOY.md` | 部署指南（Docker / Render） |
| `SESSION.md` | 本文件，进度追踪 |
