# yuque-agent

从零自建的本地 RAG 知识库系统，让个人 Markdown 笔记变成可对话的知识库。

```bash
./start.sh
```

一键启动，自动打开浏览器。

## 架构

```
knowledge/*.md
     │
     ▼
 分块 (RecursiveCharacterTextSplitter) + 上下文增强 (标题/前后文/路径)
     │
     ▼
 Chunk
     │
     ├──→ BGE Embedding (512维) ──→ FAISS 向量库
     └──→ jieba 分词 + BM25 ──────→ 关键词索引
                                          │
用户问题 ─────────────────────────────────┘
     │
     ▼
 Hybrid Search (向量 + BM25 → RRF 融合)
     │
     ▼
 [可选] BGE Reranker (Cross-encoder 精排)
     │
     ▼
 PromptBuilder (上下文拼接)
     │
     ▼
 DeepSeek API → 回答
```

## 文档

| 文档 | 内容 |
|------|------|
| [GUIDE.md](./GUIDE.md) | 安装、配置、使用、技术栈、分数说明 |
| [DESIGN.md](./DESIGN.md) | 设计决策（为什么这么设计）、优化前后对比 |
| [SESSION.md](./SESSION.md) | 开发进度、下一任务 |

## 技术栈

| 层 | 技术 | 位置 |
|---|---|---|
| 分块 | LangChain RecursiveCharacterTextSplitter | 本地 |
| Embedding | BAAI/bge-small-zh-v1.5 (512维) | 本地 |
| 关键词检索 | BM25 + jieba 分词 | 本地 |
| 向量检索 | FAISS (IndexFlatIP) | 本地 |
| 精排 | BAAI/bge-reranker-v2-m3 (Cross-encoder) | 本地 |
| 生成 | DeepSeek Chat API | 联网 |

## 快速开始

```bash
# 安装
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置 .env 中的 DEEPSEEK_API_KEY

# 构建索引（首次）
python scripts/import_markdown.py
python scripts/build_chunks.py
python scripts/build_index.py

# 启动
./start.sh
```
