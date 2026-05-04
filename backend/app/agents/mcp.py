from contextlib import asynccontextmanager
from typing import List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession

from app.core.config import settings

from loguru import logger

# mcp_client: MultiServerMCPClient | None = None

xhs_mcp_session = None  # 小红书MCP持久会话
mcp_client: MultiServerMCPClient | None = None  # MCP客户端
amap_mcp_session = None  # 高德地图MCP持久会话

AMAP_MCP_TIMEOUT_SECONDS = 20


def _create_mcp_client():
    """
    创建MCP客户端
    :return: MCP客户端
    """
    global mcp_client
    if mcp_client is None:
        logger.info("正在创建MCP客户端 ...")
        mcp_config = {
            # 小红书MCP配置
            "xiaohongshu_mcp": {
                "transport": "http",
                "url": settings.XHS_MCP_URL,
                "timeout": settings.XHS_MCP_TIMEOUT,
            },
            # 高德地图MCP配置
            "amap-maps-streamableHTTP": {
                "transport": "http",
                "url": f"{settings.AMAP_MCP_BASE_URL}?key={settings.AMAP_API_KEY}",
                "timeout": min(settings.AMAP_MCP_TIMEOUT, AMAP_MCP_TIMEOUT_SECONDS),
            }
        }

        mcp_client = MultiServerMCPClient(mcp_config)
        logger.info("MCP客户端创建完成")


def fix_xhs_tool_schema(tool) -> BaseTool:
    """
    修复工具的 schema，确保符合 OpenAI function calling 的要求
    :param tool: 原始工具
    :return: 修复后的工具
    """
    # 确保 args_schema 是字典类型
    if isinstance(tool.args_schema, dict):
        if "properties" not in tool.args_schema:
            tool.args_schema["properties"] = {}
            tool.args_schema["required"] = []

    return tool


@asynccontextmanager
async def create_xhc_mcp_session():
    """
    创建小红书MCP持久会话（上下文管理器）

    """
    global xhs_mcp_session, mcp_client
    if xhs_mcp_session is None:
        if mcp_client is None:
            _create_mcp_client()

        # client = _create_mcp_client()  # 创建MCP客户端
        logger.info(f"正在创建小红书MCP持久会话 ...")

        async with mcp_client.session(server_name="xiaohongshu_mcp") as session:

            # tools = await load_mcp_tools(session=session)
            # fixed_tools = [fix_tool_schema(t) for t in tools]
            # logger.info(f"已加载 {len(fixed_tools)} 个小红书MCP工具")

            try:
                xhs_mcp_session = session
                logger.info("小红书MCP会话创建完成")

                yield
            finally:
                logger.info("小红书MCP会话已关闭")


@asynccontextmanager
async def create_amap_mcp_session():
    """
    创建高德地图MCP持久会话（上下文管理器）

    """
    global amap_mcp_session, mcp_client
    if amap_mcp_session is None:
        if mcp_client is None:
            _create_mcp_client()

        # client = _create_mcp_client()  # 创建MCP客户端
        logger.info(f"正在创建高德地图MCP持久会话 ...")

        async with mcp_client.session(server_name="amap-maps-streamableHTTP") as session:

            try:
                amap_mcp_session = session
                logger.info("高德地图MCP会话创建完成")

                yield
            finally:
                logger.info("高德地图MCP会话已关闭")
