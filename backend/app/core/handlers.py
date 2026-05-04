from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.enums import StatusInfo
from app.core.exceptions import BusinessException
from loguru import logger


def _error_response(status: StatusInfo) -> JSONResponse:
    return JSONResponse(
        status_code=status.value[0],
        content={
            "code": status.value[1],
            "message": "error",
            "error_message": status.value[2],
            "data": None,
        },
    )


def _status_for_validation_error(request: Request, exception: RequestValidationError) -> StatusInfo:
    path = request.url.path
    if path == "/api/v1/travel/plan":
        return StatusInfo.TRAVEL_PLAN_INVALID_PARAMS

    if path.startswith("/api/v1/trips"):
        return StatusInfo.TRIP_BAD_REQUEST

    if path.startswith("/api/v1/auth"):
        error_types = {error.get("type") for error in exception.errors()}
        if "missing" in error_types:
            return StatusInfo.LOGIN_EMPTY_CREDENTIALS
        return StatusInfo.LOGIN_INVALID_LENGTH

    return StatusInfo.BAD_REQUEST


def handler_request_validation_exception(request: Request, exception: RequestValidationError) -> JSONResponse:
    """
    请求参数校验异常处理器，用于处理FastAPI在请求参数校验过程中抛出的异常
    :param request: 请求实例
    :param exception: 请求参数校验异常实例
    :return: JSONResponse 包含错误信息的响应体
    """
    logger.error(f"[RequestValidationError处理器] 请求路径:{request.url.path}, 异常信息:{exception}")
    return _error_response(_status_for_validation_error(request, exception))


def handler_business_exception(request: Request, exception: BusinessException) -> JSONResponse:
    """
    业务异常处理器，用于处理业务逻辑中抛出的异常
    :param request: 请求实例
    :param exception: 业务异常实例
    :return: JSONResponse 包含错误信息的响应体
    """

    http_code = exception.http_code  # 从异常实例中获取HTTP状态码
    code = exception.code  # 从异常实例中获取业务状态码
    error_message = exception.error_message  # 从异常实例中获取错误消息

    logger.error(f"[BusinessException处理器] http状态码:{http_code}, 业务状态码:{code}, 错误消息:{error_message}")

    return JSONResponse(
        status_code=http_code,
        content={
            "code": code,
            "message": "error",
            "error_message": error_message,
            "data": None
        }
    )


def handler_http_exception(request: Request, exception: StarletteHTTPException) -> JSONResponse:
    """
    HTTP异常处理器，主要用于统一 404 响应格式。
    """
    logger.error(
        f"[HTTPException处理器] 请求路径:{request.url.path}, "
        f"http状态码:{exception.status_code}, 异常信息:{exception.detail}"
    )
    if exception.status_code == 404:
        return _error_response(StatusInfo.ROUTE_NOT_FOUND)
    return JSONResponse(
        status_code=exception.status_code,
        content={
            "code": exception.status_code,
            "message": "error",
            "error_message": str(exception.detail),
            "data": None,
        },
    )


def handler_unhandled_exception(request: Request, exception: Exception) -> JSONResponse:
    """
    未捕获异常处理器。
    """
    logger.exception(f"[未捕获异常处理器] 请求路径:{request.url.path}, 异常信息:{str(exception)}")
    return _error_response(StatusInfo.INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI):
    """
    注册异常处理器
    :param app: FastAPI应用实例
    :return:
    """
    logger.info("正在注册异常处理器 ...")
    app.add_exception_handler(RequestValidationError, handler_request_validation_exception)
    app.add_exception_handler(BusinessException, handler_business_exception)
    app.add_exception_handler(StarletteHTTPException, handler_http_exception)
    app.add_exception_handler(Exception, handler_unhandled_exception)
    logger.info("异常处理器注册完成")
