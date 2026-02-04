from datetime import date, timedelta
from typing import List

import matplotlib.pyplot as plt
import requests

from ecliptic.basic_scan import (
    PLANET_IDS,
    _circular_span_deg,
    fetch_geocentric_ecliptic_longitude,
)


def compute_spans(
    start_day: date, end_day: date, planets: List[str]
) -> tuple[list[date], list[float]]:
    """
    指定期間について、各日の最小スパン（全惑星が収まる最小弧の長さ）を計算する。
    """
    for p in planets:
        if p not in PLANET_IDS:
            raise ValueError(f"Unknown planet name: {p}")

    days: list[date] = []
    spans: list[float] = []

    with requests.Session() as sess:
        d = start_day
        while d <= end_day:
            lons = []
            for p in planets:
                lon = fetch_geocentric_ecliptic_longitude(
                    PLANET_IDS[p], d, session=sess
                )
                lons.append(lon)

            span = _circular_span_deg(lons)
            days.append(d)
            spans.append(span)

            d += timedelta(days=1)

    return days, spans


def main() -> None:
    # 可視化する期間と惑星をここで指定します。
    start_day = date(2026, 1, 1)
    end_day = date(2028, 12, 31)
    planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]

    span_threshold_deg = 10.0

    print(
        f"Computing minimal span for {len(planets)} planets "
        f"from {start_day} to {end_day} ..."
    )
    days, spans = compute_spans(start_day, end_day, planets)

    print("Plotting ...")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(days, spans, marker="o", markersize=2, linewidth=0.8, label="span (deg)")
    ax.axhline(
        span_threshold_deg,
        color="red",
        linestyle="--",
        linewidth=1,
        label=f"threshold = {span_threshold_deg}°",
    )

    ax.set_ylabel("Minimal span (deg)")
    ax.set_xlabel("Date")
    ax.set_title("Planetary alignment span over time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()

