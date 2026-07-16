# Session State — 2026-07-15

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
| Phase 4.4 | Query Rewriting（LLM 查询改写，提高检索命中率） | ✅ |
| Phase 4.4 | Query Rewriting（LLM 查询改写，提高检索命中率） | ✅ |
| Phase 4.5 | Agent Runtime（Tool 抽象 + Memory + Planner + Agent 编排） | ✅ |
| Phase 4.6 | Agent 接管系统入口（server.py 改为 Agent 驱动） | ✅ |

### Query Rewriting 实现详情

| 模块 | 文件 | 核心类 |
|------|------|--------|
| QueryRewriter | `src/agent/query_rewriter.py` | `QueryRewriter` |

特性：
- LLM 驱动：使用 DeepSeekLLM 将口语化问题改写为关键词查询
- 可选注入：SearchKnowledgeTool 接受可选的 query_rewriter 参数
- 降级保护：LLM 调用失败时自动回退使用原始查询
- 可观测：改写后的查询记录在 ToolResult.metadata 中，前端可见

### Agent Runtime 实现详情

| 模块 | 文件 | 核心类 |
|------|------|--------|
| Tool 层 | `src/agent/tool.py` | `Tool(ABC)`, `ToolResult`, `ToolMetadata`, `ToolManager`, `ToolError`, `ToolCategory`, `SearchKnowledgeTool` |
| Memory 层 | `src/agent/memory.py` | `Memory(ABC)`, `Message`, `ConversationMemory`, `MessageFormatter` |
| Planner 层 | `src/agent/planner.py` | `Planner(ABC)`, `Plan`, `RuleBasedPlanner` |
| 编排层 | `src/agent/agent.py` | `Agent`, `Observation`, `AgentState` |

### 设计原则

| 原则 | 实现 |
|------|------|
| Agent 不直接调 Retriever | 通过 `SearchKnowledgeTool` 间接调用，Tool 隔离基础设施 |
| Planner 不看 Tool 实例 | `Planner.decide()` 接收 `list[ToolMetadata]`，物理隔绝 `execute()` |
| Memory 有抽象接口 | Agent 依赖 `Memory(ABC)`，可替换为 SummaryMemory / VectorMemory |
| 已有模块零修改 | Retriever / Reranker / PromptBuilder / DeepSeekLLM 接口不变 |
| 依赖注入 | 所有模块构造时注入，Agent 只依赖接口不依赖实现 |

### 本次会话 Bugfix / 优化

| 问题 | 解决 |
|------|------|
| Python 3.14 → 3.11 降级 | LangChain 兼容性，PyTorch 稳定性 |
| PyTorch 2.13 JIT 卡顿 | 降回 torch 2.5.1 + 启动预热 |
| Reranker ~3s/次太慢 | 候选 20→5，添加开关，耗时~1s |
| LLM 每次新建 TCP 连接 | 改为持久 httpx.Client 复用连接 |
| 前端 Recall 栏冗余 | 只在开启 Rerank 时显示 |
| Windows 兼容性 | 创建 start.bat，VC++ 文档 |
| 配置缺失 reranker_model_name | 补到 config.py + .env.example |
| 控制台 emoji 乱码 | 全部替换为 `[标签]` ASCII 格式 |
| 知识库文件名字符编码损坏 | 按文件内容标题重命名 + 重建索引 |
| Agent 重复搜索 5 次 | RuleBasedPlanner 增加 `_already_searched` 检查 |

### 下一任务

**Phase 5：质量闭环（RAGAS 评估 + Token 管理 + Prompt 版本管理）**

待开发清单：
- Phase 5: 质量闭环（RAG 评估体系、Token 管理、Prompt 版本管理）
- Phase 6: 服务化（FastAPI + 流式输出 + 可观测性）
- Phase 7: LLM Planner 升级（替换 RuleBasedPlanner）
- Phase 8: 多 Tool 扩展（Calculator / WebSearch / SQL / GitHub）

---

## 启动命令

```bash
# 生产模式（一键启动，前端+API 统一在 8000 端口）
python start.py

# 开发模式（前端热更新在 5173，API 在 8000）
python start.py --dev

# Windows
start.bat
start.bat --dev

# macOS / Linux
./start.sh
./start.sh --dev
```

---

## 环境要点

| 项 | 值 |
|---|---|
| Python | 3.11.15 (python@3.11) |
| PyTorch | 2.5.1 (固定, 不用 2.13) |
| DeepSeek API Key | 已配置在 .env |
| Embedding | BAAI/bge-small-zh-v1.5 (~100MB) |
| Reranker | BAAI/bge-reranker-v2-m3 (~2.2GB, 可开关) |
| 检索耗时 | Hybrid ~15ms, Rerank ~1s, LLM ~2s |
| Agent 架构 | Tool(ABC) + Memory(ABC) + Planner(ABC) + Agent 编排 |

---

## 文档索引

| 文件 | 用途 |
|------|------|
| `README.md` | 项目首页 |
| `GUIDE.md` | 完整用户手册 + Mermaid 时序图 + 分数说明 |
| `DESIGN.md` | 10 个设计问答 + 3 个 Phase 优化对比 + Agent 设计决策 |
| `SESSION.md` | 本文件，进度追踪 |
