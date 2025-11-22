# newestclean.py  (minimal changes applied)

from flask import Flask, request, render_template, render_template_string
from jinja2 import TemplateNotFound
import os, time, requests, pytz, difflib
from datetime import datetime, timedelta
from timezonefinder import TimezoneFinder
from dotenv import load_dotenv
import config

from flask_login import LoginManager, current_user, login_required
from sqlalchemy import func, select, inspect

from models_core import init_db, get_session, User, SearchEvent, ObservationLog
from auth import bp as auth_bp




# --- Setup ---
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("Missing API_KEY in .env")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET", "dev")

# --- DB + Login setup ---
init_db()

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # redirect target for @login_required
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id: str):
    db = get_session()
    return db.get(User, int(user_id))

app.register_blueprint(auth_bp)

LIMIT = config.LIMIT
DAYS_OF_WEEK = config.DAYS_OF_WEEK

# use local session + timeouts for safety
SESSION = requests.Session()
REQUEST_KW = dict(timeout=10)

# --- Helpers (unchanged) ---
def day_suffix(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

def future_day_gen():
    idx = DAYS_OF_WEEK.index(time.strftime("%A", time.localtime()).upper())
    while True:
        idx = (idx + 1) % 7
        yield DAYS_OF_WEEK[idx]

_future_day = future_day_gen()

def future_day():
    return next(_future_day)

def print_temperature(temp_k: float, temp_type: str):
    t = (temp_type or "c").lower()
    if t == "c":
        return f"{temp_k - 273.15:.2f}°C", "celsius"
    if t == "f":
        return f("{(temp_k - 273.15) * 9 / 5 + 32:.2f}°F"), "fahrenheit"
    return "Invalid temperature type", "unknown"

def fetch_forecast_data(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode,sunrise,sunset,"
        "rain_sum,precipitation_probability_max"
        "&hourly=relative_humidity_2m,temperature_2m,weathercode"
        "&timezone=auto"
    )
    try:
        r = SESSION.get(url, **REQUEST_KW)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None

def organize_weekly_forecast(data, temp_type):
    forecast = []
    days = data["daily"]["time"]
    tmax = list(data["daily"]["temperature_2m_max"])
    tmin = list(data["daily"]["temperature_2m_min"])
    rain_chances = data["daily"]["precipitation_probability_max"]
    wcodes = data["daily"]["weathercode"]

    for i, d in enumerate(days):
        dt = datetime.strptime(d, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        month = config.MONTH_NAME_MAP[dt.strftime("%m")]
        day_num = int(dt.strftime("%d"))

        if (temp_type or "c").lower() == "f":
            tmax[i] = round(tmax[i] * 9 / 5 + 32, 1)
            tmin[i] = round(tmin[i] * 9 / 5 + 32, 1)

        formatted = f"{day_name}, {month} {day_num}{day_suffix(day_num)}"
        forecast.append({
            "day": day_name,
            "month_day_full": formatted,
            "temperature_2m_max": tmax[i],
            "temperature_2m_min": tmin[i],
            "rain": rain_chances[i],
            "weathercode": wcodes[i]
        })
    return forecast

def organize_rain_and_sun(data):
    return data["daily"]["rain_sum"][0], data["daily"]["sunrise"][0], data["daily"]["sunset"][0]

def hourly_forcast_list_f(data, now_local, temp_type, num_hours=24):
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    wcodes = data["hourly"]["weathercode"]

    now_str = now_local.strftime("%Y-%m-%dT%H:00")
    start_idx = times.index(now_str) if now_str in times else 0

    out = []
    total = len(times)
    for i in range(num_hours):
        idx = (start_idx + i) % total
        t = times[idx]
        temp_k = temps[idx] + 273.15
        temp_formatted, _unit = print_temperature(temp_k, temp_type)

        date_part, hour_part = t.split("T")
        hh, mm = map(int, hour_part.split(":")[:2])
        if hh == 0:
            display_hour = f"12:{mm:02d} AM"
        elif hh < 12:
            display_hour = f"{hh}:{mm:02d} AM"
        elif hh == 12:
            display_hour = f"12:{mm:02d} PM"
        else:
            display_hour = f"{hh - 12}:{mm:02d} PM"

        desc = config.WEATHERCODE_MAP.get(wcodes[idx], "Unknown")
        out.append({
            "display_hour": display_hour,
            "temp": temp_formatted,
            "date": date_part,
            "desc": desc
        })
    return out

def organize_humidity(data):
    humidity = data["hourly"]["relative_humidity_2m"]
    n_days = len(humidity) // 24
    week_humid = []
    for day in range(n_days):
        s, e = day * 24, day * 24 + 24
        avg = round(sum(humidity[s:e]) / 24, 2)
        week_humid.append((future_day(), avg))
    return week_humid

def get_coordinates(city, country):
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city},{country}&limit={LIMIT}&appid={API_KEY}"
    try:
        r = SESSION.get(url, **REQUEST_KW)
        r.raise_for_status()
        data = r.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
        return False, "Invalid coordinate found"
    except requests.RequestException:
        return False, "API request failed"

def get_current_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}"
    try:
        r = SESSION.get(url, **REQUEST_KW)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None

def image_type_f(temp, description, temp_type, now_local=None, sunrise_time=None, sunset_time=None):
    description = (description or "").lower()
    if now_local and sunrise_time and sunset_time:
        try:
            if sunrise_time == "00:00" and sunset_time == "00:00":
                return "polarseasoncase"

            now_total = now_local.hour * 60 + now_local.minute
            sr_h, sr_m = map(int, sunrise_time.split(":"))
            ss_h, ss_m = map(int, sunset_time.split(":"))
            sr_total = sr_h * 60 + sr_m
            ss_total = ss_h * 60 + ss_m

            if now_total < sr_total:
                return "mooncase"
            elif sr_total <= now_total <= sr_total + config.SUN_WINDOW_MINUTES:
                return "sunrisecase"
            elif ss_total - 20 <= now_total <= ss_total:
                return "sunsetcase"
            elif now_total > ss_total + 20:
                return "mooncase"
        except Exception:
            pass

    if "rain" in description: return "raincase"
    if "snow" in description: return "snowycase"
    if "cloud" in description: return "cloudycase"
    if "clear" in description: return "clearcase"
    if "sun" in description: return "sunnycase"
    if any(x in description for x in ["fog", "mist"]): return "foggycase"

    unit = (temp_type or "").lower()
    if unit == "celsius":
        return "snowycase" if temp < 0 else "sunnycase" if temp > 25 else "clearcase"
    if unit == "fahrenheit":
        return "snowycase" if temp < 32 else "sunnycase" if temp > 77 else "clearcase"
    return "clearcase"

def get_theme_group(image_type):
    snowtype = {"snowycase","coldcase"}
    dark_and_soft = {
        "cloudycase","raincase","foggycase","snowycase","coldcase",
        "sunnycase","sunrisecase","sunsetcase","clearcase"
    }
    special = {"mooncase","polarseasoncase"}
    if image_type in snowtype: return "snowtype"
    if image_type in dark_and_soft: return "dark_and_soft"
    if image_type in special: return "special_case"
    return "dark_and_soft"

def get_local_time(lat, lon):
    tf = TimezoneFinder()
    tz_str = tf.timezone_at(lng=lon, lat=lat)
    if tz_str is None:
        raise ValueError("Could not determine time zone for the given location.")
    tz = pytz.timezone(tz_str)
    return datetime.now(tz)

def format_time_for_display(ts: str):
    hhmm = ts[11:16]
    hr, minute = map(int, hhmm.split(":"))
    suffix = "am" if hr < 12 else "pm"
    hr = hr if 1 <= hr <= 12 else hr - 12 if hr > 12 else 12
    return f"{hr}:{minute:02d} {suffix}"

def extract_time_only(ts: str):  # '2025-08-22T05:27'
    return ts[11:16]

# ==========================
# City-only geocoding helpers (with fuzzy fallback)
# ==========================
ADMIN_WORDS = (
    "county", "province", "district", "municipio", "region",
    "prefecture", "department", "governorate", "oblast", "territory"
)

def _is_admin_like(name: str) -> bool:
    n = (name or "").lower()
    return any(w in n for w in ADMIN_WORDS)

def _normalize_city(s: str) -> str:
    return "".join((s or "").lower().split())

def _owm_query(q: str, limit=7):
    url = "https://api.openweathermap.org/geo/1.0/direct"
    params = {"q": q, "limit": limit, "appid": API_KEY}
    r = SESSION.get(url, params=params, **REQUEST_KW)
    r.raise_for_status()
    data = r.json() or []
    out = []
    for d in data:
        out.append({
            "name": d.get("name", ""),
            "state": d.get("state", ""),
            "country": d.get("country", ""),
            "lat": d.get("lat"),
            "lon": d.get("lon"),
        })
    return out

def search_locations(city, limit=7):
    city = (city or "").strip()
    if len(city) < 2:
        return []

    # 1) Normal query
    try:
        primary = _owm_query(city, limit=limit)
        if primary:
            return primary
    except requests.RequestException:
        return []

    # 2) Fuzzy fallback
    words = [w for w in city.split() if w]
    longest = max(words, key=len) if words else city
    broaden_terms = []

    if len(longest) >= 3:
        broaden_terms.append(longest)
    if words and words[0].lower() != longest.lower():
        broaden_terms.append(words[0])
    if len(city) >= 3:
        broaden_terms.append(city[:3])

    seen = set()
    candidates = []
    for term in broaden_terms:
        try:
            for item in _owm_query(term, limit=10):
                key = (item.get("name"), item.get("state"), item.get("country"))
                if key not in seen and item.get("lat") is not None and item.get("lon") is not None:
                    seen.add(key)
                    candidates.append(item)
        except requests.RequestException:
            continue

    if not candidates:
        return []

    target = _normalize_city(city)
    def score(item):
        name_norm = _normalize_city(item.get("name",""))
        sim = difflib.SequenceMatcher(None, target, name_norm).ratio()
        bonus = 0.02 if (item.get("country") == "US" and item.get("state")) else 0.0
        return sim + bonus

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]

def pick_best_location(cands, query_city=None):
    if not cands:
        return None

    cands = [c for c in cands if c.get("lat") is not None and c.get("lon") is not None]
    if not cands:
        return None

    if len(cands) == 1:
        return cands[0]

    query = (query_city or "").strip().lower()

    exact_non_admin = [c for c in cands if (c.get("name","").lower() == query) and not _is_admin_like(c.get("name",""))]
    if len(exact_non_admin) == 1:
        return exact_non_admin[0]
    elif len(exact_non_admin) > 1:
        with_state = [c for c in exact_non_admin if c.get("state")]
        if with_state:
            return with_state[0]
        return exact_non_admin[0]

    us = [c for c in cands if (c.get("country") or "").upper() == "US"]
    non_us = [c for c in cands if (c.get("country") or "").upper() != "US"]

    if len(non_us) == 1:
        return non_us[0]

    us_citylike = [c for c in us if not _is_admin_like(c.get("name",""))]
    if us_citylike:
        states = { (c.get("state") or "").lower() for c in us_citylike }
        if len(states - {""}) > 1:
            return None  # ambiguous (e.g., Springfield)
        starts = [c for c in us_citylike if c.get("name","").lower().startswith(query)]
        if starts:
            with_state = [c for c in starts if c.get("state")]
            return with_state[0] if with_state else starts[0]
        with_state = [c for c in us_citylike if c.get("state")]
        return with_state[0] if with_state else us_citylike[0]

    non_admin = [c for c in cands if not _is_admin_like(c.get("name",""))]
    if non_admin:
        return non_admin[0]

    return cands[0]

# --- Routes ---
@app.route("/")
def home():
    return render_template("weather_form.html")

@app.route("/get_weather", methods=["GET","POST"])
def get_weather_page():
    if request.method == "POST":
        # Support direct lat/lon postback (after user picks)
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        temp_type = (request.form.get("temp_type") or "c").lower()  # normalize

        if lat and lon:
            city = request.form.get("picked_name") or "Selected location"
            country = request.form.get("picked_country") or ""
            lat = float(lat); lon = float(lon)
        else:
            # original inputs (country may be absent if you removed it from the form)
            city = (request.form.get("city") or "").strip()
            country = (request.form.get("country") or "").strip()

            if not city and not country:
                return render_template("error.html", message="Please provide a city (and optional country).")

            if city and not country:
                # city-only flow
                candidates = search_locations(city, limit=7)
                if not candidates:
                    return render_template("error.html", message=f"No results for “{city}”.")
                pick = pick_best_location(candidates, query_city=city)
                if pick is None:
                    # ambiguous US city → ask user to choose
                    return render_template("choose_location.html", candidates=candidates, city_query=city)
                country = pick.get("country", "")
                lat = float(pick["lat"]); lon = float(pick["lon"])
                city = pick.get("name") or city
            else:
                # existing flow (kept)
                if not city or not country:
                    return render_template("error.html", message="Please provide both city and country.")
                coordinates = get_coordinates(city, country)
                if coordinates[0] is False:
                    return render_template("error.html", message="Invalid Location")
                lat, lon = coordinates

        # === original logic unchanged below ===
        ow = get_current_weather(lat, lon)
        om = fetch_forecast_data(lat, lon)
        if not ow or not om:
            return render_template("error.html", message="Weather data could not be loaded.")

        daily_code = om["daily"]["weathercode"][0]
        description = config.WEATHERCODE_MAP.get(daily_code, "Unknown")

        temp_c = om["daily"]["temperature_2m_max"][0]
        temp_k = temp_c + 273.15
        temp_display, temp_unit = print_temperature(temp_k, temp_type)

        humidity_data = organize_humidity(om)
        rain, sunrise, sunset = organize_rain_and_sun(om)
        weekly_forecast = organize_weekly_forecast(om, temp_type)
        local_time = get_local_time(lat, lon)
        hourly_forecast = hourly_forcast_list_f(om, local_time, temp_type)

        sunrise_time = extract_time_only(sunrise)
        sunset_time = extract_time_only(sunset)

        display_sunrise = format_time_for_display(sunrise)
        display_sunset = format_time_for_display(sunset)

        try:
            temp_num = float(temp_display.replace("°C","").replace("°F",""))
        except:
            temp_num = temp_c

        image_type = image_type_f(
            temp_num,
            description,
            temp_unit,
            now_local=local_time,
            sunrise_time=sunrise_time,
            sunset_time=sunset_time
        )
        theme_group = get_theme_group(image_type)

        # --- minimal addition: LOG THE SEARCH ---
        try:
            db = get_session()
            db.add(SearchEvent(
                user_id=current_user.id if current_user.is_authenticated else None, # if user signed in save that info 
                city=city,
                country=country or None,
                lat=lat,
                lon=lon,
                temp_unit=(temp_type or "c")[:1].lower()
            ))
            db.commit()
        except Exception:
            pass  # keep behavior same: don't break page if logging fails

        return render_template(
            "mine.html",
            image_type=image_type,
            city=city, country=country,
            temperature=temp_display,
            description=description,
            humidity_data=humidity_data,
            rain=rain,
            sunrise=display_sunrise,
            sunset=display_sunset,
            weekly_forcast=weekly_forecast,
            hourly_forecast=hourly_forecast,
            weathercode_map=config.WEATHERCODE_MAP,
            theme_group=theme_group,
            temp_type=temp_type
        )

    return render_template("weather_form.html")
# --- helper added just above analytics route ---
def table_has_column(session, table_name: str, column_name: str) -> bool:
    """
    Returns True if the given column exists in the given table,
    using SQLAlchemy's inspector (works cleanly with SQLite).
    """
    try:
        insp = inspect(session.bind)
        cols = [c["name"].lower() for c in insp.get_columns(table_name)]
        return column_name.lower() in cols
    except Exception:
        return False


@app.route("/analytics")
@login_required
def analytics():
    db = get_session()

    # Top cities (same query style you use elsewhere)
    top_cities = db.execute(
        select(SearchEvent.city, func.count(SearchEvent.id))
        .group_by(SearchEvent.city)
        .order_by(func.count(SearchEvent.id).desc())
        .limit(10)
    ).all()

    # Handle missing `country` column gracefully
    has_country = table_has_column(db, "search_event", "country")

    if has_country:
        recent = db.execute(
            select(SearchEvent.city, SearchEvent.country, SearchEvent.created_at)
            .where(SearchEvent.user_id == current_user.id)
            .order_by(SearchEvent.created_at.desc())
            .limit(15)
        ).all()
    else:
        rows = db.execute(
            select(SearchEvent.city, SearchEvent.created_at)
            .where(SearchEvent.user_id == current_user.id)
            .order_by(SearchEvent.created_at.desc())
            .limit(15)
        ).all()
        recent = [(city, "", ts) for (city, ts) in rows]

    return render_template("analytics.html", top_cities=top_cities, recent=recent)

@app.errorhandler(404)
def not_found_error(e):
    return render_template("error.html", message="404 - Page Not Found"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", message="500 - Internal Server Error"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
