# Travel Agent Backend

FastAPI 后端服务，负责用户认证、行程生成、行程列表和行程详情查询。行程生成通过智能体流程完成，并使用 SSE 向前端推送规划状态。

## 本地开发环境

需要先准备：

- Python `3.11+`
- Poetry
- PostgreSQL
- 可用的 DeepSeek、高德地图和 MCP 配置

## 技术栈

- FastAPI
- SQLAlchemy Async
- Alembic
- PostgreSQL
- LangGraph
- LangChain
- Pydantic Settings
- Loguru

## 本地配置

安装依赖：

```bash
poetry install  --only main --no-root
```

创建本地环境变量文件：

```bash
cp .env.example .env.dev
```

本地开发启动时使用：

```bash
ENV=dev
```

此时配置会从 `backend/.env.dev` 读取。需要按本机情况填写：

- `DEEPSEEK_API_KEY`
- `AMAP_API_KEY`
- `AMAP_MCP_BASE_URL`
- `XHS_MCP_URL`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `AUTH_SECRET`

本地 PostgreSQL 需要提前创建对应数据库和用户。示例：

```sql
CREATE USER devuser WITH PASSWORD '123456';
CREATE DATABASE travel_agent OWNER devuser;
```

## 数据库迁移

执行迁移：

```bash
ENV=dev poetry run alembic upgrade head
```

新增迁移：

```bash
ENV=dev poetry run alembic revision --autogenerate -m "describe change"
```

## 启动服务

```bash
ENV=dev poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后接口前缀：

```text
http://127.0.0.1:8000/api/v1
```

## 目录结构

```text
app/
  agents/       智能体编排和各 Agent 实现
  api/          FastAPI 路由
  core/         配置、数据库、异常处理、安全和日志
  models/       SQLAlchemy 模型
  schemas/      请求和响应模型
  services/     业务服务
alembic/        数据库迁移
tests/          测试代码
```

## 主要接口

| 模块 | 接口 |
| --- | --- |
| 认证 | `POST /api/v1/auth/register` |
| 认证 | `POST /api/v1/auth/login` |
| 认证 | `GET /api/v1/auth/me` |
| 行程规划 | `POST /api/v1/travel/plan` |
| 行程 | `GET /api/v1/trips` |
| 行程 | `GET /api/v1/trips/{trip_id}` |

完整契约以根目录 [API.md](../API.md) 为准。

## 本地检查

语法检查：

```bash
python3 -m compileall app
```
