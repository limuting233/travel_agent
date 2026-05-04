from datetime import date

from pydantic import BaseModel, Field


class TripOverviewResponse(BaseModel):
    """
    行程列表项响应模型。
    """

    id: str = Field(description="行程ID")
    title: str = Field(description="行程标题")
    location: str = Field(description="目的地")
    days: int = Field(description="旅行天数")
    start_date: date | None = Field(description="开始日期")
    end_date: date | None = Field(description="结束日期")
    status: str = Field(description="行程状态")
    latest_version_no: int = Field(description="最新版本号")
    created_at: int = Field(description="创建时间，秒级 Unix timestamp")
    updated_at: int = Field(description="更新时间，秒级 Unix timestamp")


class TripListResponse(BaseModel):
    """
    行程列表响应模型。
    """

    items: list[TripOverviewResponse] = Field(description="行程列表")
    page: int = Field(description="页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="总数量")


class TripVersionResponse(BaseModel):
    """
    行程版本响应模型。
    """

    version_no: int = Field(description="版本号")
    source: str = Field(description="版本来源")
    content: dict = Field(description="行程内容")
    created_at: int = Field(description="创建时间，秒级 Unix timestamp")


class TripDetailResponse(BaseModel):
    """
    行程详情响应模型。
    """

    id: str = Field(description="行程ID")
    title: str = Field(description="行程标题")
    location: str = Field(description="目的地")
    days: int = Field(description="旅行天数")
    start_date: date | None = Field(description="开始日期")
    end_date: date | None = Field(description="结束日期")
    preferences: list[str] | None = Field(description="用户偏好")
    status: str = Field(description="行程状态")
    latest_version: TripVersionResponse | None = Field(description="最新行程版本")
    created_at: int = Field(description="创建时间，秒级 Unix timestamp")
    updated_at: int = Field(description="更新时间，秒级 Unix timestamp")


class TripDeleteResponse(BaseModel):
    """
    删除行程响应模型。
    """

    deleted: bool = Field(description="是否删除成功")
