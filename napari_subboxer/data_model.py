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

    def as_vectors_data(self):
        position = np.array([self.z, self.y, self.x])
        x_vector = np.asarray(self.x_vector, dtype=float)[::-1] if \
            self.x_vector is not None else None
        y_vector = np.asarray(self.y_vector, dtype=float)[::-1] if \
            self.y_vector is not None else None
        z_vector = np.asarray(self.z_vector, dtype=float)[::-1] if \
            self.z_vector is not None else None

        xyz_vectors_napari = [
            np.stack((position, vector), axis=0)
            if (vector is not None)
            else None
            for vector
            in (x_vector, y_vector, z_vector)
        ]
        return xyz_vectors_napari
