from typing import Literal

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response.base import BaseResponse, success
from app.schemas.response.trip import (
    TripDeleteResponse,
    TripDetailResponse,
    TripListResponse,
)
from app.services.travel import TravelService

router = APIRouter()


@router.get("", response_model=BaseResponse[TripListResponse])
async def list_trips(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Literal["planning", "completed", "failed"] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    查询当前用户的行程列表。
    """
    logger.info(
        f"[行程列表接口] user_id={current_user.id}, page={page}, "
        f"page_size={page_size}, status={status}"
    )

    travel_service = TravelService(db_session)
    data = await travel_service.list_trips(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )
    return success(TripListResponse(**data))


@router.get("/{trip_id}", response_model=BaseResponse[TripDetailResponse])
async def get_trip_detail(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    查询当前用户的行程详情。
    """
    logger.info(f"[行程详情接口] user_id={current_user.id}, trip_id={trip_id}")

    travel_service = TravelService(db_session)
    data = await travel_service.get_trip_detail(
        user_id=current_user.id,
        trip_id=trip_id,
    )
    return success(TripDetailResponse(**data))


@router.delete("/{trip_id}", response_model=BaseResponse[TripDeleteResponse])
async def delete_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    软删除当前用户的行程。
    """
    logger.info(f"[删除行程接口] user_id={current_user.id}, trip_id={trip_id}")

    travel_service = TravelService(db_session)
    data = await travel_service.delete_trip(
        user_id=current_user.id,
        trip_id=trip_id,
    )
    return success(TripDeleteResponse(**data))
