import json
from typing import AsyncGenerator

from loguru import logger
from pydantic import BaseModel


async def sse_generator(generator: AsyncGenerator[BaseModel | dict | str, None]):
    """
    sse 生成器
    :param generator:
    :return:
    """
    try:
        async for chunk in generator:
            # model_dump_json() 比 json.dumps(model.dict()) 性能更好
            # payload = chunk.model_dump_json()
            event = chunk.event
            data = chunk.data

            yield f"event: {event}\ndata: {data.model_dump_json()}\n\n"
    except Exception as e:
        logger.exception(f"[sse_generator] 异常: {str(e)}")
