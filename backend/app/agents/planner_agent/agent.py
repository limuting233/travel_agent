from plistlib import load
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

from app.agents.planner_agent.prompt import PLANNER_AGENT_SYSTEM_PROMPT


class TripOverview(BaseModel):
    """
    行程概述模型
    """
    title: str = Field(description="行程标题")
    total_distance_km: float = Field(description="总距离（公里）")
    tags: list[str] = Field(description="行程标签")


class ScheduleItemPlay(BaseModel):
    """
    行程计划项模型（游玩）
    """
    seq: int = Field(description="计划项序号", examples=[1, 2, 3], ge=1)
    time_window: str = Field(
        description="活动时间窗口,格式为HH:MM-HH:MM", examples=["08:00-09:00"])
    poi_id: str = Field(description="高德地图POI ID", examples=["B0L1KZTJ0T"])
    poi_name: str = Field(description="POI名称", examples=["天安门"])
    category: Literal["CORE_SIGHTSEEING", "LOCAL_GASTRONOMY", "CITY_LEISURE", "ACCOMMODATION"] = Field(
        description="POI分类", examples=["CORE_SIGHTSEEING", "LOCAL_GASTRONOMY", "CITY_LEISURE", "ACCOMMODATION"])
    action: Literal["浏览", "午餐", "休息", "住宿", "晚餐", "早餐", "其他"] = Field(description="活动类型",
                                                                                    examples=["浏览", "午餐", "休息",
                                                                                              "住宿", "晚餐", "早餐",
                                                                                              "其他"])
    duration_hour: float = Field(description="活动持续时间（小时）", examples=[
        1.0, 2.0, 3.5], gt=0.0)
    cost: float | None = Field(
        default=None, description="活动成本（元）", examples=[0, 10, 20], ge=0.0)
    reason: str = Field(description="活动原因", examples=["历史悠久，是中国的重要历史景点"])
    photo: str = Field(default="", description="地点照片URL", examples=["https://example.com/photo1.jpg"])
    location: str = Field(default="", description="地点位置，格式为：经度,纬度", examples=["116.397428,39.90923"])


class ScheduleItemCommute(BaseModel):
    """
    行程计划项模型（通勤）
    """
    seq: int = Field(description="计划项序号", examples=[1, 2, 3], ge=1)
    time_window: str = Field(
        description="通勤时间窗口,格式为HH:MM-HH:MM", examples=["12:00-13:00"])
    action: Literal["通勤"] = Field(
        description="action的值只可以是通勤", examples=["通勤"])
    transport_mode: Literal["bicycling", "driving", "transit_integrated", "walking"] = Field(
        description="通勤方式", examples=["bicycling", "driving", "transit_integrated", "walking"])
    distance_meter: float = Field(description="通勤距离（米）", examples=[
        1000, 2000, 300.5], gt=0.0)
    commute_time_min: int = Field(
        description="通勤持续时间（分钟）", examples=[10, 20, 30], gt=0)
    from_poi: str = Field(description="出发POI 名称", examples=["天安门"])
    to_poi: str = Field(description="到达POI 名称", examples=["故宫"])


class DailyTrip(BaseModel):
    """
    每日行程模型
    """
    day: int = Field(description="第几天", examples=[1, 2, 3], ge=1)
    date: str | None = Field(default=None, description="日期，未指定旅行日期时为None，格式为YYYY-MM-DD", examples=["2024-01-01"])
    weather_label: str = Field(description="天气标签")
    schedule: list[ScheduleItemPlay | ScheduleItemCommute] = Field(
        description="行程计划，每个元素为一个活动，包含活动名称和时间窗口")


class PlannerAgentOutput(BaseModel):
    """
    旅游规划师智能体输出模型
    """
    trip_overview: TripOverview = Field(description="行程概述")
    daily_itinerary: list[DailyTrip] = Field(description="每日行程")


class PlannerAgentBuilder:
    """
    旅游规划师智能体构建器，用于构建旅游规划师智能体。
    """

    def __init__(self):
        # 初始化deepseek模型
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_API_MODEL, 
            base_url=settings.DEEPSEEK_API_BASE, 
            api_key=settings.DEEPSEEK_API_KEY,
            extra_body={"thinking": {"type": "disabled"}})

    async def build(self):
        """
        构建旅游规划师智能体
        :return: 旅游规划师智能体实例
        """
        from app.agents.mcp import amap_mcp_session
        amap_tools = await load_mcp_tools(session=amap_mcp_session)
        pla_agent_need_tools = [tool for tool in amap_tools if
                                tool.name in ["maps_direction_bicycling", "maps_direction_driving",
                                              "maps_direction_transit_integrated", "maps_direction_walking",
                                              "maps_distance"]]
        return create_agent(
            model=self.llm,
            tools=pla_agent_need_tools,
            system_prompt=PLANNER_AGENT_SYSTEM_PROMPT,
            response_format=ToolStrategy(PlannerAgentOutput),
            debug=True,
        )

        # return create_agent(
        #     model=self.llm
        # )
