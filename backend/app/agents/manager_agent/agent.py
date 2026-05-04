import json
from typing import Literal, Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agents.manager_agent.prompt import MANAGER_AGENT_SYSTEM_PROMPT
from app.agents.manager_agent.tools import is_need_search_weather_tool
from app.core.config import settings
from loguru import logger


class ManagerAgentOutput(BaseModel):
    next_to: Literal["environment_agent", "resource_agent", "planner_agent", "finish"] = Field(
        description="下一个要调用的智能体，必须是以下值之一: environment_agent, resource_agent, planner_agent, finish"
    )
    reason: str = Field(description="调用下一个智能体的原因，必须是简明的中文说明")

    @classmethod
    def parse_response(cls, resp: dict[str, Any]) -> "ManagerAgentOutput":
        """
        解析智能体的响应，返回结构化输出

        :param resp: 智能体的响应，包含messages和structured_response字段
        :return: 结构化输出，包含next_to和reason字段
        """

        if "structured_response" in resp and resp["structured_response"]:
            return resp["structured_response"]

        # 从content中解析
        last_msg = resp["messages"][-1]
        content = last_msg.content
        # ```json\n{{\n  \"next_to\": \"environment_agent\",\n  \"reason\": \"is_need_search_weather工具返回True，start_date(2026-02-15)在天气预报可查询范围内(今日为2026-02-15)，需先查询天气制定出行策略\"\n}
        # 移除```json\n前缀
        logger.info(f"原始content: \n{content}")
        content = content.replace("```json\n", "").replace("```", "")
        logger.info(f"移除```json\\n前缀和```尾缀后的content:\n {content}")

        try:
            return cls.model_validate_json(content)
        except Exception:
            decoded = content.encode().decode("unicode_escape")
            return cls.model_validate_json(decoded)


class ManagerAgentBuilder:
    def __init__(self):
        # 初始化deepseek模型
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_API_MODEL, 
            base_url=settings.DEEPSEEK_API_BASE, 
            api_key=settings.DEEPSEEK_API_KEY,
            extra_body={"thinking": {"type": "disabled"}})

    def build(self):
        return create_agent(
            model=self.llm,
            tools=[is_need_search_weather_tool],
            system_prompt=MANAGER_AGENT_SYSTEM_PROMPT,
            response_format=ToolStrategy(ManagerAgentOutput),
            debug=True,
        )
