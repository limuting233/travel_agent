from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import StatusInfo
from app.core.exceptions import BusinessException


class AuthCredentialRequest(BaseModel):
    """
    认证请求基础模型
    """
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

    @field_validator("username", "password")
    @classmethod
    def validate_username_password(cls, v):
        v = v.strip()
        if not v:
            raise BusinessException(StatusInfo.LOGIN_EMPTY_CREDENTIALS)

        if len(v) < 5 or len(v) > 12:
            raise BusinessException(StatusInfo.LOGIN_INVALID_LENGTH)
        return v


class RegisterRequest(AuthCredentialRequest):
    """
    注册请求模型
    """


class LoginRequest(AuthCredentialRequest):
    """
    登录请求模型
    """
