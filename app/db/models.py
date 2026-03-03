"""SQLAlchemy models for Tracer Dashboard."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class UserRole(str, PyEnum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"


class WellType(str, PyEnum):
    """Well types."""
    INJECTION = "injection"      # Нагнетательная
    PRODUCTION = "production"    # Добывающая
    GRYPHON = "gryphon"          # Грифон


class WellStatus(str, PyEnum):
    """Well operational status."""
    WORKING = "working"          # Работает
    REPAIR = "repair"            # Ремонт
    NOT_WORKING = "not_working"  # Не работает
    KRS = "krs"                  # КРС (капитальный ремонт скважины)


class GPSStatus(str, PyEnum):
    """GPS coordinate acquisition status."""
    RECEIVED = "received"
    TIMEOUT = "timeout"
    SKIPPED = "skipped_by_user"


class SampleType(str, PyEnum):
    """Sample types."""
    WATER = "water"                  # Вода
    OIL = "oil"                      # Нефть
    GAS = "gas"                      # Газ
    NOT_SAMPLED_GAS = "not_sampled_gas"  # Проба не отобрана (высокий газовый фактор)
    OTHER = "other"                  # Другое


class Deposit(Base):
    """
    Месторождение (deposit/field).
    Верхний уровень иерархии: Месторождение → Участки → Скважины → Пробы.
    Каждый Telegram-бот привязан к одному месторождению.
    """
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bot_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    group_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    sites: Mapped[list["Site"]] = relationship(
        back_populates="deposit",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


class User(Base):
    """Telegram user."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [x.value for x in e]),
        default=UserRole.USER,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    sampling_events: Mapped[list["SamplingEvent"]] = relationship(
        back_populates="operator",
        lazy="selectin"
    )

    @property
    def display_name(self) -> str:
        """Get display name for user."""
        if self.username:
            return f"@{self.username}"
        if self.first_name:
            return self.first_name
        return f"User {self.telegram_id}"


class Site(Base):
    """
    Участок (site/sector).
    Создаётся по названию нагнетательной скважины.
    Привязан к месторождению.
    """
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    deposit_id: Mapped[int] = mapped_column(ForeignKey("deposits.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    inj_well_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Unique constraint: site name unique within deposit
    __table_args__ = (
        UniqueConstraint("deposit_id", "name", name="uq_site_deposit_name"),
    )

    # Relationships
    deposit: Mapped["Deposit"] = relationship(back_populates="sites")
    wells: Mapped[list["Well"]] = relationship(
        back_populates="site",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    sampling_events: Mapped[list["SamplingEvent"]] = relationship(
        back_populates="site",
        lazy="selectin"
    )


class Well(Base):
    """
    Скважина (добывающая, грифон или нагнетательная).
    Привязана к участку.
    """
    __tablename__ = "wells"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    well_type: Mapped[WellType] = mapped_column(
        Enum(WellType, name="well_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False
    )
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Unique constraint: well name unique within site
    __table_args__ = (
        UniqueConstraint("site_id", "name", name="uq_well_site_name"),
        Index("ix_wells_site_name", "site_id", "name"),
    )

    # Relationships
    site: Mapped["Site"] = relationship(back_populates="wells")
    sampling_events: Mapped[list["SamplingEvent"]] = relationship(
        back_populates="well",
        lazy="selectin"
    )


class SamplingEvent(Base):
    """
    Событие отбора пробы.
    Одно событие = один визит/попытка отбора.
    """
    __tablename__ = "sampling_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    operator_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Well status at the time of sampling
    well_status: Mapped[WellStatus] = mapped_column(
        Enum(WellStatus, name="well_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False
    )

    # Sampling times (nullable if well not working)
    sampling_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    sampling_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Sample info
    sample_type: Mapped[SampleType] = mapped_column(
        Enum(SampleType, name="sample_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False
    )
    sample_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    volume_liters: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # GPS info
    gps_status: Mapped[GPSStatus] = mapped_column(
        Enum(GPSStatus, name="gps_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False
    )
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("ix_sampling_events_site_well_created", "site_id", "well_id", "created_at"),
        Index("ix_sampling_events_operator_created", "operator_user_id", "created_at"),
    )

    # Relationships
    site: Mapped["Site"] = relationship(back_populates="sampling_events")
    well: Mapped["Well"] = relationship(back_populates="sampling_events")
    operator: Mapped["User"] = relationship(back_populates="sampling_events")
