import json
import uuid
from datetime import date

from langchain_core.messages import SystemMessage
from langchain_core.tools.base import ToolException
from langgraph.errors import GraphRecursionError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import TravelAgentContext

from app.core.enums import StatusInfo
from app.core.exceptions import BusinessException
from app.models.base import datetime_to_unix
from app.models.travel import Trip, TripVersion
from app.schemas.request.travel import PlanTravelRequest
from loguru import logger
import time

from app.schemas.response.stream import (
    AgentStepEvent,
    DoneEvent,
    ErrorEvent,
    StartEvent,
    StreamResponse,
)


NODE_AGENT_MAP = {
    "manager_agent_node": "manager_agent",
    "environment_agent_node": "environment_agent",
    "resource_agent_node": "resource_agent",
    "planner_agent_node": "planner_agent",
}

NEXT_PHASE_AGENT_MAP = {
    "environment_agent": "environment_agent",
    "resource_agent": "resource_agent",
    "planner_agent": "planner_agent",
}

AGENT_RUNNING_MESSAGES = {
    "manager_agent": "正在分析旅行需求并决定下一步",
    "environment_agent": "正在查询天气并生成出行建议",
    "resource_agent": "正在筛选景点、美食和住宿",
    "planner_agent": "正在生成每日行程计划",
}

AGENT_COMPLETED_MESSAGES = {
    "manager_agent": "需求分析和质量检查已完成",
    "environment_agent": "天气查询和出行建议已完成",
    "resource_agent": "POI 资源筛选已完成",
    "planner_agent": "每日行程计划已生成",
}


class TravelService:
    """
    旅行service,实现旅行相关功能
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def list_trips(
        self,
        user_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> dict:
        """
        查询当前用户的行程列表。
        """
        conditions = [
            Trip.user_id == user_id,
            Trip.deleted_at.is_(None),
        ]
        if status:
            conditions.append(Trip.status == status)

        total_result = await self.db_session.execute(
            select(func.count()).select_from(Trip).where(*conditions)
        )
        total = total_result.scalar_one()

        result = await self.db_session.execute(
            select(Trip)
            .where(*conditions)
            .order_by(Trip.updated_at.desc(), Trip.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        trips = result.scalars().all()

        return {
            "items": [
                {
                    "id": trip.id,
                    "title": trip.title,
                    "location": trip.location,
                    "days": trip.days,
                    "start_date": trip.start_date,
                    "end_date": trip.end_date,
                    "status": trip.status,
                    "latest_version_no": trip.latest_version_no,
                    "created_at": datetime_to_unix(trip.created_at),
                    "updated_at": datetime_to_unix(trip.updated_at),
                }
                for trip in trips
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    async def get_trip_detail(self, user_id: str, trip_id: str) -> dict:
        """
        查询当前用户的行程详情。
        """
        trip = await self._get_active_trip(trip_id, user_id)

        latest_version = None
        if trip.latest_version_no > 0:
            version_result = await self.db_session.execute(
                select(TripVersion).where(
                    TripVersion.trip_id == trip.id,
                    TripVersion.version_no == trip.latest_version_no,
                )
            )
            version = version_result.scalar_one_or_none()
            if version is not None:
                latest_version = {
                    "version_no": version.version_no,
                    "source": version.source,
                    "content": version.content,
                    "created_at": datetime_to_unix(version.created_at),
                }

        return {
            "id": trip.id,
            "title": trip.title,
            "location": trip.location,
            "days": trip.days,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "preferences": trip.preferences,
            "status": trip.status,
            "latest_version": latest_version,
            "created_at": datetime_to_unix(trip.created_at),
            "updated_at": datetime_to_unix(trip.updated_at),
        }

    async def delete_trip(self, user_id: str, trip_id: str) -> dict:
        """
        软删除当前用户的行程。
        """
        trip = await self._get_active_trip(trip_id, user_id)
        trip.status = "deleted"
        trip.mark_deleted()
        await self.db_session.flush()
        return {"deleted": True}

    async def plan_travel(self, request: PlanTravelRequest, user_id: str):
        """
        旅行规划功能实现函数
        :param request: 旅行规划请求模型
        :param user_id: 当前用户ID
        :return:
        """
        location = request.location  # 目的地
        days = request.days  # 计划天数
        start_date = request.start_date if request.start_date else None  # 计划开始日期
        end_date = request.end_date if request.end_date else None  # 计划结束日期
        preferences = request.preferences if request.preferences else None  # 用户偏好

        thread_id = f"thread_{str(uuid.uuid4()).replace('-', '')}"
        trip = None

        try:
            trip = await self._create_trip(request, user_id, thread_id)
            await self.db_session.commit()
            logger.info(f"本次旅游规划 user_id={user_id}, trip_id={trip.id}, thread_id={thread_id}")

            yield StreamResponse(
                event="start",
                data=StartEvent(
                    thread_id=thread_id,
                    trip_id=trip.id,
                    start_at=int(time.time()),
                ),
            )

            yield self._agent_step("manager_agent", "running")

            from app.agents.graph import build_travel_agent, travel_agent

            if travel_agent is None:
                await build_travel_agent()

            async for chunk in travel_agent.astream(
                    {
                        "messages": [SystemMessage(content="开始规划")],
                        "is_just_start": True,
                        "is_need_correct": False,
                        "need_correct_content": None,

                    },
                    stream_mode="updates",
                    config={"configurable": {"thread_id": thread_id}},
                    context=TravelAgentContext(location=location, days=days,
                                               today=date.today().strftime("%Y-%m-%d") if start_date else None,
                                               preferences=preferences.split(",") if preferences else None,
                                               start_date=start_date, end_date=end_date)
            ):
                # chunk 格式: {"node_name": {state_update}}
                for node_name, state_update in chunk.items():
                    logger.info(f"当前node: {node_name}, 更新的state: {state_update}")

                    agent = NODE_AGENT_MAP.get(node_name)
                    if agent:
                        yield self._agent_step(agent, "completed")

                    if node_name == "manager_agent_node":
                        next_phase = state_update["next_phase"]
                        next_agent = NEXT_PHASE_AGENT_MAP.get(next_phase)
                        if next_agent:
                            yield self._agent_step(next_agent, "running")

                        if next_phase == "finish":
                            logger.info("本轮规划完成")

                            final_output = state_update["messages"][-1].content
                            content = json.loads(final_output)
                            version_no = await self._complete_trip(trip, content)
                            await self.db_session.commit()

                            logger.info(f"规划结果: {final_output}")
                            yield StreamResponse(
                                event="done",
                                data=DoneEvent(
                                    trip_id=trip.id,
                                    thread_id=thread_id,
                                    version_no=version_no,
                                    end_at=int(time.time()),
                                ),
                            )
                            return

            await self._fail_trip(trip, "旅行规划流程未正常完成")
            await self.db_session.commit()
            yield StreamResponse(
                event="error",
                data=ErrorEvent(
                    trip_id=trip.id,
                    thread_id=thread_id,
                    code=StatusInfo.TRAVEL_PLAN_QUALITY_FAILED.value[1],
                    error_code="PLAN_QUALITY_FAILED",
                    error_message=StatusInfo.TRAVEL_PLAN_QUALITY_FAILED.value[2],
                    failed_agent=None,
                    end_at=int(time.time()),
                ),
            )
        except Exception as exc:
            logger.exception(f"[旅行规划接口] 规划失败: {str(exc)}")
            if trip is not None:
                try:
                    await self._fail_trip(trip, str(exc))
                    await self.db_session.commit()
                except Exception as db_exc:
                    await self.db_session.rollback()
                    logger.exception(f"[旅行规划接口] 失败状态写入数据库失败: {str(db_exc)}")

            status, error_code = self._classify_plan_error(exc)
            yield StreamResponse(
                event="error",
                data=ErrorEvent(
                    trip_id=trip.id if trip is not None else "",
                    thread_id=thread_id,
                    code=status.value[1],
                    error_code=error_code,
                    error_message=status.value[2],
                    failed_agent=None,
                    end_at=int(time.time()),
                ),
            )

    @staticmethod
    def _classify_plan_error(exc: Exception) -> tuple[StatusInfo, str]:
        if isinstance(exc, ToolException):
            return StatusInfo.TRAVEL_TOOL_CALL_FAILED, "TOOL_CALL_FAILED"
        if isinstance(exc, GraphRecursionError):
            return StatusInfo.TRAVEL_PLAN_QUALITY_FAILED, "PLAN_QUALITY_FAILED"
        if isinstance(exc, json.JSONDecodeError):
            return StatusInfo.TRAVEL_AGENT_OUTPUT_INVALID, "AGENT_OUTPUT_INVALID"
        return StatusInfo.TRAVEL_INTERNAL_ERROR, "INTERNAL_ERROR"

    async def _create_trip(
        self,
        request: PlanTravelRequest,
        user_id: str,
        thread_id: str,
    ) -> Trip:
        trip = Trip(
            user_id=user_id,
            title=f"{request.location}{request.days}日旅行计划",
            location=request.location,
            days=request.days,
            start_date=self._parse_date(request.start_date),
            end_date=self._parse_date(request.end_date),
            preferences=self._parse_preferences(request.preferences),
            status="planning",
            latest_version_no=0,
            thread_id=thread_id,
        )
        self.db_session.add(trip)
        await self.db_session.flush()
        return trip

    async def _complete_trip(self, trip: Trip, content: dict) -> int:
        version_no = trip.latest_version_no + 1
        version = TripVersion(
            trip_id=trip.id,
            version_no=version_no,
            source="initial",
            content=content,
        )
        trip.status = "completed"
        trip.latest_version_no = version_no
        trip.error_message = None

        title = content.get("trip_overview", {}).get("title")
        if title:
            trip.title = title

        self.db_session.add(version)
        await self.db_session.flush()
        return version_no

    async def _fail_trip(self, trip: Trip, error_message: str) -> None:
        trip.status = "failed"
        trip.error_message = error_message[:2000]
        await self.db_session.flush()

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        return date.fromisoformat(value)

    @staticmethod
    def _parse_preferences(value: str | None) -> list[str] | None:
        if not value:
            return None
        preferences = [item.strip() for item in value.split(",") if item.strip()]
        return preferences or None

    async def _get_active_trip(self, trip_id: str, user_id: str) -> Trip:
        result = await self.db_session.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.deleted_at.is_(None),
            )
        )
        trip = result.scalar_one_or_none()
        if trip is None:
            raise BusinessException(StatusInfo.TRIP_NOT_FOUND)
        if trip.user_id != user_id:
            raise BusinessException(StatusInfo.TRIP_FORBIDDEN)
        return trip

    @staticmethod
    def _agent_step(agent: str, status: str) -> StreamResponse:
        messages = {
            "running": AGENT_RUNNING_MESSAGES,
            "completed": AGENT_COMPLETED_MESSAGES,
        }
        return StreamResponse(
            event="agent_step",
            data=AgentStepEvent(
                agent=agent,
                status=status,
                message=messages[status][agent],
            ),
        )
