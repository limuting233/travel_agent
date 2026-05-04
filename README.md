# Travel Agent

Travel Agent 是一个本地可运行的旅行规划项目，包含移动端 H5 前端和 FastAPI 后端。用户登录后填写目的地、天数、日期和偏好，后端通过智能体生成行程，前端展示每日安排、通勤信息和行程列表。

## 项目结构

```text
travel_agent/
  API.md          接口契约文档
  backend/        FastAPI 后端服务
  frontend/       Vue H5 前端应用
```

## 本地开发环境

需要先准备：

- Node.js `20.19+` 或 `22.12+`
- Python `3.11+`
- Poetry
- PostgreSQL

本地联调默认端口：

| 服务     | 地址                    |
| -------- | ----------------------- |
| 前端     | `http://127.0.0.1:5173` |
| 后端     | `http://127.0.0.1:8000` |
| API 前缀 | `/api/v1`               |

## 后端启动

进入后端目录：

```bash
cd backend
```

安装依赖：

```bash
poetry install  --only main --no-root
```

配置本地环境变量：

```bash
cp .env.example .env.dev
```

按本机情况修改 `backend/.env.dev`，重点是数据库、模型服务、高德和 MCP 配置。本地开发时 `ENV=dev` 会读取 `backend/.env.dev`。

执行数据库迁移：

```bash
ENV=dev poetry run alembic upgrade head
```

启动后端：

```bash
ENV=dev poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 前端启动

进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

确认 `frontend/.env.development` 指向本地后端：

```env
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_TARGET=http://127.0.0.1:8000
```

启动前端：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

## 本地检查

前端类型检查：

```bash
cd frontend
npx vue-tsc --noEmit -p tsconfig.app.json
npx vue-tsc --noEmit -p tsconfig.node.json
```

后端语法快速检查：

```bash
cd backend
python3 -m compileall app
```

## 文档

- 接口契约：[API.md](API.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 后端说明：[backend/README.md](backend/README.md)
