from typing import Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agents.resource_agent.prompt import RESOURCE_AGENT_SYSTEM_PROMPT
from app.core.config import settings


class SearchPlanTask(BaseModel):
    """
    单个POI搜索任务。
    """
    category: Literal["风景名胜", "科教文", "美食", "购物", "娱乐", "住宿"] = Field(
        description="高德POI搜索分类"
    )
    keyword: str = Field(description="搜索关键词，必须结合目的地和具体意图", min_length=1)
    limit: int = Field(default=3, description="该任务最多保留的候选数量", ge=1, le=8)
    reason: str = Field(default="", description="为什么需要这个搜索任务")


class SearchPlanOutput(BaseModel):
    """
    ResourceAgent输出的搜索计划。
    """
    tasks: list[SearchPlanTask] = Field(description="后端需要并发执行的POI搜索任务", min_length=1, max_length=8)


class ResourceAgentBuilder:
    """
    ResourceAgent只负责生成搜索计划，实际POI搜索由后端并发执行。
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_API_MODEL,
            base_url=settings.DEEPSEEK_API_BASE,
            api_key=settings.DEEPSEEK_API_KEY,
            extra_body={"thinking": {"type": "disabled"}},
        )

    async def build(self):
        return create_agent(
            model=self.llm,
            tools=[],
            system_prompt=RESOURCE_AGENT_SYSTEM_PROMPT,
            response_format=ToolStrategy(SearchPlanOutput),
            debug=True,
        )
