from flask import Flask, request, render_template
import os, time, requests, pytz
from datetime import datetime, timedelta
from timezonefinder import TimezoneFinder
from dotenv import load_dotenv
import config

# --- Setup ---
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("Missing API_KEY in .env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev")

LIMIT = config.LIMIT
DAYS_OF_WEEK = config.DAYS_OF_WEEK

# use local session + timeouts for safety
SESSION = requests.Session()
REQUEST_KW = dict(timeout=10)

# --- Helpers ---
def day_suffix(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

def future_day_gen():
    # eliminates global mutation; yields days cyclically
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
        return f"{(temp_k - 273.15) * 9 / 5 + 32:.2f}°F", "fahrenheit"
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

        # hh:mm AM/PM
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
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},{country}&limit={LIMIT}&appid={API_KEY}"
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

# --- Routes ---
@app.route("/")
def home():
    return render_template("weather_form.html")

@app.route("/get_weather", methods=["GET","POST"])
def get_weather_page():
    if request.method == "POST":
        city = (request.form.get("city") or "").strip()
        country = (request.form.get("country") or "").strip()
        temp_type = (request.form.get("temp_type") or "c").lower()  # normalize

        if not city or not country:
            return render_template("error.html", message="Please provide both city and country.")

        coordinates = get_coordinates(city, country)
        if coordinates[0] is False:
            return render_template("error.html", message="Invalid location.")

        lat, lon = coordinates
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

        image_type = image_type_f(
            float(temp_display[:-2]),
            description,
            temp_unit,
            now_local=local_time,
            sunrise_time=sunrise_time,
            sunset_time=sunset_time
        )
        theme_group = get_theme_group(image_type)

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

@app.errorhandler(404)
def not_found_error(e):
    return render_template("error.html", message="404 - Page Not Found"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", message="500 - Internal Server Error"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
