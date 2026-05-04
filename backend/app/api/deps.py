import json

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.enums import StatusInfo
from app.core.exceptions import BusinessException
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db():
    """
    获取异步数据库会话
    :return: 异步数据库会话
    """
    async with async_session_factory() as db_session:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db_session: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前登录用户
    :param credentials: Bearer token 凭证
    :param db_session: 异步数据库会话
    :return: 当前用户
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BusinessException(StatusInfo.AUTH_REQUIRED)

    try:
        payload = decode_access_token(credentials.credentials)
    except (ValueError, json.JSONDecodeError):
        raise BusinessException(StatusInfo.AUTH_REQUIRED)

    result = await db_session.execute(
        select(User).where(User.id == payload["sub"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise BusinessException(StatusInfo.AUTH_REQUIRED)
    return user
