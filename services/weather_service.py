import os
import requests
import difflib
from datetime import datetime
from dotenv import load_dotenv
import config

load_dotenv()
API_KEY = os.getenv("API_KEY")

SESSION = requests.Session()
REQUEST_KW = dict(timeout=10)



load_dotenv()
API_KEY = os.getenv("API_KEY")

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
    
def get_current_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}"
    try:
        r = SESSION.get(url, **REQUEST_KW)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None
    
def day_suffix(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def print_temperature(temp_k: float, temp_type: str):
    t = (temp_type or "c").lower()
    if t == "c":
        return f"{temp_k - 273.15:.2f}°C", "celsius"
    if t == "f":
        return f"{(temp_k - 273.15) * 9 / 5 + 32:.2f}°F", "fahrenheit"
    return "Invalid temperature type", "unknown"

    
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

def current_hour_description(om_data, now_local):
    """
    Pick the weather description for the current local hour
    using the hourly weathercode from Open-Meteo.
    """
    times = om_data["hourly"]["time"]
    wcodes = om_data["hourly"]["weathercode"]

    now_str = now_local.strftime("%Y-%m-%dT%H:00")

    try:
        idx = times.index(now_str)
    except ValueError:
        from datetime import datetime as _dt

        def parse(ts):
            return _dt.strptime(ts, "%Y-%m-%dT%H:%M")

        target = parse(now_str)
        idx = min(range(len(times)), key=lambda i: abs(parse(times[i]) - target))

    code = wcodes[idx]
    return config.WEATHERCODE_MAP.get(code, "Unknown")

