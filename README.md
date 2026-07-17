# DocAgent — Enterprise Knowledge Agent

> 把你的文档变成可对话的知识库。上传 Markdown / PDF / Word / TXT / HTML，像 ChatGPT 一样多轮对话，像 Perplexity 一样引用来源。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 这是什么

**DocAgent** 是一个本地优先的企业级 RAG 知识库 Agent 系统。上传文档后自动解析、切片、向量化、建立索引，然后用自然语言提问，系统检索相关内容，结合 LLM 生成带引用来源的回答。

所有数据完全本地，不上传任何第三方。

## 核心能力

| 能力 | 说明 |
|------|------|
| 多格式文档 | .md .pdf .docx .txt .html 自动解析 |
| 混合检索 | FAISS 向量 + BM25 关键词 + RRF 融合 |
| 精排增强 | Cross-encoder Reranker 对 Top 20 重排序 |
| 查询改写 | LLM 自动将口语化问题改写为搜索优化查询 |
| 行内引用 | 回答中标注 `[1][2]`，右侧面板展示来源详情 |
| 多轮对话 | SQLite 持久化，刷新不丢历史 |
| 对话管理 | 创建/切换/删除对话，侧栏对话列表 |
| 增量索引 | 同名文档 hash 去重，修改不重建全部索引 |
| 流式输出 | SSE 逐 token 渲染 + Markdown + 代码高亮 |
| 自研 Agent | Tool / Memory / Planner 三层解耦，可扩展 |
| 一键启动 | `python start.py`，纯 CPU 运行 |

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                          │
│   Sidebar (对话列表/知识库) │ ChatArea │ CitationPanel (引用)    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP REST / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                    FastAPI (api/main.py)                          │
│   /api/conversations  /api/documents  /api/chat  /api/chat/stream│
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Agent Runtime                                 │
│   Memory ─→ Planner ─→ Tool(search_knowledge) ─→ LLM(DeepSeek)  │
│     │                      │                           │          │
│  SQLite                Retriever                  PromptBuilder  │
│ (持久化)           (Hybrid + RRF)              (结构化上下文)     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     RAG Pipeline                                  │
│  Query → QueryRewriter → Embedding(BGE) → FAISS + BM25          │
│                                      ↓                            │
│                              RRF Fusion → Reranker(Cross-enc)    │
│                                      ↓                            │
│                              Top 5 SearchResult → LLM            │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 安装（仅首次）
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 DEEPSEEK_API_KEY

# 启动（每次使用只需这一条）
python start.py
# 浏览器打开 http://127.0.0.1:8000
```

> 所有数据本地存储，关闭后重启不丢失：对话历史在 `data/docagent.db`，索此在 `output/`，上传文件在 `uploads/`。

## 开发模式

```bash
python start.py --dev
# 前端 → http://localhost:5173 (热更新)
# 后端 → http://127.0.0.1:8000
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript + Vite + TailwindCSS + react-markdown |
| 后端 | Python 3.11 + FastAPI + uvicorn |
| 数据库 | SQLite + SQLAlchemy 2.0 |
| Agent Runtime | 自研（Tool/Memory/Planner 三层抽象） |
| 文档解析 | PyMuPDF + python-docx + BeautifulSoup + LangChain TextSplitter |
| Embedding | BAAI/bge-small-zh-v1.5 (512d, CPU) |
| 向量检索 | FAISS IndexIDMap(IndexFlatIP) |
| 关键词检索 | BM25 (rank-bm25) + jieba 分词 |
| RRF 融合 | Reciprocal Rank Fusion (k=60) |
| 精排 | BAAI/bge-reranker-v2-m3 (Cross-encoder, 可关闭) |
| LLM | DeepSeek Chat API |
| 部署 | Docker / Render / ngrok |

## 目录结构

```
DocAgent/
├── api/                    # FastAPI 服务层
│   ├── main.py             # 路由入口 (14 个端点)
│   ├── schemas.py          # Pydantic 请求/响应模型
│   └── document_manager.py # 文档生命周期管理
├── src/                    # 核心库
│   ├── config.py           # 配置管理 (pydantic-settings)
│   ├── agent/              # Agent Runtime
│   │   ├── agent.py        #   编排核心
│   │   ├── tool.py         #   Tool 抽象 + ToolManager
│   │   ├── memory.py       #   Memory(ABC) + 持久化实现
│   │   ├── planner.py      #   Planner(ABC) + 规则实现
│   │   └── query_rewriter.py # 查询改写
│   ├── retriever/          # 检索器
│   │   ├── retriever.py    #   Hybrid Search + RRF
│   │   └── bm25.py         #   BM25 关键词检索
│   ├── reranker/           # Cross-encoder 精排
│   ├── embedding/          # BGE Embedding 模型
│   ├── vectorstore/        # FAISS 向量索引
│   ├── ingestion/          # 文档切片器
│   ├── prompt/             # Prompt 构建器
│   ├── llm/                # DeepSeek API 客户端
│   ├── parsers/            # 多格式文档解析器
│   ├── models/             # Document/Chunk 数据模型
│   ├── importers/          # 数据源导入器
│   └── yuque/              # 语雀 API 客户端（预留）
├── storage/                # 持久化层
│   ├── database.py         # SQLite 引擎 + 自动迁移
│   ├── models.py           # ORM 模型
│   └── repository.py       # CRUD Repository
├── web/                    # React 前端
│   └── src/components/     # ChatArea/Sidebar/CitationPanel/DocumentsPage
├── scripts/                # CLI 工具
│   ├── build_index.py      # 构建 FAISS 索引
│   ├── build_chunks.py     # 文档切片
│   ├── import_markdown.py  # Markdown 导入
│   ├── search.py           # 语义检索
│   └── chat.py             # CLI 聊天
├── knowledge/              # 本地 Markdown 知识库
├── uploads/                # 用户上传文件
├── output/                 # FAISS 索引 + metadata
├── data/                   # SQLite 数据库
└── tests/                  # 测试
```

## 文档

| 文件 | 内容 |
|------|------|
| [GUIDE.md](./GUIDE.md) | 安装、配置、使用手册 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 整体架构与设计原则 |
| [DESIGN.md](./DESIGN.md) | 设计决策与优化记录 |
| [API.md](./API.md) | REST API 文档 |
| [DEPLOY.md](./DEPLOY.md) | 部署指南 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本演进 |

## License

MIT
