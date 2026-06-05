# Disease Spread Visualizer — Build Spec

## Overview

A lightweight tool for a disease control researcher to visualize how disease spreads over time across a 2D spatial area. The researcher updates a CSV with new observations (location + date + intensity), runs the tool, and a browser-based map animates the spread. The core spread algorithm is pluggable — the researcher provides his own.

---

## Workflow

1. Researcher edits `data/observations.csv` (adds new rows)
2. `watcher.py` detects the file change and automatically re-runs the pipeline
3. `algorithm.py` reads the observations, runs the spread algorithm, writes `output/spread.geojson`
4. Kepler.gl (loaded in `index.html`) picks up the new file and updates the visualization

No clicking to place points. No manual refresh needed.

---

## File Structure

```
disease_viz/
├── watcher.py            # Watches CSV, triggers pipeline on change
├── pipeline.py           # Orchestrates: load CSV → run algorithm → write GeoJSON
├── algorithm_base.py     # DiseaseAlgorithm abstract base class
├── my_algorithm.py       # Researcher's pluggable algorithm (placeholder ships here)
├── index.html            # Kepler.gl viewer, loads output/spread.geojson
├── requirements.txt
├── data/
│   └── observations.csv  # Input: x_m, y_m, date, value
└── output/
    └── spread.geojson    # Output: intensity field consumed by Kepler.gl
```

---

## Data Format

### Input — `data/observations.csv`

```
x_m, y_m, date, value
0.0, 0.0, 2024-01-01, 10
150.0, 200.0, 2024-01-03, 4
-100.0, 80.0, 2024-01-06, 7
```

- `x_m`, `y_m`: coordinates in **meters**, arbitrary origin, can be negative
- `date`: ISO 8601 date string (`YYYY-MM-DD`)
- `value`: case count or intensity (float)

### Output — `output/spread.geojson`

A GeoJSON FeatureCollection of points. Each feature represents one cell of the computed intensity grid at one time step. Fields:

```json
{
  "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [x_m, y_m] },
  "properties": {
    "date": "2024-01-05",
    "intensity": 0.73
  }
}
```

Kepler.gl uses `date` for the time filter and `intensity` for the heatmap color scale.

---

## Algorithm Interface

### `algorithm_base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class Observation:
    x: float          # meters
    y: float          # meters
    date: datetime
    value: float

class DiseaseAlgorithm(ABC):
    @abstractmethod
    def compute(
        self,
        observations: list[Observation],  # all observations up to current_date
        current_date: datetime,            # date being evaluated
        grid_x: np.ndarray,                # 2D meshgrid, meters
        grid_y: np.ndarray,                # 2D meshgrid, meters
    ) -> np.ndarray:
        """
        Returns a 2D float array (same shape as grid_x) with intensity values [0, 1].
        delta_t for each observation = current_date - observation.date (timedelta).
        """
        pass
```

### `my_algorithm.py` — Placeholder (ships with the project)

Implement a simple Gaussian decay as a working default so the app runs immediately:

```
intensity at point P = sum over all observations of:
    observation.value * exp(-distance(P, obs)^2 / (2 * sigma^2)) * exp(-delta_t.days / tau)
```

Use `sigma = 100.0` (meters) and `tau = 7.0` (days) as defaults, configurable at the top of the file. Normalize the output to [0, 1].

The researcher replaces this file with his own subclass without touching anything else.

---

## Pipeline — `pipeline.py`

```
load_observations(csv_path)
  → parse with pandas, return list[Observation]

build_grid(observations, resolution=50)
  → compute bounding box from observation coordinates + 20% padding
  → create meshgrid with `resolution` points per axis
  → return grid_x, grid_y (2D numpy arrays)

run_algorithm(algorithm, observations, date_range, grid_x, grid_y)
  → for each date in date_range (daily steps):
      call algorithm.compute(obs_up_to_date, current_date, grid_x, grid_y)
      collect (date, x, y, intensity) for all grid points where intensity > threshold (0.01)
  → return list of result rows

write_geojson(results, output_path)
  → write as GeoJSON FeatureCollection

date_range = from earliest observation date to latest observation date
```

Grid resolution should be configurable (default 50×50). Keeping it coarse is fine — Kepler.gl interpolates for display.

---

## Watcher — `watcher.py`

Use the `watchdog` library to monitor `data/observations.csv`. On any modification event, call `pipeline.py` end-to-end and print a timestamped log line. Debounce by 1 second to avoid double-triggers on rapid saves.

Start with: `python watcher.py`

Also support a one-shot mode: `python watcher.py --once` (runs pipeline once and exits, no watching).

---

## Viewer — `index.html`

A single self-contained HTML file that:
- Loads Kepler.gl from CDN
- On page load, fetches `output/spread.geojson` via `fetch()`
- Configures a heatmap layer using `intensity` as the weight field
- Enables Kepler.gl's built-in time filter on the `date` field so the researcher can scrub or play through the timeline
- Sets color scale: low intensity = blue, high = red

The page should auto-poll `output/spread.geojson` every 3 seconds and reload the layer if the file has changed (compare last-modified header). This way the browser updates automatically when the watcher re-runs the pipeline.

---

## Requirements — `requirements.txt`

```
pandas
numpy
scipy
watchdog
```

No Flask or server needed — Kepler.gl loads the GeoJSON as a local fetch. Note: the researcher will need to serve the folder locally (e.g. `python -m http.server 8000`) due to browser CORS restrictions on `file://` — add a note about this in a README.

---

## What NOT to build

- No GUI for adding data points (researcher edits CSV directly)
- No authentication, no database
- No server-side API
- No coordinate projection (stay in meters, no lat/lon conversion)

---

## Deliverable

Working project folder. Run `python watcher.py`, open `http://localhost:8000`, update the CSV, and the map updates within a few seconds. The placeholder algorithm should produce a visible heatmap on the sample data.