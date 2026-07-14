# Session State — 2026-07-13

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

### 下一任务

**Phase 4.4：查询改写（Query Rewriting）**

待开发清单：
- Phase 4.4: 查询改写（用 LLM 改写用户问题，提高检索命中率）
- Phase 5: 质量闭环（RAG 评估体系、Token 管理、Prompt 版本管理）
- Phase 6: 服务化（FastAPI + 流式输出 + 可观测性）

---

## 启动命令

```bash
# macOS
./start.sh

# Windows
start.bat
# 或
.venv\Scripts\activate && python scripts\start.py
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

---

## 文档索引

| 文件 | 用途 |
|------|------|
| `README.md` | 项目首页 |
| `GUIDE.md` | 完整用户手册 + Mermaid 时序图 + 分数说明 |
| `DESIGN.md` | 10 个设计问答 + 3 个 Phase 优化对比 |
| `SESSION.md` | 本文件，进度追踪 |
