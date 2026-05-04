# Travel Agent H5

移动端 H5 旅行规划应用。用户登录后填写目的地、天数、日期和旅行偏好，前端通过流式接口生成行程，并展示每日路线、通勤方式和外部导航入口。

## 本地开发环境

需要先准备：

- Node.js `20.19+` 或 `22.12+`
- npm
- 已启动的后端服务：`http://127.0.0.1:8000`

## 技术栈

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Tailwind CSS
- shadcn-vue 风格组件
- Motion for Vue
- Axios
- Lucide Icons

## 本地启动

安装依赖：

```bash
npm install
```

确认开发环境配置：

```env
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_TARGET=http://127.0.0.1:8000
```

启动开发服务：

```bash
npm run dev -- --port 5173
```

手机访问同一局域网下的开发服务：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

启动后使用电脑的局域网 IP 访问，例如：

```text
http://192.168.x.x:5173
```

## 接口联调

开发环境请求 `/api/v1`，由 Vite 代理到 `VITE_BACKEND_TARGET`。接口契约以根目录 [API.md](../API.md) 为准。

## 页面流程

主要页面：

| 路由 | 页面 |
| --- | --- |
| `/` | 首页 |
| `/profile` | 我的 |
| `/login` | 登录 |
| `/register` | 注册 |
| `/trip/create` | 创建行程 |
| `/trip/planning` | 规划中 |
| `/trip/:tripId` | 行程详情 |
| `/trips` | 我的行程 |

核心流程：

```text
首页
  -> 创建行程
  -> 规划中
  -> 行程详情

我的
  -> 我的行程
  -> 行程详情
```

登录约束：

- 未登录不能使用创建行程、规划中、行程详情、我的行程。
- 访问受保护页面会跳转到登录页。
- 登录成功后会回到原本要访问的页面。

## 接口文档

接口契约以根目录 [API.md](../API.md) 为准。

前端接口封装：

```text
src/api/auth.ts
src/api/travel.ts
src/api/trips.ts
src/utils/request.ts
```

## 目录结构

```text
src/
  api/              接口封装
  components/ui/    shadcn-vue 风格组件
  router/           路由和登录守卫
  stores/           Pinia 状态
  utils/            request、导航等工具
  views/            页面
```

## 常用命令

类型检查：

```bash
npx vue-tsc --noEmit -p tsconfig.app.json --pretty false
npx vue-tsc --noEmit -p tsconfig.node.json --pretty false
```

本地构建检查：

```bash
npm run build
```

## 开发说明

- 移动端页面最大宽度限制为 `430px`。
- Toast 使用 `vue-sonner`。
- 图标使用 `lucide-vue-next`。
- 登录 token 存在 `localStorage`。
- 待生成的行程参数存在 `sessionStorage`。
- 行程规划接口使用 SSE 流式响应，前端处理 `start`、`agent_step`、`tool_call`、`message`、`done`、`error` 事件。
