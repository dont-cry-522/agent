"""
yuque-agent 一键启动
===================

用法：
    python start.py          生产模式：构建前端 + 启动服务
    python start.py --dev    开发模式：前后端分离，热更新

生产模式：http://127.0.0.1:8000（一个端口，前端+API 统一）
开发模式：http://localhost:5173（Vite 热更新，API 代理到 8000）
"""

from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"


def check_index():
    if not (ROOT / "output" / "index.faiss").exists():
        print("[ERR] 索引文件不存在")
        print("     请先运行: python scripts/build_index.py")
        sys.exit(1)


def build_frontend():
    print("[build] 构建前端...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(WEB_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[ERR] 前端构建失败:")
        print(result.stderr)
        sys.exit(1)
    print("   [OK] 构建完成")


def start_dev():
    print("[dev] 启动开发模式...\n")
    check_index()

    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1"],
        cwd=str(WEB_DIR),
    )

    print("   后端: http://127.0.0.1:8000")
    print("   前端: http://localhost:5173")
    print("   Ctrl+C 停止\n")

    webbrowser.open("http://localhost:5173")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n[bye] 服务已停止")
        frontend.terminate()
        backend.terminate()


def start_prod():
    print("[start] yuque-agent 启动中...\n")
    check_index()

    if not (WEB_DIR / "dist" / "index.html").exists():
        build_frontend()

    print("[boot] 启动服务...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
    )

    time.sleep(3)

    url = "http://127.0.0.1:8000"
    print(f"\n[OK] 服务已启动: {url}")
    print("   Ctrl+C 停止\n")

    webbrowser.open(url)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[bye] 服务已停止")
        proc.terminate()


def main():
    if "--dev" in sys.argv:
        start_dev()
    else:
        start_prod()


if __name__ == "__main__":
    main()
