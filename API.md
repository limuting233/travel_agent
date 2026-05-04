# Travel Agent 后端接口文档

## 1. 基础约定

本文档定义 Travel Agent C 端旅行规划产品的后端接口契约，供前端、后端和测试对齐请求、响应、错误码与鉴权规则。

基础路径：

```http
/api/v1
```

默认响应格式：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": T | null
}
```

错误响应格式：

```json
{
    "code": 10400,
    "message": "error",
    "error_message": "错误原因",
    "data": null
}
```

鉴权方式：

```http
Authorization: Bearer <access_token>
```

时间格式：

- 日期：`YYYY-MM-DD`
- 时间窗口：`HH:mm-HH:mm`
- 时间戳：秒级 Unix timestamp

## 2. 业务异常设计

### 2.1 设计原则

- HTTP 状态码只表达请求在协议层和资源层的结果，前端可以据此决定是否跳登录、展示无权限页、展示 404 页或重试。
- 业务 code 表达具体失败原因，前端可以据此做精确文案、埋点和分支处理。
- 普通 JSON 接口成功时 HTTP 状态码为 `200`，响应体 `code` 固定为 `200`。
- 普通 JSON 接口失败时 HTTP 状态码必须是对应的 `4xx` 或 `5xx`，不能用 HTTP `200` 包业务失败。
- SSE 接口在连接建立前发生认证或参数错误，按普通 JSON 错误返回；连接建立后发生规划失败，HTTP 连接保持 `200`，通过 `event: error` 返回业务错误。
- `error_message` 是给用户或前端展示的稳定文案，不放堆栈、SQL、第三方原始错误、token 等敏感信息。

### 2.2 HTTP 状态码

| HTTP 状态码 | 使用场景                            |
| ----------- | ----------------------------------- |
| 200         | 请求成功；或 SSE 连接已成功建立     |
| 400         | 请求体、查询参数或路径参数不合法    |
| 401         | 未登录、token 缺失、token 无效/过期 |
| 403         | 已登录，但无权访问该资源            |
| 404         | 资源不存在，或已被软删除            |
| 409         | 资源冲突，例如用户名已存在          |
| 500         | 服务端未预期错误                    |
| 502         | 依赖的外部模型、地图、MCP 工具失败  |

说明：不单独使用 HTTP `422`。FastAPI/Pydantic 校验失败统一映射为 HTTP `400` + 业务 code `10400`，避免前端同时处理 `400` 和 `422` 两套参数错误。

### 2.3 业务 code 分段

| code 范围 | 模块             | 说明                           |
| --------- | ---------------- | ------------------------------ |
| 200       | 成功             | 所有普通 JSON 成功响应         |
| 10xxx     | 全局请求与系统   | 参数、路由、内部错误、上游错误 |
| 20xxx     | 用户、认证与权限 | 注册、登录、token、用户权限    |
| 30xxx     | 行程             | 行程、版本、导出、行程状态     |
| 40xxx     | 旅行规划流程     | 智能体输出、质量检查、工具调用 |

### 2.4 全局错误码

| HTTP 状态码 | 业务 code | error_message    | 说明                         |
| ----------- | --------- | ---------------- | ---------------------------- |
| 400         | 10400     | 请求参数不合法   | 参数缺失、类型错误、格式错误 |
| 404         | 10404     | 接口不存在       | 路由不存在                   |
| 500         | 10500     | 服务内部错误     | 未预期异常                   |
| 502         | 10502     | 外部服务调用失败 | 模型、地图、MCP 等依赖失败   |

### 2.5 用户、认证与权限错误码

| HTTP 状态码 | 业务 code | error_message          | 说明                         |
| ----------- | --------- | ---------------------- | ---------------------------- |
| 400         | 20400     | 用户名和密码不能为空   | 登录或注册字段为空           |
| 400         | 20401     | 用户名或密码格式不合法 | 长度、字符集或密码强度不符合 |
| 401         | 20402     | 用户名或密码错误       | 登录失败，不区分用户是否存在 |
| 401         | 20403     | 未登录或 token 无效    | token 缺失、无效或过期       |
| 403         | 20404     | 无权访问该资源         | 已登录但无访问权限           |
| 409         | 20409     | 用户名已存在           | 注册用户名冲突               |

### 2.6 行程错误码

| HTTP 状态码 | 业务 code | error_message      | 说明                        |
| ----------- | --------- | ------------------ | --------------------------- |
| 404         | 30404     | 行程不存在         | 行程不存在或已删除          |
| 403         | 30403     | 无权访问该行程     | 访问他人的行程              |
| 404         | 30414     | 行程版本不存在     | 指定版本号不存在            |
| 409         | 30409     | 行程状态不允许操作 | 例如规划中行程不允许导出    |
| 400         | 30400     | 行程请求参数不合法 | version_no、format 等不合法 |

### 2.7 旅行规划错误码

| HTTP 状态码 | 业务 code | SSE error_code       | error_message        | 说明                         |
| ----------- | --------- | -------------------- | -------------------- | ---------------------------- |
| 400         | 40400     | VALIDATION_ERROR     | 旅行规划参数不合法   | location、days、日期等不合法 |
| 502         | 40502     | TOOL_CALL_FAILED     | 外部工具调用失败     | 高德、MCP、模型工具调用失败  |
| 500         | 40510     | AGENT_OUTPUT_INVALID | 智能体输出结构不合法 | LLM 输出无法解析为目标结构   |
| 500         | 40511     | PLAN_QUALITY_FAILED  | 行程质量检查失败     | 规划结果未通过质量检查       |
| 500         | 40500     | INTERNAL_ERROR       | 旅行规划失败         | 规划流程未预期失败           |

## 3. 认证 API

### 3.1 注册

```http
POST /api/v1/auth/register
```

请求体：

```json
{
    "username": "user001",
    "password": "password123"
}
```

字段说明：

| 字段     | 类型   | 必填 | 说明                                             |
| -------- | ------ | ---- | ------------------------------------------------ |
| username | string | 是   | 用户名，长度 5-20 位，只能包含字母、数字和下划线 |
| password | string | 是   | 密码，长度 8-32 位，必须包含字母、数字和特殊字符 |

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": null
}
```

错误：

| HTTP 状态码 | 业务 code | error_message          |
| ----------- | --------- | ---------------------- |
| 400         | 20400     | 用户名和密码不能为空   |
| 400         | 20401     | 用户名或密码格式不合法 |
| 409         | 20409     | 用户名已存在           |

### 3.2 登录

```http
POST /api/v1/auth/login
```

请求体：

```json
{
    "username": "user001",
    "password": "password123"
}
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "access_token": "eyJhbGciOi...",
        "token_type": "bearer",
        "expires_at": 1770000000
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message          |
| ----------- | --------- | ---------------------- |
| 400         | 20400     | 用户名和密码不能为空   |
| 400         | 20401     | 用户名或密码格式不合法 |
| 401         | 20402     | 用户名或密码错误       |

### 3.3 当前用户

```http
GET /api/v1/auth/me
```

请求头：

```http
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "id": "usr_01HZX...",
        "username": "user001",
        "nickname": "旅行者"
        // 其他用户信息字段
        // ...
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 401         | 20403     | 未登录或 token 无效 |

## 4. 旅行规划 API

### 4.1 创建旅行规划

创建旅行规划使用 SSE 返回过程事件和最终结果。

```http
POST /api/v1/travel/plan
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer <access_token>
```

请求体：

```json
{
    "location": "上海市",
    "days": 3,
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "preferences": "美食,历史,小众探索"
}
```

字段说明：

| 字段        | 类型        | 必填 | 说明                                                       |
| ----------- | ----------- | ---- | ---------------------------------------------------------- |
| location    | string      | 是   | 目的地，建议城市或城市+区县，例如 "上海市"、"北京市海淀区" |
| days        | integer     | 是   | 旅行天数，必须大于等于 1                                   |
| start_date  | string/null | 否   | 开始日期，格式 "YYYY-MM-DD"                                |
| end_date    | string/null | 否   | 结束日期，格式 "YYYY-MM-DD"                                |
| preferences | string/null | 否   | 用户偏好，逗号分隔，例如 "美食,历史,小众探索"              |

校验规则：

- `location` 不能为空。
- `days >= 1`。
- `start_date` 和 `end_date` 必须同时提供或同时为空。
- 同时提供日期时，`days` 必须等于日期区间天数。
- `start_date` 不能早于当前日期。

#### 4.1.1 SSE 事件格式

SSE 原始格式：

```text
event: start
data: {"thread_id":"thread_xxx","trip_id":"trip_xxx","start_at":1770000000}

event: agent_step
data: {"agent":"resource_agent","status":"running","message":"正在筛选景点、美食和住宿"}
```

所有事件的 `data` 都是 JSON 字符串。

#### 4.1.2 start

规划开始。

```json
{
    "thread_id": "thread_xxx",
    "trip_id": "trip_xxx",
    "start_at": 1770000000
}
```

#### 4.1.3 agent_step

智能体阶段变化。

```json
{
    "agent": "resource_agent",
    "status": "running",
    "message": "正在筛选景点、美食和住宿"
}
```

字段说明：

| 字段    | 类型   | 说明                                                                       |
| ------- | ------ | -------------------------------------------------------------------------- |
| agent   | string | `manager_agent` / `environment_agent` / `resource_agent` / `planner_agent` |
| status  | string | `pending` / `running` / `completed` / `failed`                             |
| message | string | 给前端展示的阶段文案，例如 "正在筛选景点、美食和住宿"                      |

#### 4.1.4 tool_call

外部工具调用事件。

```json
{
    "agent": "planner_agent",
    "tool_name": "maps_distance",
    "status": "completed",
    "message": "已计算当天 POI 之间的距离",
    "latency_ms": 1260
}
```

#### 4.1.5 message

最终内容流。

```json
{
    "content": "{"
}
```

说明：当前实现可以继续逐字符输出；后续建议改为按 JSON chunk 或自然段输出。

#### 4.1.6 done

规划完成。

```json
{
    "trip_id": "trip_xxx",
    "thread_id": "thread_xxx",
    "version_no": 1,
    "end_at": 1770000060
}
```

#### 4.1.8 error

规划失败。SSE 已建立后失败时使用该事件；此时 HTTP 状态码仍为 `200`，具体失败原因看 `code` 和 `error_code`。

```json
{
    "trip_id": "trip_xxx",
    "thread_id": "thread_xxx",
    "code": 40502,
    "error_code": "TOOL_CALL_FAILED",
    "error_message": "外部工具调用失败",
    "failed_agent": "planner_agent",
    "end_at": 1770000060
}
```

错误码：

| code  | error_code           | error_message        |
| ----- | -------------------- | -------------------- |
| 40400 | VALIDATION_ERROR     | 旅行规划参数不合法   |
| 40502 | TOOL_CALL_FAILED     | 外部工具调用失败     |
| 40510 | AGENT_OUTPUT_INVALID | 智能体输出结构不合法 |
| 40511 | PLAN_QUALITY_FAILED  | 行程质量检查失败     |
| 40500 | INTERNAL_ERROR       | 旅行规划失败         |

连接建立前错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 400         | 40400     | 旅行规划参数不合法  |
| 401         | 20403     | 未登录或 token 无效 |

## 5. 行程 API

### 5.1 行程列表

```http
GET /api/v1/trips?page=1&page_size=20&status=completed
Authorization: Bearer <access_token>
```

查询参数：

| 参数      | 类型    | 必填 | 说明                                |
| --------- | ------- | ---- | ----------------------------------- |
| page      | integer | 否   | 页码，默认 1                        |
| page_size | integer | 否   | 每页数量，默认 20，最大 100         |
| status    | string  | 否   | `planning` / `completed` / `failed` |

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "items": [
            {
                "id": "trip_xxx",
                "title": "上海3日美食文化游",
                "location": "上海市",
                "days": 3,
                "start_date": "2026-05-01",
                "end_date": "2026-05-03",
                "status": "completed",
                "latest_version_no": 1,
                "created_at": 1770000000,
                "updated_at": 1770000060
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 400         | 30400     | 行程请求参数不合法  |
| 401         | 20403     | 未登录或 token 无效 |

### 5.2 行程详情

```http
GET /api/v1/trips/{trip_id}
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "id": "trip_xxx",
        "title": "上海3日美食文化游",
        "location": "上海市",
        "days": 3,
        "start_date": "2026-05-01",
        "end_date": "2026-05-03",
        "preferences": ["美食", "历史", "小众探索"],
        "status": "completed",
        "latest_version": {
            "version_no": 1,
            "source": "initial",
            "content": {
                "trip_overview": {
                    "title": "上海3日美食文化游",
                    "total_distance_km": 42.6,
                    "tags": ["美食", "历史", "小众探索"]
                },
                "daily_itinerary": [
                    {
                        "day": 1,
                        "date": "2026-05-01",
                        "weather_label": "OUTDOOR_PREFERRED",
                        "schedule": [
                            {
                                "seq": 1,
                                "time_window": "09:00-11:00",
                                "poi_id": "B0xxx001",
                                "poi_name": "外滩",
                                "category": "CORE_SIGHTSEEING",
                                "action": "浏览",
                                "duration_hour": 2,
                                "cost": 0,
                                "reason": "天气适合户外活动，外滩适合作为第一站建立城市印象",
                                "photo": "https://example.com/waitan.jpg",
                                "location": "121.490317,31.241701"
                            },
                            {
                                "seq": 2,
                                "time_window": "11:00-11:20",
                                "action": "通勤",
                                "transport_mode": "walking",
                                "distance_meter": 800,
                                "commute_time_min": 20,
                                "from_poi": "外滩",
                                "to_poi": "南京东路"
                            },
                            {
                                "seq": 3,
                                "time_window": "11:20-12:40",
                                "poi_id": "B0xxx002",
                                "poi_name": "南京东路本帮菜餐厅",
                                "category": "LOCAL_GASTRONOMY",
                                "action": "午餐",
                                "duration_hour": 1.3,
                                "cost": 120,
                                "reason": "距离上一站近，适合在核心商圈安排午餐，减少绕路",
                                "photo": "https://example.com/restaurant.jpg",
                                "location": "121.485685,31.238177"
                            },
                            {
                                "seq": 4,
                                "time_window": "12:40-13:10",
                                "action": "通勤",
                                "transport_mode": "transit_integrated",
                                "distance_meter": 5200,
                                "commute_time_min": 30,
                                "from_poi": "南京东路本帮菜餐厅",
                                "to_poi": "上海博物馆"
                            },
                            {
                                "seq": 5,
                                "time_window": "13:10-15:10",
                                "poi_id": "B0xxx003",
                                "poi_name": "上海博物馆",
                                "category": "CORE_SIGHTSEEING",
                                "action": "浏览",
                                "duration_hour": 2,
                                "cost": 0,
                                "reason": "符合历史文化偏好，且下午安排室内参观可以降低体力消耗",
                                "photo": "https://example.com/museum.jpg",
                                "location": "121.470972,31.228809"
                            },
                            {
                                "seq": 6,
                                "time_window": "15:10-15:30",
                                "action": "通勤",
                                "transport_mode": "walking",
                                "distance_meter": 900,
                                "commute_time_min": 20,
                                "from_poi": "上海博物馆",
                                "to_poi": "人民广场"
                            },
                            {
                                "seq": 7,
                                "time_window": "15:30-17:30",
                                "poi_id": "B0xxx004",
                                "poi_name": "人民广场",
                                "category": "CITY_LEISURE",
                                "action": "浏览",
                                "duration_hour": 2,
                                "cost": 0,
                                "reason": "与上海博物馆距离近，适合作为下午轻松步行和城市休闲节点",
                                "photo": "https://example.com/renminguangchang.jpg",
                                "location": "121.475190,31.228833"
                            },
                            {
                                "seq": 8,
                                "time_window": "17:30-18:00",
                                "action": "通勤",
                                "transport_mode": "walking",
                                "distance_meter": 1100,
                                "commute_time_min": 30,
                                "from_poi": "人民广场",
                                "to_poi": "淮海路餐厅"
                            },
                            {
                                "seq": 9,
                                "time_window": "18:00-19:30",
                                "poi_id": "B0xxx005",
                                "poi_name": "淮海路餐厅",
                                "category": "LOCAL_GASTRONOMY",
                                "action": "晚餐",
                                "duration_hour": 1.5,
                                "cost": 160,
                                "reason": "晚餐安排在商圈附近，方便餐后继续休闲或返回酒店",
                                "photo": "https://example.com/dinner.jpg",
                                "location": "121.468000,31.222000"
                            },
                            {
                                "seq": 10,
                                "time_window": "19:30-20:00",
                                "action": "通勤",
                                "transport_mode": "driving",
                                "distance_meter": 4500,
                                "commute_time_min": 30,
                                "from_poi": "淮海路餐厅",
                                "to_poi": "上海市中心酒店"
                            },
                            {
                                "seq": 11,
                                "time_window": "20:00-21:00",
                                "poi_id": "B0xxx006",
                                "poi_name": "上海市中心酒店",
                                "category": "ACCOMMODATION",
                                "action": "住宿",
                                "duration_hour": 1,
                                "cost": 500,
                                "reason": "办理入住并休整，酒店靠近核心城区，便于第二天继续游览",
                                "photo": "https://example.com/hotel.jpg",
                                "location": "121.473000,31.230000"
                            }
                        ]
                    }
                ]
            },
            "created_at": 1770000060
        },
        "created_at": 1770000000,
        "updated_at": 1770000060
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 401         | 20403     | 未登录或 token 无效 |
| 403         | 30403     | 无权访问该行程      |
| 404         | 30404     | 行程不存在          |

### 5.3 删除行程

```http
DELETE /api/v1/trips/{trip_id}
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "deleted": true
    }
}
```

说明：建议使用软删除，便于后续恢复和排查问题。

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 401         | 20403     | 未登录或 token 无效 |
| 403         | 30403     | 无权访问该行程      |
| 404         | 30404     | 行程不存在          |

### 5.4 修改行程（先不实现）

基于已有行程生成新版本。

```http
POST /api/v1/trips/{trip_id}/revise
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer <access_token>
```

请求体：

```json
{
    "instruction": "第二天不要安排博物馆，换成小众街区和咖啡馆，整体节奏放慢一点"
}
```

字段说明：

| 字段        | 类型   | 必填 | 说明         |
| ----------- | ------ | ---- | ------------ |
| instruction | string | 是   | 用户修改指令 |

SSE 事件：

- 与创建规划一致。
- `done` 事件返回新的 `version_no`。

done 示例：

```json
{
    "trip_id": "trip_xxx",
    "thread_id": "thread_xxx",
    "version_no": 2,
    "end_at": 1770000300
}
```

验收要求：

- 不覆盖旧版本。
- 新版本写入 `trip_versions`。
- 最新详情接口默认返回最新版本。

错误：

| HTTP 状态码 | 业务 code | error_message        |
| ----------- | --------- | -------------------- |
| 400         | 30400     | 行程请求参数不合法   |
| 401         | 20403     | 未登录或 token 无效  |
| 403         | 30403     | 无权访问该行程       |
| 404         | 30404     | 行程不存在           |
| 409         | 30409     | 行程状态不允许操作   |
| 500         | 40500     | 旅行规划失败         |
| 502         | 40502     | 外部工具调用失败     |

### 5.5 行程版本列表（先不实现）

```http
GET /api/v1/trips/{trip_id}/versions
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "items": [
            {
                "version_no": 1,
                "source": "initial",
                "revision_instruction": null,
                "created_at": 1770000060
            },
            {
                "version_no": 2,
                "source": "revision",
                "revision_instruction": "第二天不要安排博物馆，换成小众街区和咖啡馆",
                "created_at": 1770000300
            }
        ]
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 401         | 20403     | 未登录或 token 无效 |
| 403         | 30403     | 无权访问该行程      |
| 404         | 30404     | 行程不存在          |

### 5.6 指定版本详情（先不实现）

```http
GET /api/v1/trips/{trip_id}/versions/{version_no}
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "trip_id": "trip_xxx",
        "version_no": 2,
        "source": "revision",
        "revision_instruction": "第二天不要安排博物馆，换成小众街区和咖啡馆",
        "content": {
            "trip_overview": {
                "title": "上海3日美食文化游",
                "total_distance_km": 39.8,
                "tags": ["美食", "历史", "小众探索"]
            },
            "daily_itinerary": [
                {
                    "day": 1,
                    "date": "2026-05-01",
                    "weather_label": "OUTDOOR_PREFERRED",
                    "schedule": [
                        {
                            "seq": 1,
                            "time_window": "09:00-11:00",
                            "poi_id": "B0xxx001",
                            "poi_name": "外滩",
                            "category": "CORE_SIGHTSEEING",
                            "action": "浏览",
                            "duration_hour": 2,
                            "cost": 0,
                            "reason": "天气适合户外活动，外滩适合作为第一站建立城市印象",
                            "photo": "https://example.com/waitan.jpg",
                            "location": "121.490317,31.241701"
                        },
                        {
                            "seq": 2,
                            "time_window": "11:00-11:20",
                            "action": "通勤",
                            "transport_mode": "walking",
                            "distance_meter": 800,
                            "commute_time_min": 20,
                            "from_poi": "外滩",
                            "to_poi": "南京东路"
                        }
                    ]
                }
            ]
        },
        "created_at": 1770000300
    }
}
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 401         | 20403     | 未登录或 token 无效 |
| 403         | 30403     | 无权访问该行程      |
| 404         | 30404     | 行程不存在          |
| 404         | 30414     | 行程版本不存在      |

## 6. 导出 API（先不实现）

### 6.1 导出行程

```http
GET /api/v1/trips/{trip_id}/export?format=markdown&version_no=2
Authorization: Bearer <access_token>
```

查询参数：

| 参数       | 类型    | 必填 | 说明                |
| ---------- | ------- | ---- | ------------------- |
| format     | string  | 是   | `markdown` / `json` |
| version_no | integer | 否   | 不传则导出最新版本  |

Markdown 响应：

```http
Content-Type: text/markdown; charset=utf-8
```

JSON 响应：

```http
Content-Type: application/json
```

错误：

| HTTP 状态码 | 业务 code | error_message       |
| ----------- | --------- | ------------------- |
| 400         | 30400     | 行程请求参数不合法  |
| 401         | 20403     | 未登录或 token 无效 |
| 403         | 30403     | 无权访问该行程      |
| 404         | 30404     | 行程不存在          |
| 404         | 30414     | 行程版本不存在      |

## 7. 调试与观测 API（先不实现）

这些接口用于开发和问题排查，C 端前端默认不展示。

### 7.1 智能体执行记录

```http
GET /api/v1/trips/{trip_id}/agent-runs
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "items": [
            {
                "id": "run_xxx",
                "agent_name": "resource_agent",
                "status": "completed",
                "input_summary": "上海市 3 天 美食 历史",
                "output_summary": "返回 15 个 POI",
                "error_message": null,
                "started_at": 1770000010,
                "ended_at": 1770000025
            }
        ]
    }
}
```

### 7.2 工具调用记录

```http
GET /api/v1/trips/{trip_id}/tool-call-logs
Authorization: Bearer <access_token>
```

成功响应：

```json
{
    "code": 200,
    "message": "success",
    "error_message": null,
    "data": {
        "items": [
            {
                "id": "tool_xxx",
                "agent_run_id": "run_xxx",
                "tool_name": "search_poi",
                "status": "completed",
                "response_summary": "返回 20 个 POI",
                "latency_ms": 820,
                "created_at": 1770000016
            }
        ]
    }
}
```

## 8. 核心枚举

### 8.1 trip.status

| 值        | 含义   |
| --------- | ------ |
| planning  | 规划中 |
| completed | 已完成 |
| failed    | 失败   |
| deleted   | 已删除 |

### 8.2 POI category

| 值               | 含义     |
| ---------------- | -------- |
| CORE_SIGHTSEEING | 核心景点 |
| LOCAL_GASTRONOMY | 本地美食 |
| CITY_LEISURE     | 城市休闲 |
| ACCOMMODATION    | 住宿     |

### 8.3 schedule.action

| 值   | 含义               |
| ---- | ------------------ |
| 浏览 | 游览景点或城市空间 |
| 早餐 | 早餐               |
| 午餐 | 午餐               |
| 晚餐 | 晚餐               |
| 休息 | 休息               |
| 住宿 | 酒店或民宿         |
| 通勤 | 地点之间移动       |
| 其他 | 其他活动           |

## 9. 行程内容结构

### 9.1 TripOverview

```json
{
    "title": "上海3日美食文化游",
    "total_distance_km": 42.6,
    "tags": ["美食", "历史", "小众探索"]
}
```

### 9.2 DailyItinerary

```json
{
    "day": 1,
    "date": "2026-05-01",
    "weather_label": "OUTDOOR_PREFERRED",
    "schedule": [
        {
            "seq": 1,
            "time_window": "09:00-11:00",
            "poi_id": "B0xxx001",
            "poi_name": "外滩",
            "category": "CORE_SIGHTSEEING",
            "action": "浏览",
            "duration_hour": 2,
            "cost": 0,
            "reason": "天气适合户外活动，外滩适合作为第一站建立城市印象",
            "photo": "https://example.com/waitan.jpg",
            "location": "121.490317,31.241701"
        },
        {
            "seq": 2,
            "time_window": "11:00-11:20",
            "action": "通勤",
            "transport_mode": "walking",
            "distance_meter": 800,
            "commute_time_min": 20,
            "from_poi": "外滩",
            "to_poi": "南京东路"
        }
    ]
}
```

### 9.3 活动节点

```json
{
    "seq": 1,
    "time_window": "09:00-11:00",
    "poi_id": "B0xxx",
    "poi_name": "外滩",
    "category": "CORE_SIGHTSEEING",
    "action": "浏览",
    "duration_hour": 2,
    "cost": 0,
    "reason": "天气晴朗，适合安排城市地标步行游览",
    "photo": "https://example.com/photo.jpg",
    "location": "121.490317,31.241701"
}
```

### 9.4 通勤节点

```json
{
    "seq": 2,
    "time_window": "11:00-11:20",
    "action": "通勤",
    "transport_mode": "walking",
    "distance_meter": 800,
    "commute_time_min": 20,
    "from_poi": "外滩",
    "to_poi": "南京东路"
}
```
