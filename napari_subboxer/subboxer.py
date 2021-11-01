from enum import auto
from functools import partial
from typing import Optional

import mrcfile
import napari
import napari.layers
import numpy as np
from napari.utils.misc import StringEnum
from psygnal import Signal

from .plane_controls import shift_plane_along_normal, set_plane_normal_axis, \
    orient_plane_perpendicular_to_camera
from .points_controls import add_point


class RenderingMode(StringEnum):
    VOLUME = auto()
    PLANE = auto()


class Subboxer:
    plane_thickness_changed = Signal(float)
    rendering_mode_changed = Signal(str)

    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        self.viewer.dims.ndisplay = 3
        self.volume_layer: Optional[napari.layers.Image] = None
        self.plane_layer: Optional[napari.layers.Image] = None
        self.bounding_box_layer: Optional[napari.layers.Points] = None

    @property
    def plane_thickness(self):
        return self.plane_layer.experimental_slicing_plane.thickness

    @plane_thickness.setter
    def plane_thickness(self, value):
        self.plane_layer.experimental_slicing_plane.thickness = value
        self.plane_thickness_changed.emit()

    def increase_plane_thickness(self, event=None):
        self.plane_layer.experimental_slicing_plane.thickness += 1
        self.plane_thickness_changed.emit()

    def decrease_plane_thickness(self, event=None):
        self.plane_layer.experimental_slicing_plane.thickness -= 1
        self.plane_thickness_changed.emit()

    def open_reconstruction(self, tomogram_file: str):
        with mrcfile.open(tomogram_file) as mrc:
            tomogram = mrc.data
        self.add_volume_layer(tomogram)
        self.add_plane_layer(tomogram)
        self.add_transformations_layer()
        self.add_bounding_box()
        self.connect_callbacks()
        self.viewer.reset_view()
        self.viewer.camera.angles = (140, -55, -140)
        self.viewer.camera.zoom = 0.8
        self.viewer.layers.selection.active = self.volume_layer

    def close_reconstruction(self):
        self.disconnect_callbacks()
        self.viewer.layers.remove(self.volume_layer)
        self.viewer.layers.remove(self.bounding_box_layer)

    def add_volume_layer(self, reconstruction: np.ndarray):
        self.volume_layer = self.viewer.add_image(
            data=reconstruction,
            name='reconstruction',
            colormap='gray',
            rendering='mip',
        )

    def add_plane_layer(self, reconstruction: np.ndarray):
        plane_parameters = {
            'enabled': True,
            'position': np.array(reconstruction.shape) / 2,
            'normal': (1, 0, 0),
            'thickness': 5,
        }
        self.plane_layer = self.viewer.add_image(
            data=reconstruction,
            name='plane',
            colormap='magenta',
            gamma=2.0,
            rendering='mip',
            blending='additive',
            experimental_slicing_plane=plane_parameters
        )

    def add_transformations_layer(self):
        self.transformations_layer = self.viewer.add_points(
            name='transformations',
            ndim=3,
            face_color='magenta',
            n_dimensional=True
        )

    def add_bounding_box(self):
        bounding_box_max = self.volume_layer.data.shape
        bounding_box_points = np.array(
            [
                [0, 0, 0],
                [0, 0, bounding_box_max[2]],
                [0, bounding_box_max[1], 0],
                [bounding_box_max[0], 0, 0],
                [bounding_box_max[0], bounding_box_max[1], 0],
                [bounding_box_max[0], 0, bounding_box_max[2]],
                [0, bounding_box_max[1], bounding_box_max[2]],
                [bounding_box_max[0], bounding_box_max[1], bounding_box_max[2]]
            ]
        )
        self.bounding_box_layer = self.viewer.add_points(
            data=bounding_box_points,
            name='bounding box',
            blending='opaque',
            face_color='cornflowerblue',
            edge_color='black',
            edge_width=2,
            size=10,
        )

    def connect_callbacks(self):
        # plane click and drag
        self._shift_plane_callback = partial(
            shift_plane_along_normal,
            layer=self.plane_layer
        )
        self.viewer.mouse_drag_callbacks.append(
            self._shift_plane_callback
        )

        # plane orientation (ortho)
        for key in 'xyz':
            callback = partial(
                set_plane_normal_axis,
                layer=self.volume_layer,
                axis=key
            )
            self.viewer.bind_key(key, callback)


        self.volume_layer.experimental_slicing_plane.events.thickness.connect(
            partial(self.plane_thickness_changed.emit, self.plane_thickness)
        )

        # plane orientation(camera)
        self._orient_plane_callback = partial(
            orient_plane_perpendicular_to_camera,
            layer=self.plane_layer
        )
        self.viewer.bind_key('o', self._orient_plane_callback)

        # plane thickness (buttons)
        self.viewer.bind_key(
            '[', self.decrease_plane_thickness
        )
        self.viewer.bind_key(
            ']', self.increase_plane_thickness
        )

        # add point in points layer on alt-click
        self._add_point_callback = partial(
            add_point,
            points_layer=self.transformations_layer,
            plane_layer=self.plane_layer
        )
        self.viewer.mouse_drag_callbacks.append(
            self._add_point_callback
        )

    def disconnect_callbacks(self):
        self.viewer.mouse_drag_callbacks.remove(self._shift_plane_callback)
        self.viewer.mouse_drag_callbacks.remove(self._add_point_callback)
        for key in 'xyzo[]':
            self.viewer.keymap.pop(key.upper())

