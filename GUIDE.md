# GUIDE.md — DocAgent 用户手册

## 环境配置

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxx
HF_ENDPOINT=https://hf-mirror.com    # 国内自动镜像
DISABLE_RERANKER=1                    # 可选：关闭精排加速启动
```

### 启用 Reranker

取消 `.env` 中 `DISABLE_RERANKER` 注释或删除该行。Reranker 首次需下载 2.2GB 模型。

---

## 文档上传

### 支持格式

| 格式 | 解析器 | 说明 |
|------|--------|------|
| `.md` | 直接读取 | Markdown 原样保留 |
| `.pdf` | PyMuPDF | 按页提取文本，扫描件无效 |
| `.docx` | python-docx | 按段落提取，自动识别标题 |
| `.txt` | 多编码检测 | UTF-8 / GBK / GB2312 自动适配 |
| `.html` | BeautifulSoup | 去除 script/style 后提取正文 |

### 上传方式

**Web 页面**：侧栏 → 文档标签 → 拖拽文件或点击选择

**CLI**（仅 Markdown）：
```bash
# 将 .md 文件放入 knowledge/ 目录
# 然后：
python scripts/import_markdown.py
python scripts/build_chunks.py
python scripts/build_index.py
```

### 上传流程

```
文件 → 格式识别 → Parser 提取纯文本 → Chunk 切片(500字) → BGE Embedding(512d)
                                                                    ↓
                                                            FAISS + BM25 索引
```

上传完成后立即可在对话中检索，无需重启。

---

## 建立索引

### 从 knowledge/ 目录构建

```bash
python scripts/import_markdown.py    # 扫描 knowledge/ → documents.json
python scripts/build_chunks.py       # 文档切片 → chunks.json
python scripts/build_index.py        # 向量化 + FAISS 索引
```

### 从 uploads/ 目录重建

页面点击「重建全部索引」或：

```
POST /api/index/rebuild
```

### 增量更新

上传同名文档时自动 SHA256 比对：
- **内容相同** → 跳过索引
- **内容不同** → 先移除旧的 Chunk，再追加新的

删除文档时只移除该文档的向量，其他文档不受影响。

---

## 对话管理

### 新建对话

侧栏点击「新对话」或 `POST /api/conversations`

首条消息发送后自动用内容前 30 字命名。

### 切换对话

点击侧栏对话列表中的任意对话项，ChatArea 自动加载历史消息。

### 删除对话

Hover 对话项 → 点击 × 按钮 → 确认。删除后对话及所有消息从数据库移除。

### 对话持久化

所有对话和历史消息存储在 `data/docagent.db` (SQLite)，刷新页面不丢失。

---

## 多轮聊天

在同一对话中连续发送消息，系统自动维护上下文：

```
User: MCP 是什么
AI:   MCP 全称 Model Context Protocol... [1][2]
User: 它和 REST 有什么区别         ← 系统从历史中理解"它"指代 MCP
AI:   MCP 与 REST 的核心区别在于... [2]
```

每条对话窗口保留最近 20 条消息作为上下文。

---

## 知识库管理

### 查看文档

侧栏 → 文档标签 → 文档表格

显示：文件名、格式、大小、Chunk 数、上传时间

### 删除文档

文档表格右侧「删除」按钮 → 同时移除上传文件和索引中的向量

### 系统统计

文档页顶部显示：文档总数、Chunk 总数、总大小

也可通过 `GET /api/stats` 获取。

---

## 检索说明

### 四层检索流程

```
用户问题
  → QueryRewriter (LLM 改写查询)
  → BM25 关键词检索 + FAISS 向量检索 (各取 Top 20)
  → RRF 融合排序
  → BGE Reranker (Cross-encoder 精排 Top 5)
  → PromptBuilder → LLM
```

### 检索分数含义

| 分数 | 来源 | 范围 |
|------|------|------|
| Vec | BGE Embedding 余弦相似度 | 0~1 |
| BM25 | jieba 分词 + BM25 关键词匹配 | 0~+ |
| RRF | 融合两路排名 | 0~0.033 |
| Rerank | Cross-encoder 精细打分 | -10~10 |

### 耗时分布

- 检索（Embedding + BM25 + FAISS + RRF）：~15ms
- Reranker（Cross-encoder 精排 5 对）：~800ms
- LLM（DeepSeek API）：~2-4s

---

## 模型说明

| 模型 | 大小 | 用途 | 首次下载 |
|------|------|------|----------|
| BAAI/bge-small-zh-v1.5 | ~100MB | 文本向量化 | 启动时自动 |
| BAAI/bge-reranker-v2-m3 | ~2.2GB | 精排重排序 | 可选，`DISABLE_RERANKER=1` 跳过 |

模型下载一次后缓存到 HuggingFace 本地目录，后续启动直接从缓存加载。

---

## 命令行工具

```bash
# 语义检索（无需 API Key）
python scripts/search.py "Python 异步编程" --top 5

# CLI 交互式对话（需要 API Key）
python scripts/chat.py
```

---

## 部署

详见 [DEPLOY.md](./DEPLOY.md)
