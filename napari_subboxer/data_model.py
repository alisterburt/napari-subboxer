import numpy as np
from napari.utils.events import EventedModel
from pydantic import validator

from typing import Tuple, Optional


class SubParticlePose(EventedModel):
    """An object representing the pose of a subparticle.

    Vectors are xyz ordered.
    """
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

    @property
    def position_napari(self):
        return np.array([self.z, self.y, self.x])

    @property
    def x_vector_napari(self):
        if self.x_vector is None:
            return None
        vector_napari = np.asarray(self.x_vector, dtype=float)[::-1]
        return np.stack((self.position_napari, vector_napari), axis=0)

    @property
    def y_vector_napari(self):
        if self.y_vector is None:
            return None
        vector_napari = np.asarray(self.y_vector, dtype=float)[::-1]
        return np.stack((self.position_napari, vector_napari), axis=0)

    @property
    def z_vector_napari(self):
        if self.z_vector is None:
            return None
        vector_napari = np.asarray(self.z_vector, dtype=float)[::-1]
        return np.stack((self.position_napari, vector_napari), axis=0)

    def _initialise_xy_vectors(self):
        if self.z_vector is None:
            self.x_vector = (1, 0, 0)
            self.y_vector = (0, 1, 0)
            self.z_vector = (0, 0, 1)
            return
        if self.x_vector is None and self.y_vector is None:
            arbitrary_vector = np.array([1.23, 2.34, 3.45])
            self.x_vector = np.cross(self.z_vector, arbitrary_vector)
            self.y_vector = np.cross(self.z_vector, self.x_vector)
