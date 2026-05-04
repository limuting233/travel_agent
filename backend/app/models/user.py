from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PublicIdMixin, TimestampMixin


class User(PublicIdMixin, TimestampMixin, Base):
    """
    用户表
    """

    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    id_prefix = "usr"

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="用户名",
    )
    nickname: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="旅行者",
        server_default=text("'旅行者'"),
        comment="用户昵称",
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=True,
        comment="手机号",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        comment="邮箱",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希",
    )
