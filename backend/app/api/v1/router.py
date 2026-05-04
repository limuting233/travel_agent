from fastapi import APIRouter, FastAPI

from app.api.v1.endpoints import auth, travel, trips
from loguru import logger


api_router = APIRouter()


# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(travel.router, prefix="/travel", tags=["travel"])


def setup_router(app: FastAPI):
    """
    配置FastAPI应用实例的路由
    :param app: FastAPI应用实例
    :return: None
    """
    # 配置API路由
    logger.info("正在配置 API(v1) 路由 ...")

    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(travel.router, prefix="/travel", tags=["travel"])
    api_router.include_router(trips.router, prefix="/trips", tags=["trips"])

    app.include_router(api_router, prefix="/api/v1")
    logger.info("API(v1) 路由配置完成")
