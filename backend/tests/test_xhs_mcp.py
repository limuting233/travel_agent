import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app.core.config import settings


def format_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(format_exception(item) for item in exc.exceptions)

    return f"{type(exc).__name__}: {exc}"


async def main() -> None:
    print(f"ENV={os.getenv('ENV', 'dev')}")
    print(f"XHS_MCP_URL={settings.XHS_MCP_URL}")

    client = MultiServerMCPClient(
        {
            "xiaohongshu_mcp": {
                "transport": "http",
                "url": settings.XHS_MCP_URL,
                "timeout": settings.XHS_MCP_TIMEOUT,
            }
        }
    )

    try:
        async with client.session("xiaohongshu_mcp") as session:
            tools = await load_mcp_tools(session)
    except httpx.ConnectError as exc:
        raise SystemExit(f"小红书 MCP 不可用：无法连接服务。原因：{exc}") from exc
    except Exception as exc:
        raise SystemExit(
            f"小红书 MCP 不可用：连接或加载工具失败。原因：{format_exception(exc)}"
        ) from exc

    print(f"tool_count={len(tools)}")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
