"""
一键启动 — 初始化所有组件并打开前端页面

用法：
    python scripts/start.py

效果：
    1. 加载 FAISS 索引 + Embedding 模型
    2. 启动 HTTP 服务 (http://127.0.0.1:8000)
    3. 自动打开浏览器
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.server import create_server


def main():
    host = "127.0.0.1"
    port = 8000

    print("[start] yuque-agent 启动中...\n")

    server = create_server(host=host, port=port)

    url = f"http://{host}:{port}"
    print(f"[OK] 服务已启动: {url}")
    print("   Ctrl+C 停止服务\n")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bye] 服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
