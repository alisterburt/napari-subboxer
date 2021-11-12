from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Callable
import numpy as np
from .interactivity_utils import theta2rotz

if TYPE_CHECKING:
    from .subboxer import Subboxer
    from napari import Viewer
    from napari.utils.events import Event


def update_in_plane_rotation(
        viewer: Viewer,
        event: Event,
        subboxer: Subboxer = None,
        callback: Optional[Callable] = None
):
    # only if alt clicked
    if 'Alt' not in event.modifiers:
        return

    # disable interactivity of selected layer
    viewer.layers.selection.active = viewer.layers[0]
    viewer.layers.selection.active.interactive = False

    # get necessary info from active subparticle
    active_subparticle = subboxer.active_subparticle
    active_subparticle._initialise_xy_vectors()
    subparticle_rotation_matrix = np.column_stack((
        active_subparticle.x_vector,
        active_subparticle.y_vector,
        active_subparticle.z_vector
    ))
    original_x_vector = np.array(active_subparticle.x_vector).reshape((3, 1))

    mouse_dragged = False
    start_position = np.copy(event.position)
    yield
    while event.type == 'mouse_move':
        drag_vector = event.position - start_position
        if np.all(drag_vector == 0):
            magnitude = 0
        else:
            magnitude = np.linalg.norm(drag_vector)
            mouse_dragged = True
        # print(magnitude)
        rotz = theta2rotz(magnitude * 25)
        rotm = subparticle_rotation_matrix @ rotz @ np.linalg.pinv(subparticle_rotation_matrix)
        active_subparticle.x_vector = rotm @ original_x_vector
        active_subparticle.y_vector = np.cross(
            active_subparticle.z_vector, active_subparticle.x_vector
        )
        subboxer.populate_subparticle_vectors_layers()
        print(active_subparticle.y_vector)
        yield
    viewer.layers.selection.active.interactive = True
