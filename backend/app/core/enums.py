from enum import Enum


class StatusInfo(Enum):
    """
    状态信息枚举类
    """
    # (http状态码, 业务状态码, 状态描述)
    SUCCESS = (200, 200, "success")

    # 全局系统类 (10xxx)
    BAD_REQUEST = (400, 10400, "请求参数不合法")
    ROUTE_NOT_FOUND = (404, 10404, "接口不存在")
    INTERNAL_ERROR = (500, 10500, "服务内部错误")
    UPSTREAM_ERROR = (502, 10502, "外部服务调用失败")

    # 用户与权限类 (20xxx)
    LOGIN_EMPTY_CREDENTIALS = (400, 20400, "用户名和密码不能为空")
    LOGIN_INVALID_LENGTH = (400, 20401, "用户名或密码格式不合法")
    LOGIN_INVALID_CREDENTIALS = (401, 20402, "用户名或密码错误")
    AUTH_REQUIRED = (401, 20403, "未登录或 token 无效")
    AUTH_FORBIDDEN = (403, 20404, "无权访问该资源")
    REGISTER_USERNAME_EXISTS = (409, 20409, "用户名已存在")

    # 行程类 (30xxx)
    TRIP_BAD_REQUEST = (400, 30400, "行程请求参数不合法")
    TRIP_FORBIDDEN = (403, 30403, "无权访问该行程")
    TRIP_NOT_FOUND = (404, 30404, "行程不存在")
    TRIP_STATUS_CONFLICT = (409, 30409, "行程状态不允许操作")
    TRIP_VERSION_NOT_FOUND = (404, 30414, "行程版本不存在")

    # 旅行规划类 (40xxx)
    TRAVEL_PLAN_INVALID_PARAMS = (400, 40400, "旅行规划参数不合法")
    TRAVEL_INTERNAL_ERROR = (500, 40500, "旅行规划失败")
    TRAVEL_TOOL_CALL_FAILED = (502, 40502, "外部工具调用失败")
    TRAVEL_AGENT_OUTPUT_INVALID = (500, 40510, "智能体输出结构不合法")
    TRAVEL_PLAN_QUALITY_FAILED = (500, 40511, "行程质量检查失败")
