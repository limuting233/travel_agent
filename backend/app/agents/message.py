from typing import Literal

from langchain_core.messages import AIMessage


class ManagerAgentMessage(AIMessage):
    """
    manager_agent消息,继承AIMessage,用于表示manager_agent的消息
    """
    type: Literal["manager_agent"] = "manager_agent"


class EnvironmentAgentMessage(AIMessage):
    """
    environment_agent消息,继承AIMessage,用于表示environment_agent的消息
    """
    type: Literal["environment_agent"] = "environment_agent"


class ResourceAgentMessage(AIMessage):
    """
    resource_agent消息,继承AIMessage,用于表示resource_agent的消息
    """
    type: Literal["resource_agent"] = "resource_agent"


class PlannerAgentMessage(AIMessage):
    """
    planner_agent消息,继承AIMessage,用于表示planner_agent的消息
    """
    type: Literal["planner_agent"] = "planner_agent"
