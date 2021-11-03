import numpy as np
from napari.utils.events import EventedModel
from pydantic import validator

from typing import Tuple, Optional


class SubParticlePose(EventedModel):
    x: float
    y: float
    z: float
    x_vector: Optional[Tuple[float, float, float]] = None
    y_vector: Optional[Tuple[float, float, float]] = None
    z_vector: Optional[Tuple[float, float, float]] = None

    @validator('x_vector', 'y_vector', 'z_vector', pre=True)
    def normalise_vector(cls, value):
        if value is None:
            return value
        return tuple(np.asarray(value) / np.linalg.norm(value))