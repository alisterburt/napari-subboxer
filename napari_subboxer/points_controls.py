from typing import Callable, Optional

import napari.layers

from .interactivity_utils import point_in_bounding_box


def add_point(
        viewer,
        event,
        points_layer: napari.layers.Points = None,
        plane_layer: napari.layers.Image = None,
        append: bool = True,
        callback: Optional[Callable] = None,
):
    # Early exit if not alt-clicked
    if 'Alt' not in event.modifiers:
        return

    # Early exit if volume_layer isn't visible
    if not plane_layer.visible:
        return

    # Ensure added points will be visible until plane depth is sorted
    points_layer.blending = 'translucent_no_depth'

    # Calculate intersection of click with plane through data in data coordinates
    intersection = plane_layer.experimental_slicing_plane.intersect_with_line(
        line_position=viewer.cursor.position, line_direction=viewer.cursor._view_direction
    )

    # Check if click was on plane by checking if intersection occurs within
    # data bounding box. If not, exit early.
    if not point_in_bounding_box(intersection, plane_layer.extent.data):
        return

    if append:
        points_layer.add(intersection)
    else:
        points_layer.data = intersection
        # points_layer.add(intersection)


    if callback is not None:
        callback()