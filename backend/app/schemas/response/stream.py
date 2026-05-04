from typing import Literal, Union

from pydantic import BaseModel, Field


class StartEvent(BaseModel):
    """
    工作流开始事件数据
    """
    thread_id: str = Field(..., description="线程ID")
    trip_id: str = Field(..., description="行程ID")
    start_at: int = Field(..., description="本次对话开始时间,秒时间戳")


class AgentStepEvent(BaseModel):
    """
    智能体阶段变化事件数据
    """
    agent: Literal[
        "manager_agent",
        "environment_agent",
        "resource_agent",
        "planner_agent",
    ] = Field(..., description="智能体名称")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        ..., description="智能体阶段状态"
    )
    message: str = Field(..., description="阶段展示文案")


class ToolCallEvent(BaseModel):
    """
    外部工具调用事件数据
    """
    agent: str = Field(..., description="发起工具调用的智能体")
    tool_name: str = Field(..., description="工具名称")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        ..., description="工具调用状态"
    )
    message: str = Field(..., description="工具调用展示文案")
    latency_ms: int | None = Field(default=None, description="工具调用耗时，毫秒")


class MessageEvent(BaseModel):
    """
    消息事件数据
    """
    content: str = Field(..., description="消息内容")


class DoneEvent(BaseModel):
    """
    完成事件数据
    """
    trip_id: str = Field(..., description="行程ID")
    thread_id: str = Field(..., description="聊天线程ID")
    version_no: int = Field(..., description="行程版本号")
    end_at: int = Field(..., description="本次对话结束时间,秒时间戳")


class ErrorEvent(BaseModel):
    """
    规划失败事件数据
    """
    trip_id: str = Field(..., description="行程ID")
    thread_id: str = Field(..., description="聊天线程ID")
    code: int = Field(..., description="业务状态码")
    error_code: str = Field(..., description="错误码")
    error_message: str = Field(..., description="错误信息")
    failed_agent: str | None = Field(default=None, description="失败智能体")
    end_at: int = Field(..., description="失败结束时间,秒时间戳")


class StreamResponse(BaseModel):
    """
    流式响应模型
    """
    event: Literal[
        "start",
        "agent_step",
        "tool_call",
        "message",
        "error",
        "done",
    ] = Field(description="事件类型")
    data: Union[
        StartEvent,
        AgentStepEvent,
        ToolCallEvent,
        MessageEvent,
        DoneEvent,
        ErrorEvent,
    ] = Field(description="事件数据")
