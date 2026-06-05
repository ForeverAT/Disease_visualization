# Disease Spread Visualizer

A lightweight tool for visualizing how a disease spreads across a city over time.  
You maintain a CSV of case observations — the tool watches it, runs your spread algorithm, and updates a live heatmap in the browser automatically.

![Demo — Hong Kong heatmap with time scrubber]

---

## How it works

```
observations.csv  →  pipeline.py  →  output/spread.geojson  →  index.html
       ↑                  ↑
  you edit this      watcher.py re-runs it on every save
```

- Each row in the CSV is one observation: a location, a date, and a case count.
- The pipeline projects coordinates to metres, runs the spread algorithm on a spatial grid, and writes a GeoJSON file.
- The browser polls that file every 3 seconds and re-renders the heatmap automatically.

---

## Quick start

**Requirements:** Python 3.10+

```bash
git clone <this-repo>
cd disease_visualization

pip install -r requirements.txt

# Terminal 1 — watch for CSV changes and re-run the pipeline
python watcher.py

# Terminal 2 — serve the viewer
python -m http.server 8000
```

Open **http://localhost:8000** in your browser.  
Edit `data/observations.csv`, save, and the map updates within 3 seconds.

> **Why `http.server`?** The viewer fetches `output/spread.geojson` via the browser's `fetch()` API, which blocks requests from `file://` URLs due to browser security (CORS). Serving over HTTP avoids this. You don't need any server-side logic — `python -m http.server` is enough.

---

## Input data format

Edit `data/observations.csv`. Each row is one observation event:

```
lat,lng,date,value
22.3193,114.1693,2024-01-01,8
22.2793,114.1851,2024-01-03,3
```

| Column | Format | Description |
|--------|--------|-------------|
| `lat`  | decimal degrees | Latitude, e.g. `22.3193` |
| `lng`  | decimal degrees | Longitude, e.g. `114.1693` |
| `date` | `YYYY-MM-DD` | Date the observation was recorded |
| `value` | positive number | Case count or intensity at that location |

**Tips:**
- Multiple rows for the same location on different dates are fine — this is how you build up a cluster over time.
- The same location reported multiple times nearby will accumulate intensity; an isolated single report stays dim. This is by design (see Algorithm below).
- To find lat/lng for any address: right-click in [Google Maps](https://maps.google.com) or [OpenStreetMap](https://openstreetmap.org) → copy coordinates.

### Sample datasets

**Hong Kong** (ships as default)

| District | lat | lng |
|----------|-----|-----|
| Mong Kok | 22.3193 | 114.1693 |
| Yau Ma Tei | 22.3124 | 114.1699 |
| Sham Shui Po | 22.3306 | 114.1627 |
| Tsim Sha Tsui | 22.2988 | 114.1722 |
| Causeway Bay | 22.2793 | 114.1851 |
| Wan Chai | 22.2796 | 114.1717 |
| Sha Tin | 22.3834 | 114.1868 |

**Taipei** — paste this into `data/observations.csv` to switch cities:

```
lat,lng,date,value
25.0478,121.5319,2024-03-01,8
25.0330,121.5654,2024-03-03,5
25.0413,121.5701,2024-03-05,3
25.0280,121.5136,2024-03-06,6
25.0630,121.5231,2024-03-08,4
25.0170,121.4633,2024-03-10,2
25.0478,121.5319,2024-03-10,7
25.0330,121.5654,2024-03-12,8
```

| District | lat | lng |
|----------|-----|-----|
| Zhongzheng (Main Station) | 25.0478 | 121.5319 |
| Songshan | 25.0330 | 121.5654 |
| Xinyi | 25.0413 | 121.5701 |
| Da'an | 25.0280 | 121.5136 |
| Datong | 25.0630 | 121.5231 |
| Banqiao | 25.0170 | 121.4633 |

The map automatically centers and zooms to fit your data on first load.

---

## Algorithm

The default algorithm (`my_algorithm.py`) models spread as a **Gaussian decay in space and time**, with a clustering effect: isolated single reports appear faint; areas with multiple nearby reports over time build up to a bright hotspot.

```
raw(P) = Σ  value × exp(−distance² / 2σ²) × exp(−Δt / τ)
intensity(P) = clip(raw / SATURATION, 0, 1) ^ POWER
```

Four tunable constants at the top of `my_algorithm.py`:

| Constant | Default | What it controls |
|----------|---------|-----------------|
| `SIGMA` | `800.0` m | Spatial spread radius per case (~1 city block = 200 m, district = 1 km) |
| `TAU` | `7.0` days | How fast past cases lose weight (7 = weekly decay, 14 = fortnightly) |
| `SATURATION` | `15.0` | The accumulated raw score that saturates to full intensity. Set to ~3–5× a typical single `value` so isolated reports are faint and clusters of 4–6 reports turn bright. |
| `POWER` | `1.2` | Amplification exponent. Values > 1 suppress isolated cases relative to clusters. `1.2` is gentle; `2.0` is aggressive. |

---

## Plug in your own algorithm

Subclass `DiseaseAlgorithm` in any file:

```python
# my_algorithm.py  (or a new file)
from algorithm_base import DiseaseAlgorithm, Observation
import numpy as np
from datetime import datetime

class MyAlgorithm(DiseaseAlgorithm):
    def compute(
        self,
        observations: list[Observation],  # all cases up to current_date
        current_date: datetime,
        grid_x: np.ndarray,               # 2D meshgrid, metres (local projection)
        grid_y: np.ndarray,
    ) -> np.ndarray:
        # Return a 2D float array in [0, 1], same shape as grid_x
        ...
```

`Observation` fields: `.x`, `.y` (metres, local tangent-plane projection), `.date` (datetime), `.value` (float).

If you put your class in a different file, update the import in `pipeline.py`:

```python
from your_file import MyAlgorithm as GaussianDecayAlgorithm
```

---

## One-shot mode

Run the pipeline once without watching:

```bash
python watcher.py --once
```

---

## File structure

```
disease_visualization/
├── watcher.py          # Watches observations.csv, re-runs pipeline on save (1 s debounce)
├── pipeline.py         # CSV → local projection → algorithm → GeoJSON
├── algorithm_base.py   # Observation dataclass + DiseaseAlgorithm abstract base class
├── my_algorithm.py     # Default Gaussian decay algorithm (edit or replace this)
├── index.html          # Browser viewer: MapLibre GL map + Deck.gl heatmap overlay
├── requirements.txt
├── data/
│   └── observations.csv   # ← your input data goes here
└── output/
    └── spread.geojson     # auto-generated, do not edit
```

---

## Tech stack

| Layer | Library |
|-------|---------|
| Pipeline | Python · pandas · numpy |
| File watching | watchdog |
| Base map | [MapLibre GL JS](https://maplibre.org) + CARTO dark-matter tiles (free, no API key) |
| Heatmap overlay | [Deck.gl](https://deck.gl) BitmapLayer |
| Coordinate projection | Equirectangular local tangent plane (accurate to < 0.1 % for city-scale areas) |
