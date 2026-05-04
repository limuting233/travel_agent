from typing import TypeVar, Generic, Literal

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    接口响应模型，返回json格式
    """
    code: int = Field(description="业务状态码")
    message: Literal["success", "error"] = Field(description="业务状态描述")
    error_message: str | None = Field(description="错误信息")
    data: T | None = Field(description="响应数据")


def success(data: T | None = None) -> BaseResponse[T]:
    """
    成功响应处理函数
    :param data: 响应数据
    :return: 成功响应模型
    """
    return BaseResponse(code=200, message="success", error_message=None, data=data)


def error(code: int, error_message: str) -> BaseResponse:
    """
    错误响应处理函数
    :param code: 状态码
    :param error_message: 错误信息
    :return: 错误响应模型
    """
    return BaseResponse(code=code, message="error", error_message=error_message, data=None)
