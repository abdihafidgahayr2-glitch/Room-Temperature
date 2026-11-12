from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import DateTime, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    # bcrypt hash - the plain password is never stored
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)


class Reading(Base):
    __tablename__ = "reading"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sensor: Mapped[str] = mapped_column(String(20), nullable=False)  # "temperature" or "humidity"
    content: Mapped[float] = mapped_column(Float, nullable=False)
    date_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                     default=lambda: datetime.now(UTC), index=True)


class WindowEvent(Base):
    __tablename__ = "window_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state: Mapped[str] = mapped_column(String(10), nullable=False)   # "open" or "closed"
    reason: Mapped[str] = mapped_column(String(20), nullable=False)  # "auto", "manual" or "startup"
    date_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                     default=lambda: datetime.now(UTC), index=True)


class Setting(Base):
    __tablename__ = "setting"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    open_at: Mapped[float] = mapped_column(Float, nullable=False)
    close_at: Mapped[float] = mapped_column(Float, nullable=False)
