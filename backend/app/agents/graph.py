import json
import math
from datetime import date, datetime, timedelta

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

from app.agents.context import TravelAgentContext
from app.agents.environment_agent.agent import EnvironmentAgentBuilder
from app.agents.manager_agent.agent import ManagerAgentBuilder, ManagerAgentOutput
# from app.agents.mcp import create_mcp_client
from app.agents.memory import init_checkpointer
from app.agents.message import ManagerAgentMessage, EnvironmentAgentMessage, ResourceAgentMessage, PlannerAgentMessage
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

RESOURCE_SEARCH_LIMIT = 6
PLANNER_ROUTE_MCP_CALL_LIMIT = 6


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


def _build_candidate(raw_poi: dict, amap_category: str, preferences: list[str] | None) -> dict | None:
    rating = _to_float(raw_poi.get("评分（0-5分）"))
    category = RESOURCE_CATEGORY_MAP[amap_category]

    if rating is not None and rating < 3.8 and category != "ACCOMMODATION":
        return None

    tags = []
    raw_tags = raw_poi.get("标签")
    if raw_tags:
        tags.extend([tag.strip() for tag in str(raw_tags).split(";") if tag.strip()])
    if preferences:
        tags.extend(preferences)

    name = raw_poi.get("名称", "")
    reason_parts = []
    if rating is not None:
        reason_parts.append(f"高德评分{rating:g}")
    reason_parts.append("与用户偏好和行程类型匹配")

    return {
        "id": raw_poi.get("id", ""),
        "name": name,
        "category": category,
        "tags": list(dict.fromkeys(tags)) or [amap_category],
        "location": raw_poi.get("经纬度（经度,纬度）", ""),
        "rating": rating,
        "price": _to_float(raw_poi.get("人均消费（元/人）")),
        "open_time": raw_poi.get("营业时间（每周）", "") or "",
        "suggested_duration": _suggested_duration(category),
        "photo": raw_poi.get("照片URL") or "",
        "recommend_reason": "，".join(reason_parts) + "。",
    }


async def _collect_resource_candidates(
    location: str,
    days: int,
    preferences: list[str] | None,
) -> list[dict]:
    target_count = await calculate_poi_count(days)
    preference_text = " ".join(preferences or [])
    food_keyword = preference_text if preference_text else "本地美食"

    search_plan = [
        ("风景名胜", "景点", max(days * 2, 2)),
        ("科教文", "博物馆", max(days, 1)),
        ("美食", food_keyword, max(days * 2, 2)),
        ("购物", "商圈", max(days, 1)),
        ("住宿", "酒店", 1),
        ("娱乐", "夜景", max(days, 1)),
    ]

    candidates = []
    seen_ids = set()
    for amap_category, keyword, category_limit in search_plan[:RESOURCE_SEARCH_LIMIT]:
        category_count = 0
        pois = await search_poi(city=location, keywords=keyword, category=amap_category)
        for raw_poi in pois:
            poi_id = raw_poi.get("id")
            if not poi_id or poi_id in seen_ids:
                continue
            candidate = _build_candidate(raw_poi, amap_category, preferences)
            if candidate is None:
                continue
            seen_ids.add(poi_id)
            candidates.append(candidate)
            category_count += 1
            if category_count >= category_limit:
                break
        if len(candidates) >= target_count:
            break

    logger.info(f"resource_agent确定性搜索完成，POI数量: {len(candidates)}, 目标数量: {target_count}")
    return candidates[:target_count]


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
    route_call_state: dict,
) -> dict:
    from_location = from_poi.get("location", "")
    to_location = to_poi.get("location", "")
    estimated_distance = _haversine_meter(from_location, to_location)
    transport_mode = "walking" if estimated_distance < 1500 else "driving"
    distance_meter = estimated_distance
    commute_time_min = max(5, round(estimated_distance / (5000 / 60)))

    if route_call_state["count"] < PLANNER_ROUTE_MCP_CALL_LIMIT and "maps_distance" in route_tools:
        route_call_state["count"] += 1
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


def _pop_candidate(groups: dict, category: str, fallback: list[dict]) -> dict | None:
    if groups.get(category):
        return groups[category].pop(0)
    return fallback.pop(0) if fallback else None


def _trip_date(start_date: str | None, day_index: int) -> str:
    if start_date:
        base = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        base = date.today()
    return (base + timedelta(days=day_index)).strftime("%Y-%m-%d")


async def _build_deterministic_plan(context: TravelAgentContext, candidates: list[dict]) -> dict:
    route_tools = await _load_amap_route_tools()
    route_call_state = {"count": 0}
    groups = {
        "CORE_SIGHTSEEING": [],
        "LOCAL_GASTRONOMY": [],
        "CITY_LEISURE": [],
        "ACCOMMODATION": [],
    }
    for candidate in candidates:
        groups.setdefault(candidate.get("category"), []).append(candidate)

    fallback = [candidate for candidate in candidates]
    days = context["days"]
    daily_itinerary = []
    total_distance_meter = 0.0

    for day_index in range(days):
        morning = _pop_candidate(groups, "CORE_SIGHTSEEING", fallback)
        lunch = _pop_candidate(groups, "LOCAL_GASTRONOMY", fallback)
        afternoon = _pop_candidate(groups, "CITY_LEISURE", fallback) or _pop_candidate(groups, "CORE_SIGHTSEEING", fallback)
        dinner = _pop_candidate(groups, "LOCAL_GASTRONOMY", fallback)
        hotel = groups["ACCOMMODATION"][0] if groups["ACCOMMODATION"] else None
        day_pois = [poi for poi in [morning, lunch, afternoon, dinner, hotel] if poi]

        schedule = []
        play_windows = ["09:00-11:00", "11:30-12:40", "14:00-16:00", "18:00-19:30", "20:00-21:00"]
        commute_windows = ["11:00-11:30", "12:40-14:00", "16:00-18:00", "19:30-20:00"]
        actions = ["浏览", "午餐", "浏览", "晚餐", "住宿"]

        seq = 1
        for index, poi in enumerate(day_pois):
            schedule.append(_build_play_item(seq, play_windows[index], poi, actions[index]))
            seq += 1
            if index < len(day_pois) - 1:
                commute = await _build_commute_item(
                    seq=seq,
                    time_window=commute_windows[index],
                    from_poi=poi,
                    to_poi=day_pois[index + 1],
                    route_tools=route_tools,
                    route_call_state=route_call_state,
                )
                total_distance_meter += commute["distance_meter"]
                schedule.append(commute)
                seq += 1

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
        # todo 对poi列表进行质检
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
        # todo 对最终规划结果进行质检
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
    is_need_correct = state["is_need_correct"]
    if not is_need_correct:
        candidates = await _collect_resource_candidates(
            location=location,
            days=days,
            preferences=preferences,
        )

        return {
            "current_phase": "resource_agent",
            "next_phase": "manager_agent",
            "messages": [
                SystemMessage(content="resource_agent已完成确定性POI搜索"),
                ResourceAgentMessage(content=json.dumps(candidates, ensure_ascii=False)),
            ]
        }
    # todo 对poi列表进行质检不通过，需要重新查询poi


async def planner_agent_node(state: TravelAgentState, runtime: Runtime[TravelAgentContext]):
    """
    planner agent节点
    :param state: travel agent状态
    :param runtime: travel agent运行时
    :return: travel agent状态中需要更新的部分
    """
    logger.info("进入planner_agent_node")
    context = runtime.context

    if not state["is_need_correct"]:
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
            "messages": [
                SystemMessage(content="planner_agent已完成确定性行程生成，并使用高德路线MCP计算通勤"),
                PlannerAgentMessage(content=res),
            ]
        }
    # todo 对planner_agent的输出进行质检不通过，需要重新规划


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
