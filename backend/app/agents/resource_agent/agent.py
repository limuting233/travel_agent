from contextlib import asynccontextmanager
from typing import List, Literal, Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agents.resource_agent.prompt import RESOURCE_AGENT_SYSTEM_PROMPT
from app.agents.resource_agent.tools.poi import search_poi_tool, calculate_poi_count_tool
from app.core.config import settings


class Candidate(BaseModel):
    """
    地点候选模型
    """
    id: str = Field(description="高德地图地点ID", examples=["B0L1KZTJ0T"])
    name: str = Field(description="地点名称", examples=["天安门"])
    category: Literal["CORE_SIGHTSEEING", "LOCAL_GASTRONOMY", "CITY_LEISURE", "ACCOMMODATION"] = Field(
        description="地点分类", examples=["CORE_SIGHTSEEING"])
    tags: List[str] = Field(description="地点标签", examples=[["历史", "文化"]])
    location: str = Field(default="", description="地点位置，格式为：经度,纬度", examples=["116.397428,39.90923"])
    rating: float | None = Field(default=None, description="地点评分", examples=[4.5])
    price: float | None = Field(default=None, description="人均消费，单位：元/人", examples=[100])
    open_time: str = Field(
        default="",
        description="营业时间，24小时制。支持三种格式：1)单时段：HH:mm-HH:mm；2)多时段用逗号分隔：HH:mm-HH:mm,HH:mm-HH:mm；3)区分工作日/休息日用分号分隔：工作日HH:mm-HH:mm;休息日HH:mm-HH:mm",
        examples=["09:00-22:00", "09:00-14:00,16:00-20:00",
                  "工作日09:00-14:00,16:00-20:00;休息日09:00-14:00,16:00-24:00"]
    )
    suggested_duration: float | None = Field(default=None, description="建议游玩时间，单位小时", examples=[2])
    photo: str = Field(default="", description="地点照片URL，一个就可以", examples=["https://example.com/photo1.jpg"])
    recommend_reason: str = Field(default="", description="基于地点数据和用户偏好生成的推荐理由",
                                  examples=["历史悠久，是中国的重要历史景点"])


class ResourceAgentOutput(BaseModel):
    """
    ResourceAgent输出模型
    """
    candidates: List[Candidate] = Field(description="符合条件的地点列表", examples=[[
        Candidate(id="B0L1KZTJ0T", name="天安门", category="CORE_SIGHTSEEING", tags=["历史", "文化"],
                  location="116.397428,39.90923", rating=4.5, price=100, open_time="09:00-22:00", suggested_duration=2,
                  photo="https://example.com/photo1.jpg",
                  recommend_reason="历史悠久，是中国的重要历史景点")]])

    # @classmethod
    # def parse_response(cls, resp: dict[str, Any]) -> "ResourceAgentOutput":
    #     """
    #     解析ResourceAgent的响应，将其转换为ResourceAgentOutput模型
    #     :param resp: ResourceAgent的响应，包含结构化输出字段
    #     :return: ResourceAgentOutput模型实例
    #     """
    #     if "structured_response" in resp and resp["structured_response"]:
    #         return resp["structured_response"]
    #
    #     last_msg = resp["messages"][-1].content


class ResourceAgentBuilder:
    """
    ResourceAgent构建器，用于构建ResourceAgent
    """

    def __init__(self):
        # 初始化deepseek模型
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_API_MODEL,
            base_url=settings.DEEPSEEK_API_BASE,
            api_key=settings.DEEPSEEK_API_KEY,
            extra_body={"thinking": {"type": "disabled"}}
        )

    # @asynccontextmanager
    async def build(self):
        """
        构建ResourceAgent
        :return: ResourceAgent实例
        """
        res_agent = create_agent(
            model=self.llm,
            tools=[search_poi_tool, calculate_poi_count_tool],
            system_prompt=RESOURCE_AGENT_SYSTEM_PROMPT,
            response_format=ToolStrategy(ResourceAgentOutput),
            debug=True,
        )
        return res_agent
