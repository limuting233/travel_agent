from typing import Literal, List

import httpx
from langchain_core.tools import StructuredTool
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings

AMAP_POI_TIMEOUT_SECONDS = 15.0
AMAP_POI_PAGE_SIZE = 20


class SearchPoiInput(BaseModel):
    """
    搜索POI输入模型
    """
    city: str = Field(
        description="目标城市名称，支持中文城市名。建议使用'城市+区'格式以提高精度。",
        examples=["北京市", "上海市浦东新区", "杭州市西湖区"]
    )
    keywords: str = Field(
        description="搜索关键词，可以是地点名称、品牌名、菜系类型等。支持模糊搜索。",
        examples=["故宫", "星巴克", "川菜", "希尔顿酒店"]
    )
    category: Literal["风景名胜", "科教文", "美食", "购物", "娱乐", "住宿"] = Field(
        description="""POI分类，用于筛选搜索结果类型：
        - 风景名胜: 景点、公园、自然风光
        - 科教文: 博物馆、图书馆、学校、文化场馆
        - 美食: 餐厅、小吃店、咖啡厅、糕饼店
        - 购物: 商场、超市、专卖店
        - 娱乐: KTV、电影院、游乐场
        - 住宿: 酒店、宾馆、民宿"""
    )


async def search_poi(city: str, keywords: str, category: str) -> List[dict]:
    """
    根据关键词和区域代码搜索POI
    :param city: 城市名称
    :param keywords: 搜索关键词
    :param category: POI分类
    :return: 搜索到的POI列表
    """
    AMAP_TYPE_MAPPING = {
        "风景名胜": "110000|110100|110101|110102|110103|110104|110105|110106|110200|110201|110202|110203|110204|110205|110206|110207|110208|110209|110210",
        "科教文": "140100|140101|140102|140200|140201|140300|140400|140500|140600|140700",
        "美食": "050000|050100|050101|050102|050103|050104|050105|050106|050107|050108|050109|050110|050111|050112|050113|050114|050115|050119|050120|050121|050122|050123|050200|050201|050202|050203|050204|050400|050500",
        "购物": "060100|060101|060102|060103|060200|060201|060202|060400|060401|060402|060403|060404|060800|060900|060901",
        "娱乐": "080302|080303|080304|080400|080401|080402|080500|080501|080502|080503|080504|080505",
        "住宿": "100101|100102|100103|100104|100105|100200|100201"
    }

    types = AMAP_TYPE_MAPPING[category]

    logger.info(f"[search_poi] city={city}, keywords={keywords}, category={category}")

    async with httpx.AsyncClient(timeout=AMAP_POI_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.get(
                url=f"{settings.AMAP_API_BASE}/v5/place/text",
                params={
                    "key": settings.AMAP_API_KEY,
                    "keywords": keywords,
                    "types": types,
                    "region": city,
                    "city_limit": "true",
                    "show_fields": "business,navi,photos",
                    "page_size": AMAP_POI_PAGE_SIZE,
                }
            )
            resp.raise_for_status()
            resp = resp.json()
            # print(resp)
            if resp["status"] == "0":
                raise Exception(resp["info"])
            pois = resp["pois"]
            # print(pois)
            # return pois
            filter_pois = []
            for poi in pois:
                new_poi = {
                    "id": poi["id"],
                    "名称": poi["name"],
                    "经纬度（经度,纬度）": poi["location"],
                    "地址": poi["address"],
                    "分类": poi["type"],
                    "营业时间（每周）": poi["business"].get("opentime_week", ""),
                    "联系电话": poi["business"].get("tel", ""),
                    "标签": poi["business"].get("tag", ""),
                    "评分（0-5分）": poi["business"].get("rating", ""),
                    "人均消费（元/人）": poi["business"].get("cost", ""),
                    "入口位置（经度,纬度）": poi["navi"].get("entr_location", ""),
                    "出口位置（经度,纬度）": poi["navi"].get("exit_location", ""),
                    "照片URL": poi["photos"][0].get("url", "") if poi.get("photos", []) else None,
                }
                filter_pois.append(new_poi)
            logger.info(f"[search_poi] 返回 {len(filter_pois)} 个POI")
            return filter_pois

        except Exception:
            logger.exception(f"搜索POI失败")
            return []


search_poi_tool = StructuredTool.from_function(
    coroutine=search_poi,
    name="search_poi",
    description="""
    基于高德地图的POI（兴趣点）搜索工具。
    
    功能：根据城市、关键词和分类搜索指定区域内的地点信息。
    
    适用场景：
    - 查找旅游景点、餐厅、酒店、购物中心等
    - 获取商家的详细信息（地址、电话、营业时间、评分等）
    - 规划行程时查找特定类型的场所
    
    返回数据结构（JSON列表）：
    - id: POI唯一标识
    - 名称: 商家/地点名称
    - 经纬度: 地理坐标（经度,纬度）
    - 地址: 详细地址
    - 分类: POI类型分类
    - 营业时间: 每周营业时间
    - 联系电话: 商家电话
    - 标签: 特色标签（如菜品、服务等）
    - 评分: 0-5分评分
    - 人均消费: 消费参考（元/人）
    - 入口/出口位置: 导航坐标
    - 照片URL: 商家图片链接
    """,
    args_schema=SearchPoiInput,
    return_direct=False,
)


class CalculatePoiCountInput(BaseModel):
    """
    计算POI数量输入模型
    """
    days: int = Field(
        description="旅游天数，必须为正整数。用于估算行程所需的地点数量。如果描述为两天一夜则算days为1，以此类推",
        ge=1,
        examples=[3, 5, 7]
    )


async def calculate_poi_count(days: int) -> int:
    """
    根据旅游天数计算推荐的POI（兴趣点）数量。

    计算规则：每天4个POI + 3个固定POI

    :param days: 旅游天数
    :return: 推荐的POI总数量
    """
    return days * 4 + 3


calculate_poi_count_tool = StructuredTool.from_function(
    coroutine=calculate_poi_count,
    name="calculate_poi_count",
    description="""
    旅游行程POI数量计算工具。
    
    功能：根据旅游天数计算行程规划所需的推荐POI（兴趣点）数量。
    
    计算规则：
    - 公式：天数 × 4 + 3
    
    使用场景：
    - 规划旅游行程前，估算需要收集多少个地点信息
    - 确保行程内容丰富度与天数匹配
    
    示例：
    - 3天行程 → 15个POI（3×4+3）
    - 5天行程 → 23个POI（5×4+3）
    - 7天行程 → 31个POI（7×4+3）
    """,
    args_schema=CalculatePoiCountInput,
    return_direct=False,
)
