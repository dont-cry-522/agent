# Python 异步编程指南

## asyncio 基础

Python 的 asyncio 是官方提供的异步 I/O 框架，基于事件循环（Event Loop）实现。

### 核心概念

1. **协程（Coroutine）**：用 `async def` 定义的函数，可以在执行过程中挂起和恢复
2. **任务（Task）**：调度协程执行，由事件循环管理
3. **Future**：表示一个尚未完成的计算结果，相当于 JavaScript 的 Promise

### 基本用法

```python
import asyncio

async def fetch_data(url: str) -> str:
    print(f"开始请求: {url}")
    await asyncio.sleep(1)  # 模拟网络 I/O
    return f"来自 {url} 的数据"

async def main():
    # gather 并发执行多个协程
    results = await asyncio.gather(
        fetch_data("https://api.example.com/users"),
        fetch_data("https://api.example.com/posts"),
    )
    for r in results:
        print(r)

asyncio.run(main())
```

## async/await 语法规则

- `async def` 声明一个协程函数，调用它返回一个协程对象，不会立即执行
- `await` 只能在 `async def` 内部使用
- `await` 挂起当前协程，将控制权交还给事件循环，等待被等待的对象完成

## 并发模式对比

| 模式 | 适用场景 | 并发方式 | CPU 利用率 |
|------|---------|----------|-----------|
| 多线程 | I/O 密集 | 系统线程切换 | 受 GIL 限制 |
| 多进程 | CPU 密集 | 系统进程隔离 | 充分利用多核 |
| 异步 | 高并发 I/O | 单线程协程切换 | 不涉及 CPU 密集 |
