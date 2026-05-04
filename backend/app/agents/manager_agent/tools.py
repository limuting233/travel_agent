from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from datetime import datetime, date


class IsNeedSearchWeatherInput(BaseModel):
    """
    是否需要搜索天气工具的输入参数
    """
    start_date: str | None = Field(description="开始日期，没有则为None", examples=["2026-01-11"],
                                   pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(description="结束日期，没有则为None", examples=["2026-01-15"],
                                 pattern=r"^\d{4}-\d{2}-\d{2}$")
    today: str | None = Field(description="当前日期，没有则为None", examples=["2026-01-11"],
                              pattern=r"^\d{4}-\d{2}-\d{2}$")


async def is_need_search_weather(start_date: str | None, end_date: str | None, today: str | None) -> bool:
    """
    判断是否需要搜索天气
    :return: 是否需要搜索天气
    """
    # 如果开始日期、结束日期、当前日期都有值
    if not (start_date and end_date and today):
        return False
    if datetime.strptime(start_date, "%Y-%m-%d") >= datetime.strptime(today, "%Y-%m-%d") and (datetime.strptime(
            start_date,
            "%Y-%m-%d") - datetime.strptime(
        today, "%Y-%m-%d")).days <= 2:
        return True
    return False


is_need_search_weather_tool = StructuredTool.from_function(
    coroutine=is_need_search_weather,
    name="is_need_search_weather",
    description="""
    判断是否需要查询天气的决策工具。
    
    功能：根据旅行开始日期与当前日期的时间差，判断是否在天气预报可查询范围内。
    
    决策逻辑：
    - 天气API仅支持查询未来3天（含今天）的数据
    - 当 start_date 在 [today, today+2] 范围内时返回 True
    - 当 start_date 超出3日窗口或缺少必要日期参数时返回 False
    
    使用场景：
    - Manager Agent 在启动阶段决定是否调度 Environment Agent 查询天气
    - 避免对超出预报范围的日期进行无效的天气查询
    """,
    return_direct=False,
    args_schema=IsNeedSearchWeatherInput,
)
