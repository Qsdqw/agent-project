FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（chromadb 需要 C++ 运行时）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 复制项目
COPY . .

# HuggingFace 模型缓存目录（设为卷持久化，避免每次重启重下载 Cross-Encoder）
ENV HF_HOME=/app/.cache/huggingface

# ChromaDB 不走 SQLite 多线程写入冲突，使用环境量覆盖
ENV CHROMA_TELEMETRY_IMPL=none

EXPOSE 8000 8501

# 默认启动 FastAPI；docker-compose 会覆盖 command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
