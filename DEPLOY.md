# 部署指南

## 方案 A：本地运行（开发 / 个人使用）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 构建索引（首次）
python scripts/build_index.py

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 4. 启动
python start.py          # 生产模式
python start.py --dev    # 开发模式（热更新）
```

浏览器打开 http://127.0.0.1:8000

---

## 方案 B：Render 云端部署（免费，别人也能用）

### 1. 推送到 GitHub

```bash
git init
git add .
git commit -m "yuque-agent v2"
git branch -M main
git remote add origin https://github.com/你的用户名/yuque-agent.git
git push -u origin main
```

### 2. 在 Render 创建服务

1. 打开 [render.com](https://render.com) → Sign Up（GitHub 登录最快）
2. 面板 → New → **Web Service**
3. 选择你的 GitHub 仓库
4. 配置：

| 配置项 | 值 |
|--------|-----|
| Name | `yuque-agent` |
| Runtime | Docker |
| Instance | Free |

### 3. 设置环境变量

Environment Variables：

| Key | Value |
|-----|-------|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key |
| `DISABLE_RERANKER` | `1` |

### 4. 部署

点击 **Deploy Web Service**。等待 5-10 分钟，你会得到一个 `https://yuque-agent.onrender.com` 地址。

### 5. 使用

浏览器打开上面的地址，上传 Markdown 文件，开始对话。

---

## 方案 C：Docker 自部署

```bash
# 构建
docker build -t yuque-agent .

# 运行
docker run -p 8000:8000 \
  -e DEEPSEEK_API_KEY=sk-xxx \
  -e DISABLE_RERANKER=1 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/uploads:/app/uploads \
  yuque-agent
```

---

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥 |
| `DISABLE_RERANKER` | 否 | 设为 `1` 禁用 Reranker（节省内存） |
| `DEEPSEEK_BASE_URL` | 否 | 自定义 API 地址（默认 `https://api.deepseek.com`） |

---

## 注意事项

- **Render 免费实例** 15 分钟无人访问会休眠，下次需等 30-60 秒唤醒。可注册 [UptimeRobot](https://uptimerobot.com) 每 5 分钟 ping 一次防止休眠。
- **API 费用** 走你的 DeepSeek Key，和部署方式无关。一次对话约 0.001-0.005 元。
- **Reranker** 需要 2GB+ 内存，免费实例建议关闭。本地开发不受影响。
