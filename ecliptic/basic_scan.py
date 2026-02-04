import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple

import requests

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Horizons major-body IDs (COMMAND)
PLANET_IDS = {
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
    "Uranus": "799",
    "Neptune": "899",
    # Earth is 399 (usually excluded from "alignment planets")
}


@dataclass
class AlignmentHit:
    start: date
    end: date
    planets: List[str]
    max_span_deg: float  # minimal arc covering all longitudes


def _circular_span_deg(angles_deg: List[float]) -> float:
    """
    Given angles on a circle [0,360), return minimal arc length covering all angles.
    """
    if not angles_deg:
        return 0.0
    a = sorted([x % 360.0 for x in angles_deg])
    if len(a) == 1:
        return 0.0
    # Find the largest gap between consecutive angles (including wrap-around).
    gaps = []
    for i in range(len(a) - 1):
        gaps.append(a[i + 1] - a[i])
    gaps.append((a[0] + 360.0) - a[-1])  # wrap gap
    largest_gap = max(gaps)
    return 360.0 - largest_gap


def _parse_lon_from_result_text(result_text: str) -> float:
    """
    Parse ecliptic longitude from Horizons 'result' text when CSV_FORMAT=YES and QUANTITIES=31.
    We request a single day (START=STOP-STEP), so we take the first data line inside $$SOE/$$EOE.
    """
    # Extract lines between $$SOE and $$EOE
    m = re.search(r"\$\$SOE(.*?)\$\$EOE", result_text, flags=re.S)
    if not m:
        raise ValueError("Could not find $$SOE/$$EOE block in Horizons response.")
    block = m.group(1).strip()

    # Find first non-empty line that looks like CSV data (ignore headers)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("No ephemeris data lines found in $$SOE block.")

    # If CSV_FORMAT=YES, line is comma-separated. Quantity 31 includes:
    # ... "EclLon", "EclLat" (names vary), but we’ll take the first numeric pair at the end.
    # Safer: split by comma and pick last two fields that can be floats.
    parts = [p.strip() for p in lines[0].split(",")]

    floats = []
    for p in reversed(parts):
        try:
            floats.append(float(p))
        except ValueError:
            continue
        if len(floats) >= 2:
            break
    if len(floats) < 2:
        raise ValueError(f"Could not parse ecliptic lon/lat from line: {lines[0]}")

    ecl_lat = floats[0]
    ecl_lon = floats[1]
    return ecl_lon % 360.0


def fetch_geocentric_ecliptic_longitude(
    body_id: str,
    day: date,
    session: Optional[requests.Session] = None,
) -> float:
    """
    Fetch observer-centered Earth ecliptic longitude for the target body on given date (UTC).
    Uses EPHEM_TYPE=OBSERVER, CENTER='500@399' (Earth geocenter),
    QUANTITIES='31' (Observer-centered Earth ecliptic lon/lat),
    CSV_FORMAT=YES for easier parsing.
    """
    s = session or requests.Session()

    start = day.isoformat()
    stop = (day + timedelta(days=1)).isoformat()

    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",  # geocenter @ Earth
        "START_TIME": f"'{start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": "'30 d'",
        "QUANTITIES": "'31'",  # Observer-centered Earth ecliptic lon/lat
        "CSV_FORMAT": "YES",
        "CAL_FORMAT": "CAL",
        "TIME_DIGITS": "MINUTES",
    }

    r = s.get(HORIZONS_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "result" not in data:
        raise ValueError(f"Unexpected Horizons response: {data.keys()}")
    return _parse_lon_from_result_text(data["result"])


def list_planetary_alignments(
    start_day: date,
    end_day: date,
    planets: List[str],
    span_threshold_deg: float = 10.0,
) -> List[AlignmentHit]:
    """
    Scan [start_day, end_day] inclusive and return alignment intervals where
    minimal arc covering all planet longitudes <= span_threshold_deg.
    """
    for p in planets:
        if p not in PLANET_IDS:
            raise ValueError(f"Unknown planet name: {p}. Available: {list(PLANET_IDS.keys())}")

    hits: List[Tuple[date, float]] = []
    with requests.Session() as sess:
        d = start_day
        while d <= end_day:
            lons = []
            for p in planets:
                lon = fetch_geocentric_ecliptic_longitude(PLANET_IDS[p], d, session=sess)
                lons.append(lon)

            span = _circular_span_deg(lons)
            if span <= span_threshold_deg:
                hits.append((d, span))
            d += timedelta(days=1)

    # Merge consecutive days into intervals
    if not hits:
        return []

    intervals: List[AlignmentHit] = []
    cur_start = hits[0][0]
    cur_end = hits[0][0]
    cur_max_span = hits[0][1]

    for (d, span) in hits[1:]:
        if d == cur_end + timedelta(days=1):
            cur_end = d
            cur_max_span = max(cur_max_span, span)
        else:
            intervals.append(AlignmentHit(cur_start, cur_end, planets, cur_max_span))
            cur_start = d
            cur_end = d
            cur_max_span = span

    intervals.append(AlignmentHit(cur_start, cur_end, planets, cur_max_span))
    return intervals


def main() -> None:
    # 例：2026年〜2028年の間で、7惑星（地球除く）の直列っぽい期間を探す
    start_day = date(2026, 1, 1)
    end_day = date(2028, 12, 31)

    planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]

    # “直列”の厳しさ：10°以内に収まったら直列扱い（ここは好みで変えてOK）
    span_threshold_deg = 10.0

    intervals = list_planetary_alignments(start_day, end_day, planets, span_threshold_deg)

    if not intervals:
        print("No alignments found in the given window.")
    else:
        print(f"Found {len(intervals)} alignment interval(s) where span <= {span_threshold_deg}°")
        for itv in intervals:
            if itv.start == itv.end:
                print(f"{itv.start.isoformat()}  span<= {itv.max_span_deg:.2f}°")
            else:
                print(f"{itv.start.isoformat()} 〜 {itv.end.isoformat()}  span<= {itv.max_span_deg:.2f}°")


