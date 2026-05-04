from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.graph import build_travel_agent
from app.agents.mcp import create_amap_mcp_session
from app.api.v1.router import setup_router
# from app.agents.memory import init_checkpointer, close_checkpointer
# from app.api.v1.router import api_router
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.logging import setup_logging
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理上下文管理器
    :param app: FastAPI应用实例
    :return: None
    """
    async with create_amap_mcp_session():
        await build_travel_agent()
        yield

    # await build_travel_agent()


# def setup_router(app: FastAPI):
#     """
#     配置FastAPI应用实例的路由
#     :param app: FastAPI应用实例
#     :return: None
#     """
#     # 配置API路由
#     logger.info("正在配置 API(v1) 路由 ...")
#     app.include_router(api_router, prefix="/api/v1")
#     logger.info("API(v1) 路由配置完成")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例
    :return: FastAPI应用实例
    """
    # 配置日志
    setup_logging()

    logger.info(f"正在启动项目 {settings.PROJECT_NAME} ...")
    logger.info(f"当前项目版本: {settings.PROJECT_VERSION}")

    # 创建FastAPI应用实例
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        lifespan=lifespan,
    )

    # 配置API路由
    setup_router(app)

    # 注册异常处理器
    register_exception_handlers(app)

    return app


app = create_app()
