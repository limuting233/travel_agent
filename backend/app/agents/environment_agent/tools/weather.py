import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.core.config import settings
from loguru import logger
from datetime import datetime, date
import re


class SearchWeatherInput(BaseModel):
    location: str = Field(
        description="查询天气的目标城市或地区名称。为了避免重名歧义，建议使用'城市+区/县'的全称格式。",
        examples=["上海市浦东新区", "北京市朝阳区", "杭州市西湖区", "深圳市南山区"],
    )
    start_date: str = Field(
        description="查询起始日期，格式必须为 YYYY-MM-DD。注意：日期必须在未来4天以内（含今天）。",
        examples=["2026-01-05"],
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    end_date: str = Field(
        description="查询结束日期，格式必须为 YYYY-MM-DD。必须晚于或等于起始日期，且不能超过未来4天的范围。",
        examples=["2026-01-08"],
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )

async def search_weather(location: str, start_date: str, end_date: str) -> list[dict]:
    """
    查询天气信息
    :param location: 目的地
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 天气信息列表，每个元素为一个字典，包含日期、星期、白天/夜间天气状况、风向风力、温度等信息
    """

    async with httpx.AsyncClient() as client:
        try:
            # 获取location对应的adcode
            adcode = await get_adcode(location, client)
            # 获取adcode对应的天气
            weather = await get_weather(adcode, client, start_date, end_date)
            # print(weather)
            # weather_str = f"{location}的天气信息:\n{weather}"
            # print(weather_str)
            # print(weather)
            return weather
            # return weather_str
        except Exception as e:
            logger.exception(f"查询{location}的天气信息失败")
            return f"查询{location}的天气信息失败"


search_weather_tool = StructuredTool.from_function(
    coroutine=search_weather,  # 使用 coroutine 参数支持异步函数
    name="search_weather",
    description="""
    专业气象数据查询工具。
    
    功能：根据地点和日期范围，获取精准的每日天气预报数据。
    
    重要限制 (CRITICAL):
    1. 【时间窗口】仅支持查询未来 4 天内（含今天）的数据。例如：今天是1月1日，只能查1月1日至1月4日。
    2. 【超出范围】如果请求的日期超出此范围，工具将只返回有效日期内的数据，或返回空数据。
    
    返回数据结构：
    返回一个包含每日天气详情的 JSON 列表，字段包括：日期、星期、白天/夜间天气(晴/雨等)、气温(℃)、风向风力等。
    """,
    return_direct=False,
    args_schema=SearchWeatherInput,
)


async def get_adcode(location: str, client: httpx.AsyncClient) -> str:
    """
    获取location对应的adcode
    :param location: 目的地
    :param client: httpx.AsyncClient
    :return: adcode
    """
    try:
        resp = await client.get(
            url=f"{settings.AMAP_API_BASE}/v3/geocode/geo",
            params={
                "key": settings.AMAP_API_KEY,
                "address": location,

            }
        )
        resp.raise_for_status()
        resp = resp.json()
        if resp["status"] == "0":
            raise Exception(resp["info"])
        adcode = resp["geocodes"][0]["adcode"]
        return adcode
    except Exception as e:
        # logger.error(f"获取{location}的adcode失败,{str(e)}")
        raise Exception(f"获取adcode失败,{str(e)}") from e


async def get_weather(adcode: str, client: httpx.AsyncClient, start_date: str, end_date: str) -> list[dict]:
    """
    获取adcode对应的天气,只可查询未来4天的天气信息，包括当前日期
    :param adcode: 区域编码
    :param client: httpx.AsyncClient
    :param start_date: 计划开始日期
    :param end_date: 计划结束日期
    :return: 天气信息
    """
    try:
        resp = await client.get(
            url=f"{settings.AMAP_API_BASE}/v3/weather/weatherInfo",
            params={
                "key": settings.AMAP_API_KEY,
                "city": adcode,
                "extensions": "all"
            }
        )
        resp.raise_for_status()
        resp = resp.json()
        # print(resp["forecasts"][0]["casts"])
        if resp["status"] == "0":
            raise Exception(resp["info"])
        if resp["status"] == "1" and resp["info"] == "OK" and resp["infocode"] == "10000" and resp["count"] == "1":
            casts = resp["forecasts"][0]["casts"]  # 获取casts列表

            # 过滤出指定日期范围内的天气信息
            filtered_casts = filter(
                lambda x: datetime.strptime(start_date, "%Y-%m-%d") <= datetime.strptime(x["date"],
                                                                                         "%Y-%m-%d") <= datetime.strptime(
                    end_date, "%Y-%m-%d"), casts)
            # print(list(filtered_casts))
            # for cast in casts:
            #     if datetime.strptime(start_date, "%Y-%m-%d") <= datetime.strptime(cast["date"],
            #                                                                       "%Y-%m-%d") <= datetime.strptime(
            #         end_date, "%Y-%m-%d"):
            #         filtered_casts.append(cast)
            # print(list(filtered_casts))

            # filtered_casts = list(filtered_casts)
            # 调整filtered_casts的键名，和一些值的单位
            # 星期数字转中文映射（1=星期一，2=星期二，依此类推）
            week_map = {'1': '星期一', '2': '星期二', '3': '星期三', '4': '星期四', '5': '星期五', '6': '星期六',
                        '7': '星期日'}
            # 存储每日天气的中文描述
            weather = []
            for cast in filtered_casts:
                date_ = datetime.strftime(datetime.strptime(
                    cast["date"], "%Y-%m-%d"), "%Y年%m月%d日")
                week = week_map[cast["week"]]
                day_weather = cast["dayweather"]
                night_weather = cast["nightweather"]
                day_temperature = cast["daytemp"]
                night_temperature = cast["nighttemp"]
                day_wind = cast["daywind"]
                night_wind = cast["nightwind"]
                day_power = cast["daypower"]
                night_power = cast["nightpower"]

                day_weather_dict = {
                    "日期": date_,
                    "星期": week,
                    "白天天气": day_weather,
                    "白天平均气温（℃）": day_temperature,
                    "白天风向": day_wind,
                    "白天风力（级）": day_power,
                    "夜间天气": night_weather,
                    "夜间平均气温（℃）": night_temperature,
                    "夜间风向": night_wind,
                    "夜间风力（级）": night_power,
                }
                weather.append(day_weather_dict)

            # return weather_info
            return weather

    except Exception as e:
        raise Exception(f"{str(e)}") from e
        # logger.error(f"查询{adcode}的天气失败, {str(e)}")
