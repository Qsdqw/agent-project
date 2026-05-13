#!/bin/bash
set -e

echo "[Entry] 检查 Cross-Encoder 模型缓存..."
python -c "
from sentence_transformers import CrossEncoder
CrossEncoder('BAAI/bge-reranker-base')
print('[Entry] Cross-Encoder 模型就绪')
" 2>/dev/null || echo "[Entry] Cross-Encoder 下载失败，将在首次 RAG 查询时重试"

echo "[Entry] 启动 FastAPI..."
exec "$@"
