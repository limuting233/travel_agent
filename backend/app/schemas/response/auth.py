from pydantic import BaseModel, Field


class LoginResponse(BaseModel):
    """
    登录响应模型
    """

    access_token: str = Field(description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_at: int = Field(description="过期时间，秒级 Unix timestamp")


class CurrentUserResponse(BaseModel):
    """
    当前登录用户响应模型
    """

    id: str = Field(description="用户ID")
    username: str = Field(description="用户名")
    nickname: str = Field(description="用户昵称")
