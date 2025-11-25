# test_backgrounds.py
"""
Quick sanity tests for image_type_f + get_theme_group.

Run:
    python test_backgrounds.py
"""

from datetime import datetime
from newestclean import image_type_f, get_theme_group


def run_tests():
    tests = [
        # --- Temperature-based, no time-of-day (now_local=None) ---

        {
            "name": "cold_celsius_no_snow",
            "temp": 5,  # below 10°C
            "desc": "Clear sky",
            "unit": "celsius",
            "now": None,
            "sr": None,
            "ss": None,
            "expected_image": "coldcase",
            "expected_theme": "snowtype",
        },
        {
            "name": "snowy_beats_cold_celsius",
            "temp": -5,  # below 0°C but description says snow
            "desc": "Slight snow fall",
            "unit": "celsius",
            "now": None,
            "sr": None,
            "ss": None,
            # description has "snow" so it should be snowycase, not coldcase
            "expected_image": "snowycase",
            "expected_theme": "snowtype",
        },
        {
            "name": "cold_fahrenheit_no_snow",
            "temp": 40,  # below 50°F
            "desc": "Clear sky",
            "unit": "fahrenheit",
            "now": None,
            "sr": None,
            "ss": None,
            "expected_image": "coldcase",
            "expected_theme": "snowtype",
        },
        {
            "name": "rain_by_description",
            "temp": 18,
            "desc": "Moderate rain",
            "unit": "celsius",
            "now": None,
            "sr": None,
            "ss": None,
            "expected_image": "raincase",
            "expected_theme": "dark_and_soft",
        },
        {
            "name": "fog_by_description",
            "temp": 4,
            "desc": "Fog",
            "unit": "celsius",
            "now": None,
            "sr": None,
            "ss": None,
            "expected_image": "foggycase",
            "expected_theme": "dark_and_soft",
        },
        {
            "name": "clear_mid_celsius",
            "temp": 15,
            "desc": "",
            "unit": "celsius",
            "now": None,
            "sr": None,
            "ss": None,
            "expected_image": "clearcase",
            "expected_theme": "dark_and_soft",
        },

        # --- Time-of-day based tests (these ignore temp/description once they match) ---

        {
            "name": "moon_before_sunrise",
            "temp": 10,
            "desc": "Clear sky",
            "unit": "celsius",
            "now": datetime(2025, 1, 1, 6, 0),  # 06:00
            "sr": "07:30",
            "ss": "18:00",
            "expected_image": "mooncase",
            "expected_theme": "special_case",
        },
        {
            "name": "sunrise_window",
            "temp": 10,
            "desc": "Clear sky",
            "unit": "celsius",
            "now": datetime(2025, 1, 1, 7, 40),  # 10 min after 07:30
            "sr": "07:30",
            "ss": "18:00",
            "expected_image": "sunrisecase",
            "expected_theme": "dark_and_soft",
        },
        {
            "name": "sunset_window",
            "temp": 10,
            "desc": "Clear sky",
            "unit": "celsius",
            "now": datetime(2025, 1, 1, 17, 50),  # 10 min before 18:00
            "sr": "07:30",
            "ss": "18:00",
            "expected_image": "sunsetcase",
            "expected_theme": "dark_and_soft",
        },
        {
            "name": "moon_after_sunset_window",
            "temp": 10,
            "desc": "Clear sky",
            "unit": "celsius",
            "now": datetime(2025, 1, 1, 18, 30),  # 30 min after 18:00
            "sr": "07:30",
            "ss": "18:00",
            "expected_image": "mooncase",
            "expected_theme": "special_case",
        },
        {
            "name": "polar_season_case",
            "temp": -10,
            "desc": "Clear sky",
            "unit": "celsius",
            "now": datetime(2025, 1, 1, 12, 0),
            "sr": "00:00",
            "ss": "00:00",
            "expected_image": "polarseasoncase",
            "expected_theme": "special_case",
        },
    ]

    passed = 0
    failed = 0

    for t in tests:
        img = image_type_f(
            t["temp"],
            t["desc"],
            t["unit"],
            now_local=t["now"],
            sunrise_time=t["sr"],
            sunset_time=t["ss"],
        )
        theme = get_theme_group(img)

        ok_img = (img == t["expected_image"])
        ok_theme = (theme == t["expected_theme"])

        if ok_img and ok_theme:
            passed += 1
            print(f"[PASS] {t['name']}: image={img}, theme={theme}")
        else:
            failed += 1
            print(f"[FAIL] {t['name']}")
            print(f"       got:      image={img}, theme={theme}")
            print(f"       expected: image={t['expected_image']}, theme={t['expected_theme']}")

    print()
    print(f"Total: {passed} passed, {failed} failed")


if __name__ == "__main__":
    run_tests()
