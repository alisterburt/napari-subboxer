from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .data_model import SubParticlePose
    from .subboxer import Subboxer
    from napari import Viewer
    from napari.utils.events import Event


def update_in_plane_rotation(viewer: Viewer, event: Event, subboxer: Subboxer = None):
    # disable interactivity of selected layer
    viewer.layers.selection.active.interactive = False

    mouse_dragged = False
    start_position = np.copy(event.position)
    yield
    while event.type == 'mouse_move':
        drag_vector = event.position - start_position
        magnitude = drag_vector / np.linalg.norm(drag_vector)
        mouse_dragged = True
        print(magnitude)
        yield
    if mouse_dragged:
        print(magnitude)
    else:
        print('clicked!')
