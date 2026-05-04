from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.request.auth import LoginRequest, RegisterRequest
from app.schemas.response.auth import CurrentUserResponse, LoginResponse
from app.schemas.response.base import BaseResponse, success
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=BaseResponse[None])
async def register(
    request: RegisterRequest,
    db_session: AsyncSession = Depends(get_db),
):
    """
    用户注册接口
    """
    logger.info(f"[注册接口] username={request.username}")

    auth_service = AuthService(db_session)
    await auth_service.register(request)
    return success()


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db_session: AsyncSession = Depends(get_db),
):
    """
    用户登录接口
    """
    logger.info(f"[登录接口] username={request.username}")

    auth_service = AuthService(db_session)
    data = await auth_service.login(request)
    return success(LoginResponse(**data))


@router.get("/me", response_model=BaseResponse[CurrentUserResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    当前用户接口
    """
    logger.info(
        f"[当前用户接口] user_id={current_user.id}, username={current_user.username}"
    )

    return success(
        CurrentUserResponse(
            id=current_user.id,
            username=current_user.username,
            nickname=current_user.nickname,
        )
    )
