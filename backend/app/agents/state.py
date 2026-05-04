import operator
from typing import TypedDict, List, Annotated, Literal

from langchain.messages import AnyMessage


class TravelAgentState(TypedDict):
    """
    旅行智能体自定义状态
    """
    # user_id: str  # 用户ID
    messages: Annotated[List[AnyMessage], operator.add]  # 消息列表
    is_just_start: bool  # 是否是刚启动
    # manager_agent_response: dict  # manager_agent响应
    #
    # environment_agent_response: str  # environment_agent响应
    # resource_agent_response: dict  # resource_agent响应
    # planner_agent_response: dict  # planner_agent响应
    current_phase: Literal["manager_agent", "environment_agent", "resource_agent", "planner_agent"]  # 当前阶段
    next_phase: Literal["manager_agent", "environment_agent", "resource_agent", "planner_agent", "finish"]  # 下一个阶段
    is_need_correct: bool  # 是否需要修正
    need_correct_content: str | None  # 需要修正的内容
