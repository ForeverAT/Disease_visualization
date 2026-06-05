from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class Observation:
    x: float
    y: float
    date: datetime
    value: float


class DiseaseAlgorithm(ABC):
    @abstractmethod
    def compute(
        self,
        observations: list["Observation"],
        current_date: datetime,
        grid_x: np.ndarray,
        grid_y: np.ndarray,
    ) -> np.ndarray:
        """
        Returns a 2D float array (same shape as grid_x) with intensity values [0, 1].
        delta_t for each observation = current_date - observation.date (timedelta).
        """
        pass
