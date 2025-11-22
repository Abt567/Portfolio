# models_core.py  (ORM + session helpers)

from __future__ import annotations
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
)
from sqlalchemy import create_engine
from flask_login import UserMixin

# ---- Base ----
class Base(DeclarativeBase):
    pass

# ---- Engine / Session ----
DB_URL = os.getenv("DATABASE_URL", "sqlite:///weather_app.db")
engine = create_engine(DB_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()

# ---- Models ----
class User(UserMixin, Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    searches: Mapped[list["SearchEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class SearchEvent(Base):
    __tablename__ = "search_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(80))
    lat: Mapped[Optional[float]] = mapped_column(Float)
    lon: Mapped[Optional[float]] = mapped_column(Float)
    temp_unit: Mapped[str] = mapped_column(String(1), nullable=False, default="c")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship(back_populates="searches")

class ObservationLog(Base):
    __tablename__ = "observation_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    rendered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
