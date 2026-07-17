# DocAgent — Enterprise Knowledge Agent

> 把你的文档变成可对话的知识库。上传 Markdown / PDF / Word / TXT / HTML，像 ChatGPT 一样提问，像 Perplexity 一样引用来源。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 这是什么

**DocAgent** 是一个本地优先的企业级 RAG 知识库 Agent 系统。你上传文档，它自动解析、切片、向量化并建立索引。然后你可以用自然语言提问，系统会从知识库中检索相关内容，结合 LLM 生成带引用来源的回答。

## 核心特性

- **自研 Agent Runtime** — Planner → Tool → LLM 三层解耦编排，支持多工具扩展
- **Hybrid Search 混合检索** — FAISS 向量检索 + BM25 关键词检索 + RRF 融合 + Cross-encoder 精排
- **LLM Query Rewriting** — 口语化问题自动改写为搜索引擎优化查询，提升召回命中率
- **SSE 流式输出** — 逐 token 实时渲染，Markdown 渲染 + 代码高亮 + 内联引用标注
- **多格式文档** — 支持 Markdown / PDF / Word / TXT / HTML 上传，自动解析、分块、向量化、增量索引
- **Docker 一键部署** — 本地 `python start.py` 启动，云端 Docker / Render 部署
- **数据完全本地** — 文档不上传任何第三方，只在你的机器上运行

## 架构

```
用户文档 (md/pdf/docx/txt/html)
     │
     ▼
 解析 → 分块 (RecursiveCharacterTextSplitter) + 上下文增强
     │
     ▼
 Chunk ──┬──→ BGE Embedding (512d) ──→ FAISS 向量索引
         └──→ jieba 分词 + BM25 ──────→ 关键词索引
                                              │
用户问题 ─────────────────────────────────────┘
     │
     ▼
┌────────── Agent Runtime ──────────────────────────┐
│                                                    │
│  Memory ─→ Planner ─→ Tool(search_knowledge)      │
│     │         │            │                       │
│     │         │     Retriever + Reranker           │
│     │         │     (Hybrid Search + RRF + 精排)   │
│     │         │            │                       │
│     └─────────┴──────→ PromptBuilder               │
│                           │                        │
│                      DeepSeek API → 回答           │
└────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动（会自动构建前端）
python start.py

# 浏览器打开 http://127.0.0.1:8000
```

> 首次运行需要下载 Embedding 模型（约 100MB），之后直接启动。

## 开发模式

```bash
# 后端 + 前端热更新
python start.py --dev
# 前端 → http://localhost:5173
# 后端 → http://127.0.0.1:8000
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React + TypeScript + Vite + TailwindCSS |
| 后端 | Python + FastAPI |
| Agent Runtime | 自研（Tool / Memory / Planner 三层抽象） |
| 文档解析 | LangChain TextSplitter + PyMuPDF + python-docx + BeautifulSoup |
| Embedding | BAAI/bge-small-zh-v1.5（512d，本地 CPU） |
| 向量检索 | FAISS（IndexFlatIP，余弦相似度） |
| 关键词检索 | BM25 + jieba 中文分词 |
| 精排 | BAAI/bge-reranker-v2-m3（Cross-encoder） |
| LLM | DeepSeek Chat API |
| 部署 | Docker + Render / ngrok |

## 文档

| 文件 | 内容 |
|------|------|
| [GUIDE.md](./GUIDE.md) | 安装、配置、使用手册 |
| [DESIGN.md](./DESIGN.md) | 设计决策与优化记录 |
| [PRODUCT_DESIGN.md](./PRODUCT_DESIGN.md) | 产品设计方案 |
| [DEPLOY.md](./DEPLOY.md) | 部署指南（Docker / Render） |
| [SESSION.md](./SESSION.md) | 开发进度日志 |

## 面试 demo

```bash
python start.py              # 终端 1：启动服务
.\ngrok.exe http 8000        # 终端 2：暴露公网
```

把 ngrok 显示的 `https://xxx.ngrok-free.app` 发给面试官即可。

## License

MIT
