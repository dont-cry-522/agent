# Session State — 2026-07-16

## 当前进度

### 已完成

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
| Phase 5 | Web 重构：FastAPI + React + TypeScript + TailwindCSS + 流式输出 | ✅ |
| Phase 5.1 | 文档管理：上传/列表/删除/增量索引/全量重建 | ✅ |
| Phase 5.2 | 聊天优化：SSE 流式输出 + Markdown 渲染 + 代码高亮 + Token 统计 | ✅ |
| Phase 5.3 | 部署：Dockerfile + .dockerignore + DEPLOY.md + ngrok | ✅ |
| Phase 5.4 | 项目改名：yuque-agent → DocAgent | ✅ |
| Phase 5.5 | README 完善 + 简历文案 | ✅ |

### 下一任务

| 阶段 | 内容 |
|------|------|
| Phase 6 | 服务化：FastAPI 生产优化 + 可观测性 |
| Phase 7 | LLM Planner 升级（替换 RuleBasedPlanner） |
| Phase 8 | 多 Tool 扩展（Calculator / WebSearch / SQL） |
| Phase 9 | 多 Agent 协作 |

---

## 启动命令

```bash
# 生产模式（一键启动）
python start.py

# 开发模式（热更新）
python start.py --dev

# 面试 Demo（ngrok 暴露公网）
python start.py          # 终端 1
.\ngrok.exe http 8000    # 终端 2
```

## 环境要点

| 项 | 值 |
|---|---|
| Python | 3.11.15 |
| PyTorch | 2.5.1 |
| DeepSeek API Key | sk-1afc165... (已配置) |
| Embedding | BAAI/bge-small-zh-v1.5 (~100MB) |
| Reranker | BAAI/bge-reranker-v2-m3 (~2.2GB, 可开关) |
| 检索耗时 | Hybrid ~500ms, Rerank ~1s, LLM ~2s |
| 前端 | React + Vite + TypeScript + TailwindCSS |
| 后端 | FastAPI + Agent Runtime |
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
