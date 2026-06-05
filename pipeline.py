import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from algorithm_base import Observation
from my_algorithm import GaussianDecayAlgorithm, SIGMA as _SIGMA

GRID_RESOLUTION = 50
INTENSITY_THRESHOLD = 0.01
PADDING_FRACTION = 0.20
MIN_PADDING_M = 3.5 * _SIGMA  # must cover the Gaussian tail: exp(−3.5²/2) ≈ 0.002
EARTH_RADIUS_M = 6_371_000.0


def _to_meters(lat: float, lng: float, clat: float, clng: float) -> tuple[float, float]:
    x = EARTH_RADIUS_M * math.radians(lng - clng) * math.cos(math.radians(clat))
    y = EARTH_RADIUS_M * math.radians(lat - clat)
    return x, y


def _to_latlon(x: float, y: float, clat: float, clng: float) -> tuple[float, float]:
    lat = math.degrees(y / EARTH_RADIUS_M) + clat
    lng = math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(clat)))) + clng
    return lat, lng


def load_observations(csv_path: str) -> tuple[list[Observation], float, float]:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    clat = float(df["lat"].mean())
    clng = float(df["lng"].mean())
    observations = []
    for _, row in df.iterrows():
        x, y = _to_meters(float(row["lat"]), float(row["lng"]), clat, clng)
        observations.append(Observation(
            x=x,
            y=y,
            date=datetime.strptime(str(row["date"]).strip(), "%Y-%m-%d"),
            value=float(row["value"]),
        ))
    return observations, clat, clng


def build_grid(
    observations: list[Observation],
    resolution: int = GRID_RESOLUTION,
) -> tuple[np.ndarray, np.ndarray]:
    xs = [o.x for o in observations]
    ys = [o.y for o in observations]
    x_pad = max((max(xs) - min(xs)) * PADDING_FRACTION, MIN_PADDING_M)
    y_pad = max((max(ys) - min(ys)) * PADDING_FRACTION, MIN_PADDING_M)
    x_lin = np.linspace(min(xs) - x_pad, max(xs) + x_pad, resolution)
    y_lin = np.linspace(min(ys) - y_pad, max(ys) + y_pad, resolution)
    return np.meshgrid(x_lin, y_lin)


def run_algorithm(
    algorithm,
    observations: list[Observation],
    date_range: list[datetime],
    grid_x: np.ndarray,
    grid_y: np.ndarray,
) -> list[dict]:
    results = []
    for current_date in date_range:
        obs_up_to = [o for o in observations if o.date <= current_date]
        if not obs_up_to:
            continue
        intensity = algorithm.compute(obs_up_to, current_date, grid_x, grid_y)
        date_str = current_date.strftime("%Y-%m-%d")
        rows, cols = np.where(intensity > INTENSITY_THRESHOLD)
        for r, c in zip(rows, cols):
            results.append({
                "date": date_str,
                "x": float(grid_x[r, c]),
                "y": float(grid_y[r, c]),
                "intensity": float(intensity[r, c]),
            })
    return results


def write_geojson(
    results: list[dict],
    output_path: str,
    clat: float,
    clng: float,
) -> None:
    features = []
    for row in results:
        lat, lng = _to_latlon(row["x"], row["y"], clat, clng)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {"date": row["date"], "intensity": row["intensity"]},
        })
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)


def run_pipeline(
    csv_path: str = "data/observations.csv",
    output_path: str = "output/spread.geojson",
) -> None:
    observations, clat, clng = load_observations(csv_path)
    grid_x, grid_y = build_grid(observations)

    min_date = min(o.date for o in observations)
    max_date = max(o.date for o in observations)
    date_range = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]

    results = run_algorithm(GaussianDecayAlgorithm(), observations, date_range, grid_x, grid_y)
    write_geojson(results, output_path, clat, clng)
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Wrote {len(results)} features over {len(date_range)} days → {output_path}"
    )


if __name__ == "__main__":
    run_pipeline()
