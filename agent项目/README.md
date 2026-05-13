# 智扫通 — 智能客服 Agent

基于 **FastAPI + LangChain + RAG + ReAct** 的智能客服系统，面向扫地机器人售后场景，支持多轮对话、知识库检索、天气感知和 Docker 一键部署。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn |
| 前端 | Streamlit |
| AI 引擎 | LangChain + ReAct Agent |
| 对话模型 | 阿里百炼 Qwen（DashScope API） |
| 向量嵌入 | text-embedding-v4（DashScope API） |
| 向量数据库 | ChromaDB |
| 关系数据库 | MySQL 8.0 |
| 缓存 | Redis 7 |
| 容器化 | Docker + Docker Compose |

## 项目结构

```
agent项目/
├── agent/                   # Agent 核心
│   ├── react_agent.py       # ReAct Agent 定义（工具 + 中间件）
│   └── tools/
│       ├── agent_tools.py   # 工具函数（RAG检索、天气、定位等）
│       └── middleware.py    # 中间件（日志、提示词切换）
├── api/                     # FastAPI 后端
│   ├── main.py              # 应用入口 + 聊天/会话 API
│   ├── router.py            # 注册/登录/登出 端点
│   └── deps.py              # JWT 签发、黑名单、依赖注入
├── storage/                 # 数据层
│   ├── mysql.py             # MySQL 连接池 + 建表
│   ├── redis_client.py      # Redis 连接单例
│   ├── vector.py            # ChromaDB 向量存储 + 知识库加载
│   ├── session.py           # 会话/消息 CRUD
│   └── auth.py              # 用户注册/查询/清理
├── rag/
│   └── rag_service.py       # 两阶段检索（向量召回 + Cross-Encoder 精排）
├── model/
│   └── factory.py           # 模型工厂（ChatTongyi + DashScopeEmbeddings）
├── frontend/
│   └── app.py               # Streamlit 前端（登录/注册/聊天）
├── config/                  # YAML 配置文件
│   ├── agent.yml            # 外部服务 + JWT + 数据库配置（${ENV} 占位符）
│   ├── rag.yml              # 模型名称配置
│   ├── chroma.yml           # 向量库参数（分块大小、检索数量）
│   └── prompts.yml          # 提示词文件路径
├── data/                    # 知识库文件（PDF/TXT）
├── prompts/                 # 提示词模板
├── docker-compose.yml       # 一键部署编排
├── Dockerfile               # 应用镜像
└── .env.example             # 环境变量模板
```

## 功能

- **RAG 知识库检索** — 向量召回 top-10 + Cross-Encoder 精排 top-3，支持 PDF/TXT
- **ReAct 推理** — Agent 自主调用工具链（检索 → 天气 → 定位 → 外部数据）
- **用户系统** — 注册 / 登录 / 登出，JWT 认证 + 黑名单吊销
- **多会话管理** — 会话隔离，历史消息持久化，Agent 池化复用
- **天气感知** — 接入高德天气 API，根据用户位置推荐保养方案
- **Redis 缓存** — RAG 结果缓存 24 小时，减少重复检索开销

## 快速开始

### 前置要求

- [Docker Desktop](https://docs.docker.com/get-docker/)（已安装可跳过）
- 阿里百炼 API Key（[免费申请](https://bailian.console.aliyun.com/)，新用户有免费额度）

### 1. 配置

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env`，**只改一行**：

```ini
DASHSCOPE_API_KEY=sk-你的百炼API密钥
```

其余配置用默认值即可，无需修改。

### 2. 一键启动

```bash
docker-compose up -d --build
```

首次启动约 3-5 分钟，自动完成：拉取镜像 → 安装依赖 → 下载 Cross-Encoder 模型 → 构建向量索引。之后再启动就是秒级。

### 3. 打开浏览器

- **前端界面**：http://localhost:8501
- 健康检查：http://localhost:8000/api/health

注册账号后即可开始对话。

### 常用命令

```bash
docker-compose up -d --build   # 重新构建并启动
docker-compose down            # 停止所有服务
docker-compose logs -f backend # 查看后端日志
docker-compose ps              # 查看容器状态
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出（JWT 加入黑名单） |
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 新建会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET | `/api/sessions/{id}/messages` | 获取消息历史 |
| POST | `/api/chat/stream` | 流式聊天（SSE） |
| GET | `/api/health` | 健康检查 |

## 本地开发（不使用 Docker）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 MySQL 和 Redis（可本地安装或用 Docker）
docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=123456 mysql:8.0
docker run -d --name redis -p 6379:6379 redis:7-alpine redis-server --requirepass 123456

# 3. 启动后端
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 4. 启动前端（新终端）
streamlit run frontend/app.py

# 5. 打开 http://localhost:8501
```

## 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Streamlit  │────▶│   FastAPI    │────▶│    MySQL     │
│   :8501      │     │   :8000      │     │    :3306     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                     ┌──────┼──────┐
                     │      │      │
                     ▼      ▼      ▼
               ┌────────┐ ┌────┐ ┌──────────┐
               │ Chrona │ │Redis│ │DashScope │
               │ 向量库 │ │缓存 │ │  API     │
               └────────┘ └────┘ └──────────┘
```
