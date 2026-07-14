# FastAPI 框架

FastAPI 是一个现代、高性能的 Python Web 框架。

## 核心特性

- 基于 Starlette 和 Pydantic，性能媲美 NodeJS 和 Go
- 自动生成 Swagger UI 和 ReDoc 文档
- 原生异步支持，使用 async/await

## 快速入门

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## 请求验证

使用 Pydantic 模型自动校验请求：

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = False

@app.post("/items")
async def create_item(item: Item):
    return item
```
