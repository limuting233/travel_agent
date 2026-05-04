from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def generate_public_id(prefix: str) -> str:
    """
    生成 API 对外暴露的可读 ID。

    API.md 中的资源 ID 都是带业务前缀的字符串，例如 usr_xxx、trip_xxx、
    run_xxx、tool_xxx。数据库内部也直接保存这种 ID，避免在接口层做二次映射。
    """
    if not prefix:
        raise ValueError("public id prefix cannot be empty")

    return f"{prefix}_{uuid.uuid4().hex}"


def datetime_to_unix(value: datetime | None) -> int | None:
    """
    将数据库 datetime 转成 API.md 约定的秒级 Unix timestamp。
    """
    if value is None:
        return None

    return int(value.timestamp())


class Base(DeclarativeBase):
    """
    数据库模型基类，所有数据库模型都应继承自该类
    """
    __abstract__ = True

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        id_value = getattr(self, "id", None)
        if id_value is None:
            return f"<{self.__class__.__name__}>"

        return f"<{self.__class__.__name__}(id={id_value!r})>"


class PublicIdMixin:
    """
    公共字符串主键。

    子类必须声明 id_prefix，例如:

        class Trip(PublicIdMixin, TimestampMixin, Base):
            id_prefix = "trip"

    这样生成的主键会匹配 API.md 中的 trip_xxx / run_xxx / tool_xxx。
    """

    id_prefix: ClassVar[str]

    @declared_attr
    def id(cls) -> Mapped[str]:
        prefix = getattr(cls, "id_prefix", "")
        return mapped_column(
            String(64),
            primary_key=True,
            default=lambda: generate_public_id(prefix),
            comment="主键ID",
        )


class TimestampMixin:
    """
    创建和更新时间。

    API 对外返回秒级 Unix timestamp；数据库保留 timezone-aware datetime，
    输出时使用 datetime_to_unix 转换。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )


class SoftDeleteMixin:
    """
    软删除能力。

    API.md 的删除行程建议使用软删除；这里提供通用 deleted_at，
    具体业务状态字段仍应由业务模型自己定义。
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        self.deleted_at = datetime.now().astimezone()
