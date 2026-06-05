import math
import numpy as np
from datetime import datetime

from algorithm_base import DiseaseAlgorithm, Observation

SIGMA      = 800.0   # spatial decay radius, metres
TAU        = 7.0     # temporal decay, days
SATURATION = 15.0    # accumulated raw score that maps to intensity 1.0
POWER      = 1.2     # amplification exponent
# How to tune these four knobs:
#   SIGMA      — how far one case "spreads" visually (~urban block = 300 m, district = 1 km)
#   TAU        — how quickly old cases lose weight (7 d = weekly; 14 d = fortnightly)
#   SATURATION — set to ~3-5× a typical single observation value so isolated cases are
#                faint and a cluster of 4-6 nearby reports fully saturates to 1.0
#   POWER      — >1 suppresses isolated reports relative to dense clusters;
#                1.2 is a gentle curve, 2.0 is aggressive


class GaussianDecayAlgorithm(DiseaseAlgorithm):
    def compute(
        self,
        observations: list[Observation],
        current_date: datetime,
        grid_x: np.ndarray,
        grid_y: np.ndarray,
    ) -> np.ndarray:
        raw = np.zeros_like(grid_x, dtype=float)

        for obs in observations:
            dist_sq  = (grid_x - obs.x) ** 2 + (grid_y - obs.y) ** 2
            delta_t  = max((current_date - obs.date).days, 0)
            spatial  = np.exp(-dist_sq / (2.0 * SIGMA ** 2))
            temporal = math.exp(-delta_t / TAU)
            raw     += obs.value * spatial * temporal

        # No global normalisation: the absolute raw score determines intensity.
        # A single isolated report with value=V stays at V/SATURATION (dim).
        # Multiple nearby reports accumulate toward SATURATION (bright).
        clipped = np.clip(raw / SATURATION, 0.0, 1.0)
        return np.power(clipped, POWER)
