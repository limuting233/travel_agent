import asyncio
import json
import math
import re
from datetime import date, datetime, timedelta

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

from app.agents.context import TravelAgentContext
from app.agents.environment_agent.agent import EnvironmentAgentBuilder
from app.agents.manager_agent.agent import ManagerAgentBuilder, ManagerAgentOutput
# from app.agents.mcp import create_mcp_client
from app.agents.memory import init_checkpointer
from app.agents.message import ManagerAgentMessage, EnvironmentAgentMessage, ResourceAgentMessage, PlannerAgentMessage
from app.agents.resource_agent.agent import ResourceAgentBuilder, SearchPlanOutput, SearchPlanTask
from app.agents.resource_agent.tools.poi import calculate_poi_count, search_poi
from app.agents.state import TravelAgentState

from loguru import logger

travel_agent = None

RESOURCE_CATEGORY_MAP = {
    "风景名胜": "CORE_SIGHTSEEING",
    "科教文": "CORE_SIGHTSEEING",
    "美食": "LOCAL_GASTRONOMY",
    "购物": "CITY_LEISURE",
    "娱乐": "CITY_LEISURE",
    "住宿": "ACCOMMODATION",
}

PLANNER_ROUTE_MCP_CALL_LIMIT = 6
BLOCKED_CHAIN_FOOD_KEYWORDS = (
    "肯德基",
    "kfc",
    "麦当劳",
    "mcdonald",
    "必胜客",
    "pizza hut",
    "达美乐",
    "domino",
    "汉堡王",
    "burger king",
    "星巴克",
    "starbucks",
    "瑞幸",
    "luckin",
    "喜茶",
    "奈雪",
    "一点点",
    "coco",
    "蜜雪冰城",
    "华莱士",
    "德克士",
    "dicos",
    "赛百味",
    "subway",
    "棒约翰",
    "papa john",
)
LOCAL_FOOD_RULES = {
    "北京": {
        "search_keywords": ("北京烤鸭", "北京小吃", "京味老字号"),
        "include_keywords": (
            "北京菜",
            "京菜",
            "京味",
            "老北京",
            "烤鸭",
            "涮肉",
            "铜锅",
            "炸酱面",
            "豆汁",
            "焦圈",
            "卤煮",
            "炒肝",
            "爆肚",
            "驴打滚",
            "豌豆黄",
            "灌肠",
            "糖火烧",
            "羊蝎子",
            "门钉肉饼",
            "褡裢火烧",
            "小吊梨汤",
            "护国寺",
            "牛街",
            "门框胡同",
            "全聚德",
            "便宜坊",
            "四季民福",
            "大董",
            "聚宝源",
            "南门涮肉",
            "稻香村",
            "庆丰",
            "姚记",
            "天兴居",
            "都一处",
            "锦芳",
            "北平",
        ),
    },
    "上海": {
        "search_keywords": ("上海本帮菜", "上海小吃", "上海老字号"),
        "include_keywords": (
            "本帮",
            "上海菜",
            "沪菜",
            "生煎",
            "小笼",
            "小笼包",
            "蟹粉",
            "排骨年糕",
            "葱油拌面",
            "红烧肉",
            "熏鱼",
            "鲜肉月饼",
            "老上海",
            "南翔",
            "德兴馆",
            "老饭店",
            "绿波廊",
        ),
    },
    "杭州": {
        "search_keywords": ("杭州杭帮菜", "杭州小吃", "杭州老字号"),
        "include_keywords": (
            "杭帮",
            "杭州菜",
            "西湖醋鱼",
            "龙井虾仁",
            "东坡肉",
            "片儿川",
            "定胜糕",
            "葱包桧",
            "知味观",
            "楼外楼",
            "奎元馆",
        ),
    },
    "南京": {
        "search_keywords": ("南京鸭血粉丝", "南京小吃", "南京老字号"),
        "include_keywords": (
            "南京菜",
            "金陵",
            "鸭血粉丝",
            "盐水鸭",
            "板鸭",
            "鸭油烧饼",
            "汤包",
            "牛肉锅贴",
            "梅花糕",
            "秦淮",
            "夫子庙",
        ),
    },
    "苏州": {
        "search_keywords": ("苏州苏帮菜", "苏州小吃", "苏州老字号"),
        "include_keywords": (
            "苏帮",
            "苏州菜",
            "松鼠桂鱼",
            "响油鳝糊",
            "苏式面",
            "奥灶面",
            "蟹粉",
            "生煎",
            "哑巴生煎",
            "得月楼",
            "松鹤楼",
        ),
    },
    "成都": {
        "search_keywords": ("成都川菜", "成都小吃", "成都老字号"),
        "include_keywords": (
            "川菜",
            "成都小吃",
            "火锅",
            "串串",
            "钵钵鸡",
            "担担面",
            "钟水饺",
            "龙抄手",
            "夫妻肺片",
            "冒菜",
            "兔头",
            "肥肠粉",
        ),
    },
    "重庆": {
        "search_keywords": ("重庆火锅", "重庆小面", "重庆江湖菜"),
        "include_keywords": (
            "重庆火锅",
            "重庆小面",
            "江湖菜",
            "毛血旺",
            "辣子鸡",
            "酸辣粉",
            "抄手",
            "豆花",
            "山城",
        ),
    },
    "西安": {
        "search_keywords": ("西安肉夹馍", "西安小吃", "西安老字号"),
        "include_keywords": (
            "肉夹馍",
            "羊肉泡馍",
            "泡馍",
            "凉皮",
            "biangbiang",
            "臊子面",
            "葫芦鸡",
            "甑糕",
            "胡辣汤",
            "回民街",
            "陕菜",
        ),
    },
    "广州": {
        "search_keywords": ("广州早茶", "广州粤菜", "广州老字号"),
        "include_keywords": (
            "粤菜",
            "广府",
            "早茶",
            "点心",
            "肠粉",
            "烧鹅",
            "叉烧",
            "云吞面",
            "艇仔粥",
            "煲仔饭",
            "陶陶居",
            "广州酒家",
            "莲香楼",
            "泮溪",
        ),
    },
    "深圳": {
        "search_keywords": ("深圳粤菜", "深圳早茶", "深圳本地美食"),
        "include_keywords": (
            "粤菜",
            "早茶",
            "点心",
            "肠粉",
            "烧鹅",
            "叉烧",
            "潮汕",
            "客家",
            "海鲜",
            "光明乳鸽",
        ),
    },
    "厦门": {
        "search_keywords": ("厦门沙茶面", "厦门小吃", "厦门闽南菜"),
        "include_keywords": (
            "闽南",
            "沙茶面",
            "海蛎煎",
            "土笋冻",
            "姜母鸭",
            "花生汤",
            "烧肉粽",
            "面线糊",
            "同安",
        ),
    },
    "武汉": {
        "search_keywords": ("武汉热干面", "武汉小吃", "武汉湖北菜"),
        "include_keywords": (
            "热干面",
            "豆皮",
            "鸭脖",
            "武昌鱼",
            "藕汤",
            "糊汤粉",
            "烧麦",
            "过早",
            "湖北菜",
            "楚菜",
        ),
    },
    "长沙": {
        "search_keywords": ("长沙湘菜", "长沙小吃", "长沙老字号"),
        "include_keywords": (
            "湘菜",
            "臭豆腐",
            "糖油粑粑",
            "口味虾",
            "剁椒鱼头",
            "米粉",
            "小炒黄牛肉",
            "长沙菜",
        ),
    },
    "天津": {
        "search_keywords": ("天津小吃", "天津老字号", "天津本地美食"),
        "include_keywords": (
            "天津菜",
            "津菜",
            "狗不理",
            "煎饼果子",
            "麻花",
            "耳朵眼",
            "锅巴菜",
            "嘎巴菜",
            "熟梨糕",
        ),
    },
    "青岛": {
        "search_keywords": ("青岛海鲜", "青岛本地菜", "青岛小吃"),
        "include_keywords": (
            "海鲜",
            "鲁菜",
            "青岛菜",
            "啤酒",
            "鲅鱼",
            "蛤蜊",
            "锅贴",
            "脂渣",
        ),
    },
    "哈尔滨": {
        "search_keywords": ("哈尔滨东北菜", "哈尔滨俄餐", "哈尔滨小吃"),
        "include_keywords": (
            "东北菜",
            "俄餐",
            "锅包肉",
            "红肠",
            "大列巴",
            "杀猪菜",
            "铁锅炖",
            "马迭尔",
        ),
    },
    "昆明": {
        "search_keywords": ("昆明云南菜", "昆明过桥米线", "昆明小吃"),
        "include_keywords": (
            "云南菜",
            "滇菜",
            "过桥米线",
            "汽锅鸡",
            "鲜花饼",
            "菌子",
            "野生菌",
            "饵块",
        ),
    },
}


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _suggested_duration(category: str) -> float:
    if category == "LOCAL_GASTRONOMY":
        return 1.5
    if category == "ACCOMMODATION":
        return 1.0
    return 2.0


def _is_blocked_chain_food(name: str) -> bool:
    normalized_name = str(name).strip().lower()
    return any(keyword in normalized_name for keyword in BLOCKED_CHAIN_FOOD_KEYWORDS)


def _normalize_food_brand_name(name: str) -> str:
    normalized_name = str(name).strip().lower()
    normalized_name = re.sub(r"[（(][^）)]*[）)]", "", normalized_name)
    normalized_name = re.sub(r"[-_·|｜/／].*$", "", normalized_name)
    normalized_name = re.sub(r"(?:旗舰店|总店|分店|门店|餐厅)$", "", normalized_name)
    normalized_name = re.sub(r"\s+", "", normalized_name)
    return normalized_name


def _food_brand_key(candidate: dict) -> str | None:
    if candidate.get("category") != "LOCAL_GASTRONOMY":
        return None

    brand_name = _normalize_food_brand_name(str(candidate.get("name") or ""))
    return brand_name or None


def _local_food_rule(location: str) -> dict | None:
    return next((rule for city, rule in LOCAL_FOOD_RULES.items() if city in location), None)


def _is_destination_local_food(raw_poi: dict, location: str) -> bool:
    rule = _local_food_rule(location)
    if not rule:
        return True

    tags = raw_poi.get("tags", "")
    if isinstance(tags, list):
        tags = "".join(str(tag) for tag in tags)

    searchable_text = "".join(
        str(raw_poi.get(key, ""))
        for key in ("名称", "分类", "标签", "地址", "name", "category", "source_category")
    )
    searchable_text += str(tags)
    return any(keyword in searchable_text for keyword in rule["include_keywords"])


def _build_recommend_reason(
    name: str,
    category: str,
    rating: float | None,
    tags: list[str],
    raw_category: str,
    search_keyword: str,
    search_reason: str,
) -> str:
    quality_text = f"高德评分{rating:g}" if rating is not None else "高德信息完整"
    tag_text = "、".join(tags[:2]) if tags else raw_category

    if category == "LOCAL_GASTRONOMY":
        if search_reason:
            return f"{name}契合“{search_keyword}”这条本地美食线索，{quality_text}，适合作为当天餐食亮点。"
        return f"{name}带有{tag_text or '本地餐饮'}特色，{quality_text}，比普通连锁餐饮更适合放进行程。"

    if category == "CORE_SIGHTSEEING":
        if "博物" in raw_category or "展览" in raw_category or "科教" in raw_category:
            return f"{name}偏文化和室内参观，{quality_text}，适合用来丰富行程的历史与城市背景。"
        return f"{name}是这条“{search_keyword}”搜索线里的重点地点，{quality_text}，适合作为当天核心游览点。"

    if category == "CITY_LEISURE":
        return f"{name}更适合安排在下午或傍晚串联动线，{quality_text}，可以补足逛街、夜景或城市休闲体验。"

    if category == "ACCOMMODATION":
        return f"{name}作为住宿候选，位置和基础信息适合后续串联每日路线，{quality_text}。"

    return f"{name}与“{search_keyword}”匹配，{quality_text}，可作为行程候选。"


def _build_resource_candidate_from_raw_poi(
    raw_poi: dict,
    amap_category: str,
    search_keyword: str,
    search_reason: str,
) -> dict | None:
    category = RESOURCE_CATEGORY_MAP.get(amap_category)
    if category is None:
        return None

    name = str(raw_poi.get("名称") or "").strip()
    poi_id = str(raw_poi.get("id") or "").strip()
    location = str(raw_poi.get("经纬度（经度,纬度）") or "").strip()
    if not name or not poi_id or not location:
        return None

    tags = []
    raw_tags = raw_poi.get("标签")
    if raw_tags:
        tags.extend(tag.strip() for tag in str(raw_tags).split(";") if tag.strip())
    raw_category = str(raw_poi.get("分类") or "").strip()
    if raw_category:
        tags.append(raw_category)

    rating = _to_float(raw_poi.get("评分（0-5分）"))
    recommend_reason = _build_recommend_reason(
        name=name,
        category=category,
        rating=rating,
        tags=tags,
        raw_category=raw_category,
        search_keyword=search_keyword,
        search_reason=search_reason,
    )

    return {
        "id": poi_id,
        "name": name,
        "category": category,
        "tags": tags or [amap_category],
        "source_category": raw_category,
        "location": location,
        "rating": rating,
        "price": _to_float(raw_poi.get("人均消费（元/人）")),
        "open_time": raw_poi.get("营业时间（每周）", "") or "",
        "suggested_duration": _suggested_duration(category),
        "photo": raw_poi.get("照片URL") or "",
        "recommend_reason": recommend_reason,
    }


def _normalize_resource_candidate(candidate: dict, location: str) -> dict | None:
    category = candidate.get("category")
    if category not in {
        "CORE_SIGHTSEEING",
        "LOCAL_GASTRONOMY",
        "CITY_LEISURE",
        "ACCOMMODATION",
    }:
        return None

    name = str(candidate.get("name") or "").strip()
    poi_id = str(candidate.get("id") or "").strip()
    poi_location = str(candidate.get("location") or "").strip()
    if not name or not poi_id or not poi_location:
        return None

    rating = _to_float(candidate.get("rating"))
    if rating is not None and rating < 3.8 and category != "ACCOMMODATION":
        return None
    if category == "LOCAL_GASTRONOMY" and _is_blocked_chain_food(name):
        return None
    if category == "LOCAL_GASTRONOMY" and not _is_destination_local_food(candidate, location):
        return None

    tags = candidate.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]

    return {
        "id": poi_id,
        "name": name,
        "category": category,
        "tags": list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip())) or [category],
        "location": poi_location,
        "rating": rating,
        "price": _to_float(candidate.get("price")),
        "open_time": str(candidate.get("open_time") or ""),
        "suggested_duration": _to_float(candidate.get("suggested_duration")) or _suggested_duration(category),
        "photo": str(candidate.get("photo") or ""),
        "recommend_reason": str(candidate.get("recommend_reason") or "根据地点质量、位置和用户偏好推荐。"),
    }


def _sanitize_resource_candidates(candidates: list[dict], location: str) -> list[dict]:
    sanitized = []
    seen_ids = set()
    seen_food_brands = set()

    for raw_candidate in candidates:
        candidate = _normalize_resource_candidate(raw_candidate, location)
        if candidate is None:
            continue

        poi_id = candidate["id"]
        if poi_id in seen_ids:
            continue

        food_brand_key = _food_brand_key(candidate)
        if food_brand_key and food_brand_key in seen_food_brands:
            continue

        seen_ids.add(poi_id)
        if food_brand_key:
            seen_food_brands.add(food_brand_key)
        sanitized.append(candidate)

    return sanitized


async def _validate_resource_candidates(
    candidates: list[dict],
    context: TravelAgentContext,
) -> tuple[bool, list[str]]:
    issues = []
    days = context["days"]
    target_count = await calculate_poi_count(days)
    categories = {candidate.get("category") for candidate in candidates}

    if len(candidates) < target_count:
        issues.append(f"POI数量不足：需要至少{target_count}个，当前{len(candidates)}个")
    if "CORE_SIGHTSEEING" not in categories:
        issues.append("缺少核心景点候选")
    if "LOCAL_GASTRONOMY" not in categories:
        issues.append("缺少本地美食候选")
    if days > 1 and "ACCOMMODATION" not in categories:
        issues.append("多天行程缺少住宿候选")

    seen_candidate_keys = set()
    seen_food_brand_keys = set()
    for candidate in candidates:
        name = str(candidate.get("name") or "").strip()
        poi_id = str(candidate.get("id") or "").strip()
        location = str(candidate.get("location") or "").strip()
        category = candidate.get("category")
        if not name or not poi_id or not location:
            issues.append(f"POI字段不完整：{name or poi_id or '未知地点'}")

        candidate_key = _candidate_key(candidate)
        if candidate_key in seen_candidate_keys:
            issues.append(f"POI重复：{name}")
        seen_candidate_keys.add(candidate_key)

        food_brand_key = _food_brand_key(candidate)
        if food_brand_key:
            if food_brand_key in seen_food_brand_keys:
                issues.append(f"同品牌美食重复：{name}")
            seen_food_brand_keys.add(food_brand_key)

        if category == "LOCAL_GASTRONOMY":
            if _is_blocked_chain_food(name):
                issues.append(f"包含连锁快餐：{name}")
            if not _is_destination_local_food(candidate, context["location"]):
                issues.append(f"美食不符合目的地本地特色：{name}")

    return not issues, issues


def _parse_search_plan_output(resp: dict) -> SearchPlanOutput:
    search_plan = resp.get("structured_response")
    if search_plan is None:
        return SearchPlanOutput.model_validate_json(resp["messages"][-1].content)
    if isinstance(search_plan, SearchPlanOutput):
        return search_plan
    return SearchPlanOutput.model_validate(search_plan)


async def _execute_search_plan_task(location: str, task: SearchPlanTask) -> list[dict]:
    pois = await search_poi(city=location, keywords=task.keyword, category=task.category)
    candidates = []
    retain_limit = task.limit * 3
    for raw_poi in pois:
        candidate = _build_resource_candidate_from_raw_poi(
            raw_poi=raw_poi,
            amap_category=task.category,
            search_keyword=task.keyword,
            search_reason=task.reason,
        )
        if candidate is None:
            continue
        candidates.append(candidate)
        if len(candidates) >= retain_limit:
            break
    return candidates


async def _execute_search_plan(location: str, search_plan: SearchPlanOutput) -> list[dict]:
    task_results = await asyncio.gather(
        *[
            _execute_search_plan_task(location=location, task=task)
            for task in search_plan.tasks
        ]
    )
    return [
        candidate
        for candidates in task_results
        for candidate in candidates
    ]


def _parse_location(location: str) -> tuple[float, float] | None:
    try:
        lng, lat = location.split(",", maxsplit=1)
        return float(lng), float(lat)
    except (AttributeError, ValueError):
        return None


def _haversine_meter(from_location: str, to_location: str) -> float:
    start = _parse_location(from_location)
    end = _parse_location(to_location)
    if start is None or end is None:
        return 3000.0

    lng1, lat1 = start
    lng2, lat2 = end
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_mcp_json(result) -> dict:
    if isinstance(result, list) and result:
        text = result[0].get("text") if isinstance(result[0], dict) else None
        if text:
            return json.loads(text)
    if isinstance(result, str):
        return json.loads(result)
    if isinstance(result, dict):
        return result
    return {}


async def _load_amap_route_tools() -> dict:
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.agents.mcp import amap_mcp_session

    tools = await load_mcp_tools(session=amap_mcp_session)
    return {tool.name: tool for tool in tools}


async def _build_commute_item(
    seq: int,
    time_window: str,
    from_poi: dict,
    to_poi: dict,
    route_tools: dict,
    use_route_tool: bool,
) -> dict:
    from_location = from_poi.get("location", "")
    to_location = to_poi.get("location", "")
    estimated_distance = _haversine_meter(from_location, to_location)
    transport_mode = "walking" if estimated_distance < 1500 else "driving"
    distance_meter = estimated_distance
    commute_time_min = max(5, round(estimated_distance / (5000 / 60)))

    if use_route_tool and "maps_distance" in route_tools:
        distance_type = "3" if transport_mode == "walking" else "1"
        try:
            result = await route_tools["maps_distance"].ainvoke(
                {
                    "origins": from_location,
                    "destination": to_location,
                    "type": distance_type,
                }
            )
            data = _extract_mcp_json(result)
            route_result = data.get("results", [{}])[0]
            distance_meter = float(route_result.get("distance", distance_meter))
            duration_seconds = float(route_result.get("duration", commute_time_min * 60))
            commute_time_min = max(1, math.ceil(duration_seconds / 60))
        except Exception:
            logger.exception(
                f"高德路线MCP调用失败: {from_poi.get('name')} -> {to_poi.get('name')}"
            )

    return {
        "seq": seq,
        "time_window": time_window,
        "action": "通勤",
        "transport_mode": transport_mode,
        "distance_meter": round(distance_meter, 1),
        "commute_time_min": commute_time_min,
        "from_poi": from_poi.get("name", ""),
        "to_poi": to_poi.get("name", ""),
    }


def _build_play_item(seq: int, time_window: str, poi: dict, action: str) -> dict:
    return {
        "seq": seq,
        "time_window": time_window,
        "poi_id": poi.get("id", ""),
        "poi_name": poi.get("name", ""),
        "category": poi.get("category", "CORE_SIGHTSEEING"),
        "action": action,
        "duration_hour": poi.get("suggested_duration") or 1.5,
        "cost": poi.get("price"),
        "reason": poi.get("recommend_reason") or "根据地点类型、位置和用户偏好安排。",
        "photo": poi.get("photo", ""),
        "location": poi.get("location", ""),
    }


def _candidate_key(candidate: dict) -> str:
    poi_id = str(candidate.get("id") or "").strip()
    if poi_id:
        return f"id:{poi_id}"

    name = str(candidate.get("name") or "").strip()
    location = str(candidate.get("location") or "").strip()
    return f"name_location:{name}:{location}"


def _pop_unused_candidate(
    groups: dict,
    category: str,
    fallback: list[dict],
    used_candidate_keys: set[str],
    used_food_brand_keys: set[str],
    anchor_location: str | None = None,
) -> dict | None:
    def pop_from(candidates: list[dict]) -> dict | None:
        valid_candidates = []
        for index, candidate in enumerate(candidates):
            candidate_key = _candidate_key(candidate)
            food_brand_key = _food_brand_key(candidate)
            if candidate_key and candidate_key in used_candidate_keys:
                continue
            if food_brand_key and food_brand_key in used_food_brand_keys:
                continue
            valid_candidates.append((index, candidate))

        if not valid_candidates:
            return None

        if anchor_location:
            selected_index, selected_candidate = min(
                valid_candidates,
                key=lambda item: _haversine_meter(anchor_location, item[1].get("location", "")),
            )
        else:
            selected_index, selected_candidate = valid_candidates[0]

        candidates.pop(selected_index)
        candidate_key = _candidate_key(selected_candidate)
        food_brand_key = _food_brand_key(selected_candidate)
        if candidate_key:
            used_candidate_keys.add(candidate_key)
        if food_brand_key:
            used_food_brand_keys.add(food_brand_key)
        return selected_candidate

    candidate = pop_from(groups.get(category) or [])
    if candidate:
        return candidate

    return pop_from(fallback)


async def _build_commute_items_for_day(
    day_pois: list[dict],
    commute_windows: list[str],
    route_tools: dict,
    route_calls_used: int,
) -> tuple[list[dict], int, float]:
    commute_tasks = []
    for index in range(len(day_pois) - 1):
        use_route_tool = route_calls_used < PLANNER_ROUTE_MCP_CALL_LIMIT
        if use_route_tool:
            route_calls_used += 1
        commute_tasks.append(
            _build_commute_item(
                seq=index * 2 + 2,
                time_window=commute_windows[index],
                from_poi=day_pois[index],
                to_poi=day_pois[index + 1],
                route_tools=route_tools,
                use_route_tool=use_route_tool,
            )
        )

    commute_items = await asyncio.gather(*commute_tasks) if commute_tasks else []
    total_distance_meter = sum(commute["distance_meter"] for commute in commute_items)
    return commute_items, route_calls_used, total_distance_meter


def _build_day_schedule(
    day_pois: list[dict],
    commute_items: list[dict],
    play_windows: list[str],
    actions: list[str],
) -> list[dict]:
    schedule = []
    seq = 1
    for index, poi in enumerate(day_pois):
        schedule.append(_build_play_item(seq, play_windows[index], poi, actions[index]))
        seq += 1
        if index < len(commute_items):
            commute = dict(commute_items[index])
            commute["seq"] = seq
            schedule.append(commute)
            seq += 1
    return schedule


def _validate_planner_output(plan: dict, context: TravelAgentContext) -> tuple[bool, list[str]]:
    issues = []
    days = context["days"]
    daily_itinerary = plan.get("daily_itinerary") or []
    if len(daily_itinerary) != days:
        issues.append(f"每日行程数量不匹配：需要{days}天，当前{len(daily_itinerary)}天")

    seen_poi_keys = set()
    seen_food_brand_keys = set()
    for day in daily_itinerary:
        day_number = day.get("day")
        schedule = day.get("schedule") or []
        play_items = [
            item
            for item in schedule
            if item.get("action") != "通勤"
        ]
        commute_items = [
            item
            for item in schedule
            if item.get("action") == "通勤"
        ]

        if not play_items:
            issues.append(f"第{day_number}天没有活动安排")
        if not any(item.get("category") == "CORE_SIGHTSEEING" for item in play_items):
            issues.append(f"第{day_number}天缺少核心景点")
        if not any(item.get("action") == "午餐" for item in play_items):
            issues.append(f"第{day_number}天缺少午餐")
        if not any(item.get("action") == "晚餐" for item in play_items):
            issues.append(f"第{day_number}天缺少晚餐")

        day_distance_meter = sum(
            float(item.get("distance_meter") or 0)
            for item in commute_items
        )
        if day_distance_meter > 50000:
            issues.append(f"第{day_number}天通勤距离过长：{day_distance_meter / 1000:.1f}km")

        for item in play_items:
            poi_name = str(item.get("poi_name") or "").strip()
            poi_id = str(item.get("poi_id") or "").strip()
            location = str(item.get("location") or "").strip()
            if not poi_name or not poi_id or not location:
                issues.append(f"第{day_number}天活动字段不完整：{poi_name or poi_id or '未知地点'}")

            poi_key = poi_id or f"{poi_name}:{location}"
            if poi_key in seen_poi_keys:
                issues.append(f"行程中POI重复：{poi_name}")
            seen_poi_keys.add(poi_key)

            if item.get("category") == "LOCAL_GASTRONOMY":
                candidate = {
                    "category": "LOCAL_GASTRONOMY",
                    "name": poi_name,
                    "tags": [],
                    "location": location,
                    "recommend_reason": item.get("reason", ""),
                }
                food_brand_key = _food_brand_key(candidate)
                if food_brand_key:
                    if food_brand_key in seen_food_brand_keys:
                        issues.append(f"行程中同品牌美食重复：{poi_name}")
                    seen_food_brand_keys.add(food_brand_key)
                if _is_blocked_chain_food(poi_name):
                    issues.append(f"行程包含连锁快餐：{poi_name}")
                if not _is_destination_local_food(candidate, context["location"]):
                    issues.append(f"行程美食不符合目的地本地特色：{poi_name}")

    return not issues, issues


def _trip_date(start_date: str | None, day_index: int) -> str | None:
    if not start_date:
        return None

    base = datetime.strptime(start_date, "%Y-%m-%d").date()
    return (base + timedelta(days=day_index)).strftime("%Y-%m-%d")


async def _build_deterministic_plan(context: TravelAgentContext, candidates: list[dict]) -> dict:
    route_tools = await _load_amap_route_tools()
    route_calls_used = 0
    groups = {
        "CORE_SIGHTSEEING": [],
        "LOCAL_GASTRONOMY": [],
        "CITY_LEISURE": [],
        "ACCOMMODATION": [],
    }
    for candidate in candidates:
        groups.setdefault(candidate.get("category"), []).append(candidate)

    fallback = [candidate for candidate in candidates]
    used_candidate_keys = set()
    used_food_brand_keys = set()
    days = context["days"]
    daily_itinerary = []
    total_distance_meter = 0.0

    for day_index in range(days):
        morning = _pop_unused_candidate(
            groups, "CORE_SIGHTSEEING", fallback, used_candidate_keys, used_food_brand_keys
        )
        lunch = _pop_unused_candidate(
            groups,
            "LOCAL_GASTRONOMY",
            fallback,
            used_candidate_keys,
            used_food_brand_keys,
            anchor_location=morning.get("location") if morning else None,
        )
        afternoon = _pop_unused_candidate(
            groups,
            "CITY_LEISURE",
            fallback,
            used_candidate_keys,
            used_food_brand_keys,
            anchor_location=lunch.get("location") if lunch else None,
        ) or _pop_unused_candidate(
            groups,
            "CORE_SIGHTSEEING",
            fallback,
            used_candidate_keys,
            used_food_brand_keys,
            anchor_location=lunch.get("location") if lunch else None,
        )
        dinner = _pop_unused_candidate(
            groups,
            "LOCAL_GASTRONOMY",
            fallback,
            used_candidate_keys,
            used_food_brand_keys,
            anchor_location=afternoon.get("location") if afternoon else None,
        )
        day_pois = [poi for poi in [morning, lunch, afternoon, dinner] if poi]

        play_windows = ["09:00-11:00", "11:30-12:40", "14:00-16:00", "18:00-19:30"]
        commute_windows = ["11:00-11:30", "12:40-14:00", "16:00-18:00"]
        actions = ["浏览", "午餐", "浏览", "晚餐"]

        commute_items, route_calls_used, day_distance_meter = await _build_commute_items_for_day(
            day_pois=day_pois,
            commute_windows=commute_windows,
            route_tools=route_tools,
            route_calls_used=route_calls_used,
        )
        total_distance_meter += day_distance_meter
        schedule = _build_day_schedule(
            day_pois=day_pois,
            commute_items=commute_items,
            play_windows=play_windows,
            actions=actions,
        )

        daily_itinerary.append(
            {
                "day": day_index + 1,
                "date": _trip_date(context.get("start_date"), day_index),
                "weather_label": "UNKNOWN",
                "schedule": schedule,
            }
        )

    tags = list(context.get("preferences") or [])
    return {
        "trip_overview": {
            "title": f"{context['location']}{days}日旅行计划",
            "total_distance_km": round(total_distance_meter / 1000, 1),
            "tags": tags,
        },
        "daily_itinerary": daily_itinerary,
    }


async def manager_agent_node(state: TravelAgentState, runtime: Runtime[TravelAgentContext]):
    """
    manager agent节点
    :param state: travel agent状态
    :param runtime: travel agent运行时
    :return: travel agent状态中需要更新的部分
    """
    logger.info("进入manager_agent_node")
    agent = ManagerAgentBuilder().build()
    is_just_start: bool = state["is_just_start"]
    context = runtime.context

    if is_just_start:
        # travel_agent 刚启动

        first_msg = _build_initial_message(context)

        resp = await agent.ainvoke(
            input={
                "messages": [SystemMessage(content=first_msg)]
            }
        )
        manager_output = ManagerAgentOutput.parse_response(resp)
        return {
            "current_phase": "manager_agent",
            "next_phase": manager_output.next_to,
            "is_just_start": False,
            "messages": [
                resp["messages"][0],
                ManagerAgentMessage(content=manager_output.model_dump_json())
            ]

            # "manager_agent_response": resp["structured_response"].model_dump(),
            # "messages": [{"role": "user", "content": first_msg}]
        }

    last_phase = state["current_phase"]  # travel agent运行的上一个阶段
    if last_phase == "environment_agent":
        weather_msg = state["messages"][-1].content
        msg = f"上一个阶段是environment_agent,environment_agent查询到的天气和生成的旅行建议如下：\n{weather_msg}\n\n，你现在要做的是对environment agent生成的内容进行质检。"
        resp = await agent.ainvoke(
            input={
                "messages": [SystemMessage(content=msg)]
            },
            config={"recursion_limit": 12},
        )
        manager_output = ManagerAgentOutput.parse_response(resp)
        return {
            "current_phase": "manager_agent",
            "next_phase": manager_output.next_to,
            "is_need_correct": True if manager_output.next_to == "environment_agent" else False,
            "need_correct_content": weather_msg if manager_output.next_to == "environment_agent" else None,
            # "is_just_start": False,
            "messages": [
                resp["messages"][0],
                ManagerAgentMessage(content=manager_output.model_dump_json())
            ]
        }

    if last_phase == "resource_agent":
        candidates = json.loads(state["messages"][-1].content)  # 解析resource agent返回的poi列表
        is_valid, issues = await _validate_resource_candidates(candidates, context)
        if not is_valid:
            reason = "；".join(issues)
            resource_attempt_count = sum(
                1
                for msg in state["messages"]
                if isinstance(msg, ResourceAgentMessage)
            )
            if resource_attempt_count >= 2:
                logger.warning(f"resource agent返回的POI列表质检仍不通过，已达到补搜上限: {reason}")
                return {
                    "current_phase": "manager_agent",
                    "next_phase": "planner_agent",
                    "is_need_correct": False,
                    "need_correct_content": None,
                    "messages": [
                        SystemMessage(content=f"resource agent返回的POI列表质检仍不通过，已达到补搜上限: {reason}"),
                        ManagerAgentMessage(
                            content=ManagerAgentOutput(
                                next_to="planner_agent",
                                reason=f"POI质检仍有问题但已达到补搜上限，继续生成可用行程：{reason}",
                            ).model_dump_json()
                        )
                    ]
                }

            return {
                "current_phase": "manager_agent",
                "next_phase": "resource_agent",
                "is_need_correct": True,
                "need_correct_content": reason,
                "messages": [
                    SystemMessage(content="resource agent返回的POI列表质检不通过"),
                    ManagerAgentMessage(
                        content=ManagerAgentOutput(next_to="resource_agent", reason=reason).model_dump_json()
                    )
                ]
            }

        return {
            "current_phase": "manager_agent",
            "next_phase": "planner_agent",
            "is_need_correct": False,
            "need_correct_content": None,
            "messages": [
                SystemMessage(content="请对resource agent返回的poi列表进行质检"),
                ManagerAgentMessage(
                    content=ManagerAgentOutput(next_to="planner_agent", reason="质检通过").model_dump_json())
            ]
        }

    if last_phase == "planner_agent":
        planner_output = state["messages"][-1].content
        planner_plan = json.loads(planner_output)
        is_valid, issues = _validate_planner_output(planner_plan, context)
        if not is_valid:
            reason = "；".join(issues)
            logger.warning(f"planner agent返回的最终规划结果质检不通过: {reason}")
            return {
                "current_phase": "manager_agent",
                "next_phase": "finish",
                "is_need_correct": False,
                "need_correct_content": None,
                "messages": [
                    SystemMessage(content=f"planner agent返回的最终规划结果质检不通过: {reason}"),
                    ManagerAgentMessage(
                        content=ManagerAgentOutput(next_to="finish", reason=f"质检不通过但已生成可用行程：{reason}").model_dump_json()
                    ),
                    ManagerAgentMessage(content=planner_output)
                ]
            }

        return {
            "current_phase": "manager_agent",
            "next_phase": "finish",
            "is_need_correct": False,
            "need_correct_content": None,
            "messages": [
                SystemMessage(content="请对planner agent返回的最终规划结果进行质检"),
                ManagerAgentMessage(
                    content=ManagerAgentOutput(next_to="finish", reason="质检通过").model_dump_json()),
                ManagerAgentMessage(content=planner_output)
            ]
        }


def _build_initial_message(context: TravelAgentContext) -> str:
    """
    构建初始消息
    :param context: 旅行智能体上下文
    :return: 初始消息
    """
    location = context["location"]
    days = context["days"]
    today = context.get("today", None)
    start_date = context.get("start_date", None)
    end_date = context.get("end_date", None)
    preferences = context.get("preferences", None)
    # 用户想去上海游玩3天，游玩时间是从2026-01-11到2026-01-13，用户的旅游偏好是历史、文化，当前日期是2026-01-11。请根据用户的旅游信息和偏好，制定一个旅游计划。
    parts = [f"用户想去{location}游玩{days}天"]
    if start_date and end_date:
        parts.append(f"游玩时间是从{start_date}到{end_date}")
    if preferences:
        parts.append(f"用户的旅游偏好是{'、'.join(preferences)}")
    if today:
        parts.append(f"当前日期是{today}")

    return ", ".join(parts) + "。" + "请根据用户的旅游信息和偏好，制定一个旅游计划。"


async def environment_agent_node(state: TravelAgentState, runtime: Runtime[TravelAgentContext]):
    """
    environment agent节点
    :param state: travel agent状态
    :param runtime: travel agent运行时
    :return: travel agent状态中需要更新的部分
    """
    logger.info("进入environment_agent_node")

    agent = EnvironmentAgentBuilder().build()

    context = runtime.context
    location = context["location"]
    start_date = context["start_date"]
    end_date = context["end_date"]
    is_need_correct = state["is_need_correct"]
    if not is_need_correct:
        # 不需要修正，直接查询天气
        msg = f"用户想去{location}旅游，请你查询{location}从{start_date}到{end_date}的天气情况。"
        resp = await agent.ainvoke(
            input={
                "messages": [SystemMessage(content=msg)]
            }
        )
        last_msg = resp["messages"][-1].model_dump()
        last_msg["type"] = "environment_agent"

        return {
            "current_phase": "environment_agent",
            "next_phase": "manager_agent",
            "messages": [
                resp["messages"][0],
                EnvironmentAgentMessage(**last_msg),
            ]
        }

    # 需要修正
    state_last_msg = json.loads(state["messages"][-1].content)
    reason = state_last_msg["reason"]
    raw_content = state["need_correct_content"]
    msg = f"你做的旅游建议存在以下问题：\n{reason}\n\n你生成的旅游建议和你查询到的天气信息如下：\n{raw_content}\n\n请根据天气信息和存在的问题，重新生成一个旅游建议。"
    resp = await agent.ainvoke(
        input={
            "messages": [SystemMessage(content=msg)]
        }
    )
    last_msg = resp["messages"][-1].model_dump()
    last_msg["type"] = "environment_agent"
    return {
        "current_phase": "environment_agent",
        "next_phase": "manager_agent",
        "is_need_correct": False,
        "need_correct_content": None,
        "messages": [
            resp["messages"][0],
            EnvironmentAgentMessage(**last_msg),
        ]
    }


async def resource_agent_node(state: TravelAgentState, runtime: Runtime[TravelAgentContext]):
    """
    resource agent节点
    :param state: travel agent状态
    :param runtime: travel agent运行时
    :return: travel agent状态中需要更新的部分
    """
    logger.info("进入resource_agent_node")

    context = runtime.context
    location = context["location"]
    days = context["days"]
    preferences = context.get("preferences", None)
    correction_reason = state.get("need_correct_content") if state["is_need_correct"] else None
    agent = await ResourceAgentBuilder().build()
    target_count = await calculate_poi_count(days)
    msg = (
        f"请为{location}{days}天旅行生成POI搜索计划。"
        f"用户偏好：{preferences or '无'}。"
        f"目标数量：至少{target_count}个。"
        "计划需要覆盖核心景点、本地美食、城市休闲和住宿。"
        "美食搜索关键词必须体现目的地本地特色，不要用外地菜系代表目的地。"
    )
    if correction_reason:
        msg += f"上一次POI质检失败原因：{correction_reason}。请针对这些问题重新生成搜索计划。"

    resp = await agent.ainvoke(
        input={
            "messages": [SystemMessage(content=msg)]
        },
        config={"recursion_limit": 8},
    )
    search_plan = _parse_search_plan_output(resp)
    raw_candidates = await _execute_search_plan(location=location, search_plan=search_plan)
    candidates = _sanitize_resource_candidates(
        candidates=raw_candidates,
        location=location,
    )

    if len(candidates) < target_count:
        retry_msg = (
            f"上一次搜索结果经过后端硬规则过滤后只剩{len(candidates)}个，"
            f"未达到目标数量{target_count}。请继续搜索{location}POI补充候选，"
            "重点补足缺失的景点、本地美食、城市休闲和住宿类型。"
            "只输出补充搜索计划，不要重复已给出的地点或同品牌美食分店。"
        )
        retry_resp = await agent.ainvoke(
            input={
                "messages": [
                    SystemMessage(content=msg),
                    HumanMessage(
                        content=f"{retry_msg}\n\n已有候选：{json.dumps(candidates, ensure_ascii=False)}"
                    ),
                ]
            },
            config={"recursion_limit": 8},
        )
        retry_plan = _parse_search_plan_output(retry_resp)
        raw_candidates.extend(await _execute_search_plan(location=location, search_plan=retry_plan))
        candidates = _sanitize_resource_candidates(
            candidates=raw_candidates,
            location=location,
        )

    return {
        "current_phase": "resource_agent",
        "next_phase": "manager_agent",
        "is_need_correct": False,
        "need_correct_content": None,
        "messages": [
            SystemMessage(content="resource_agent已生成搜索计划，后端并发搜索POI并完成硬规则过滤"),
            ResourceAgentMessage(content=json.dumps(candidates, ensure_ascii=False)),
        ]
    }


async def planner_agent_node(state: TravelAgentState, runtime: Runtime[TravelAgentContext]):
    """
    planner agent节点
    :param state: travel agent状态
    :param runtime: travel agent运行时
    :return: travel agent状态中需要更新的部分
    """
    logger.info("进入planner_agent_node")
    context = runtime.context

    candidates = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, ResourceAgentMessage):
            candidates = json.loads(msg.content)
            break

    plan = await _build_deterministic_plan(context, candidates)
    res = json.dumps(plan, ensure_ascii=False)
    return {
        "current_phase": "planner_agent",
        "next_phase": "manager_agent",
        "is_need_correct": False,
        "need_correct_content": None,
        "messages": [
            SystemMessage(content="planner_agent已完成确定性行程生成，并使用高德路线MCP计算通勤"),
            PlannerAgentMessage(content=res),
        ]
    }


async def build_travel_agent():
    """
    构建旅行智能体
    :return: None
    """
    global travel_agent
    if travel_agent is None:
        logger.info("正在构建 TravelAgent ...")
        await init_checkpointer()

        # create_mcp_client()

        graph = StateGraph(state_schema=TravelAgentState, context_schema=TravelAgentContext)

        graph.add_node(manager_agent_node, "manager_agent_node")
        graph.add_node(environment_agent_node, "environment_agent_node")
        graph.add_node(resource_agent_node, "resource_agent_node")
        graph.add_node(planner_agent_node, "planner_agent_node")

        graph.add_edge(START, "manager_agent_node")
        graph.add_conditional_edges(
            "manager_agent_node",
            lambda state: state["next_phase"],
            {
                "environment_agent": "environment_agent_node",
                "resource_agent": "resource_agent_node",
                "planner_agent": "planner_agent_node",
                "finish": END,
            }

        )

        graph.add_edge("environment_agent_node", "manager_agent_node")
        graph.add_edge("resource_agent_node", "manager_agent_node")
        graph.add_edge("planner_agent_node", "manager_agent_node")
        from app.agents.memory import checkpointer

        travel_agent = graph.compile(checkpointer=checkpointer)

        logger.info("TravelAgent 构建完成")
