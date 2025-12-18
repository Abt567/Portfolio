# models_core.py
# SQLAlchemy Core table definitions + helper functions for engine + schema creation.
# NOTE: Practice file for learning SQLAlchemy Core.
# Not imported or used by the main weather app.
from __future__ import annotations
from sqlalchemy import (
    Table, Column, Integer, String, Float, Text, DateTime, ForeignKey, MetaData,
    JSON, CheckConstraint, Index, func, create_engine
)

# --- Metadata (shared registry of all tables) ---
metadata = MetaData()

# --- Table: User ---
user = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
)

# --- Table: SearchEvent ---
search_event = Table(
    "search_event",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    Column("city", String(120), nullable=False),
    Column("lat", Float, nullable=True),
    Column("lon", Float, nullable=True),
    Column("temp_unit", String(1), server_default="c", nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    CheckConstraint("temp_unit in ('c','f')", name="ck_search_event_temp_unit"),
    Index("ix_search_event_created_at", "created_at"),
    Index("ix_search_event_city", "city"),
)

# --- Table: WeatherCache ---
weather_cache = Table(
    "weather_cache",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("city", String(120), nullable=False),
    Column("lat", Float, nullable=False),
    Column("lon", Float, nullable=False),
    Column("provider", String(40), nullable=False),   # e.g., "openweather", "open-meteo"
    Column("kind", String(20), nullable=False),       # e.g., "current", "daily", "hourly"
    Column("payload", JSON, nullable=False),          # raw JSON from provider
    Column("fetched_at", DateTime, server_default=func.now(), nullable=False),
    Index("ux_weather_cache_key", "city", "lat", "lon", "provider", "kind", unique=True),
    Index("ix_weather_cache_fetched_at", "fetched_at"),
)

# --- Table: ObservationLog ---
observation_log = Table(
    "observation_log",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    Column("city", String(120), nullable=True),
    Column("rendered_at", DateTime, server_default=func.now(), nullable=False),
    Column("summary", Text, nullable=True),
    Index("ix_observation_log_rendered_at", "rendered_at"),
)

# --- Helper Functions ---

def make_engine(db_url: str | None = None):
    """
    Create a SQLAlchemy engine.
    - If db_url is None, defaults to local SQLite file 'weather_app.db'.
    """
    db_url = db_url or "sqlite:///weather_app.db"
    return create_engine(db_url, future=True)

def create_schema(engine=None):
    """
    Create all tables if they don't exist.
    """
    eng = engine or make_engine()
    metadata.create_all(eng)

def drop_schema(engine=None):
    """
    Drop all tables (useful during development/reset).
    WARNING: destructive.
    """
    eng = engine or make_engine()
    metadata.drop_all(eng)

# --- Public exports for 'from models_core import *' ---
__all__ = [
    "metadata",
    "user",
    "search_event",
    "weather_cache",
    "observation_log",
    "make_engine",
    "create_schema",
    "drop_schema",
]
