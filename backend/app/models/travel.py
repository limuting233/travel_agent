from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PublicIdMixin, SoftDeleteMixin, TimestampMixin


class Trip(PublicIdMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    行程主表。

    保存用户一次旅行规划的主记录。具体规划内容不放在这里，
    而是按版本写入 trip_versions，方便后续修改行程时保留历史版本。
    """

    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "status in ('planning', 'completed', 'failed', 'deleted')",
            name="trip_status",
        ),
        CheckConstraint("days >= 1", name="trip_days_positive"),
        Index("ix_trips_user_status_updated", "user_id", "status", "updated_at"),
        {"comment": "行程主表"},
    )

    id_prefix = "trip"

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="行程标题",
    )
    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="目的地",
    )
    days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="旅行天数",
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="开始日期",
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="结束日期",
    )
    preferences: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="用户偏好列表",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planning",
        server_default=text("'planning'"),
        index=True,
        comment="行程状态: planning/completed/failed/deleted",
    )
    latest_version_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="最新版本号",
    )
    thread_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
        comment="创建或最近一次修改使用的线程ID",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="规划失败原因",
    )

    versions: Mapped[list["TripVersion"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TripVersion(PublicIdMixin, TimestampMixin, Base):
    """
    行程版本表。

    初次生成和后续修改都写入这里。content 保存 API.md 中 latest_version.content
    对应的完整 JSON，包括 trip_overview 和 daily_itinerary。
    """

    __tablename__ = "trip_versions"
    __table_args__ = (
        UniqueConstraint("trip_id", "version_no", name="uq_trip_versions_trip_version_no"),
        CheckConstraint("version_no >= 1", name="trip_version_no_positive"),
        CheckConstraint("source in ('initial', 'revision')", name="trip_version_source"),
        Index("ix_trip_versions_trip_created", "trip_id", "created_at"),
        {"comment": "行程版本表"},
    )

    id_prefix = "ver"

    trip_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="行程ID",
    )
    version_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="版本号",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="initial",
        server_default=text("'initial'"),
        comment="版本来源: initial/revision",
    )
    revision_instruction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="修改指令",
    )
    content: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="行程内容JSON",
    )

    trip: Mapped[Trip] = relationship(back_populates="versions")


class AgentRun(PublicIdMixin, TimestampMixin, Base):
    """
    智能体执行记录表。
    """

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'failed')",
            name="agent_run_status",
        ),
        Index("ix_agent_runs_trip_agent_created", "trip_id", "agent_name", "created_at"),
        {"comment": "智能体执行记录表"},
    )

    id_prefix = "run"

    trip_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="行程ID",
    )
    trip_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("trip_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联行程版本ID",
    )
    thread_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
        comment="线程ID",
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="智能体名称",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="执行状态",
    )
    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="输入摘要",
    )
    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="输出摘要",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始时间",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="结束时间",
    )

    trip: Mapped[Trip] = relationship(back_populates="agent_runs")
    tool_call_logs: Mapped[list["ToolCallLog"]] = relationship(
        back_populates="agent_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ToolCallLog(PublicIdMixin, TimestampMixin, Base):
    """
    工具调用日志表。
    """

    __tablename__ = "tool_call_logs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'failed')",
            name="tool_call_log_status",
        ),
        Index("ix_tool_call_logs_agent_created", "agent_run_id", "created_at"),
        {"comment": "工具调用日志表"},
    )

    id_prefix = "tool"

    agent_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="智能体执行记录ID",
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="工具名称",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="调用状态",
    )
    request_args: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="工具请求参数",
    )
    response_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="响应摘要",
    )
    response_payload: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="响应原始内容",
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="调用耗时，毫秒",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    agent_run: Mapped[AgentRun] = relationship(back_populates="tool_call_logs")
