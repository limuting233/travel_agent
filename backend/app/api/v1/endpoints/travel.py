from fastapi import APIRouter, Depends

from loguru import logger
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.stream_utils import sse_generator
from app.models.user import User
from app.schemas.request.travel import PlanTravelRequest
from app.services.travel import TravelService

router = APIRouter()


@router.post("/plan")
async def plan_travel(
    request: PlanTravelRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    旅行规划接口
    :param request: 旅行规划请求模型
    :param current_user: 当前登录用户
    :return:
    """
    logger.info(f"[旅行规划接口] user_id={current_user.id}, 请求参数: {request}")

    travel_service = TravelService(db_session)
    return StreamingResponse(
        content=sse_generator(travel_service.plan_travel(request, current_user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
