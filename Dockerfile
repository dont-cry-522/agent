FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

COPY . .

RUN mkdir -p output uploads

ENV DEEPSEEK_API_KEY=sk-placeholder
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DISABLE_RERANKER=1

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "--timeout", "300", "--bind", "0.0.0.0:8000", "api.main:app"]
