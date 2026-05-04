from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class PlanTravelRequest(BaseModel):
    """
    旅行规划接口请求模型
    """

    model_config = ConfigDict(extra="forbid")  # 禁用额外字段

    location: str = Field(description="目的地,最小到区（县）")
    days: int = Field(description="计划天数", ge=1)
    start_date: str | None = Field(default=None, description="计划开始日期,格式YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="计划结束日期,格式YYYY-MM-DD")
    preferences: str | None = Field(default=None, description="用户偏好,例如: 美食、景点、历史等,用逗号分隔")

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        """
        验证目的地是否为空,并验证目的地是否存在
        :param v: 目的地字符串
        :return: 验证后的目的地字符串
        """
        v = v.strip()
        if not v:
            raise ValueError("location不能为空")

        # todo: 验证目的地是否存在

        return v

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v):
        """
        验证日期格式是否为YYYY-MM-DD
        :param v: 日期字符串
        :return: 验证后的日期字符串
        """
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date和end_date格式必须为YYYY-MM-DD")
        return v

    @field_validator("preferences")
    @classmethod
    def validate_preferences(cls, v):
        """
        验证用户偏好是否为逗号分隔的非空字符串
        :param v: 用户偏好字符串
        :return: 验证后的用户偏好字符串
        """
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None

        items = [item.strip() for item in v.split(",")]
        if any(not item for item in items):
            raise ValueError("preferences中存在空项，请使用逗号正确分隔")

        return ",".join(items)

    @model_validator(mode="after")
    def validate_date_range(self):
        """
        验证计划开始日期和结束日期的有效性
        :return: 验证后的PlanTravelRequest模型实例
        """
        if self.start_date and self.end_date:
            start = datetime.strptime(self.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            today = date.today()
            if start < today:
                raise ValueError("start_date不能早于当前日期")
            if start > end:
                raise ValueError("start_date必须早于end_date")

            if self.days != (end - start).days + 1:
                raise ValueError("days必须与start_date和end_date之间的天数一致")
        elif self.start_date or self.end_date:
            raise ValueError("start_date和end_date必须同时提供")

        return self
