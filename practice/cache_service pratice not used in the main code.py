# NOTE: Practice file for learning SQLAlchemy Core.
# Not imported or used by the main weather app.import json, datetime as dt
from sqlalchemy import select, delete
from models_core import WeatherCache, get_session

DEFAULT_TTL_SECONDS = 600  # 10 minutes

def _now():
    return dt.datetime.utcnow()

def make_key(city: str, lat: float, lon: float, unit: str) -> str:
    city_norm = (city or "").strip().lower()
    unit = (unit or "c").lower()
    return f"{city_norm}|{round(lat,4)}|{round(lon,4)}|{unit}"

def get_cache(key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS):
    db = get_session()
    row = db.execute(select(WeatherCache).where(WeatherCache.key == key)).scalar_one_or_none()
    if not row:
        return None
    age = (_now() - row.fetched_at).total_seconds()
    if age > ttl_seconds:
        # expire old cache
        db.execute(delete(WeatherCache).where(WeatherCache.id == row.id))
        db.commit()
        return None
    return row.payload

def set_cache(key: str, payload: dict, provider: str = "combined"):
    db = get_session()
    existing = db.execute(select(WeatherCache).where(WeatherCache.key == key)).scalar_one_or_none()
    if existing:
        existing.payload_json = json.dumps(payload)
        existing.provider = provider
        existing.fetched_at = _now()
    else:
        row = WeatherCache(
            key=key,
            payload_json=json.dumps(payload),
            provider=provider,
            fetched_at=_now(),
        )
        db.add(row)
    db.commit()
