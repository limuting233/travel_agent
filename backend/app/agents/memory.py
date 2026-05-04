from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings
from loguru import logger

db_url: str = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

checkpointer: AsyncPostgresSaver | None = None
checkpointer_context = None


async def init_checkpointer() -> AsyncPostgresSaver:
    """
    初始化 checkpointer 短期记忆
    :return: AsyncPostgresSaver
    """
    global checkpointer, checkpointer_context
    if checkpointer is None or checkpointer_context is None:
        logger.info("正在初始化 checkpointer 短期记忆 ...")
        checkpointer_context = AsyncPostgresSaver.from_conn_string(conn_string=db_url)
        checkpointer = await checkpointer_context.__aenter__()
        await checkpointer.setup()
        logger.info("checkpointer 短期记忆 初始化完成")
        # return checkpointer

# async def close_checkpointer():
#     """
#     关闭 checkpointer 短期记忆
#     :return: None
#     """
#     global checkpointer, checkpointer_context
#     if checkpointer is None or checkpointer_context is None:
#         logger.info("checkpointer 短期记忆 未初始化")
#         return
#     logger.info("正在关闭 checkpointer 短期记忆 ...")
#     await checkpointer_context.__aexit__(None, None, None)
#     checkpointer = None
#     checkpointer_context = None
#     logger.info("checkpointer 短期记忆 已关闭")
