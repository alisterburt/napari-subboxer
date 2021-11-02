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


class SubboxerMode(StringEnum):
    ADD = auto()
    DEFINE_Z_AXIS = auto()
    ROTATE_IN_PLANE = auto()


class Subboxer:
    plane_thickness_changed = Signal(float)
    mode_changed = Signal(str)

    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        self.viewer.dims.ndisplay = 3

        self.volume_layer: Optional[napari.layers.Image] = None
        self.plane_layer: Optional[napari.layers.Image] = None
        self.bounding_box_layer: Optional[napari.layers.Points] = None
        self.transformations_layer: Optional[napari.layers.Points] = None

        self.mode: SubboxerMode = SubboxerMode.ADD
        self._active_transformation_index: int = 0

    @property
    def n_transformations(self):
        if self.transformations_layer is None:
            return 0
        return len(self.transformations_layer.data)

    @property
    def active_transformation_index(self):
        return self._active_transformation_index

    @active_transformation_index.setter
    def active_transformation_index(self, value: int):
        if value > self.n_transformations - 1:
            value -= self.n_transformations
        elif value < 0:
            value = self.n_transformations + value
        self._active_transformation_index = value
        self._select_active_transformation()
        self._center_camera_on_active_transformation()

    def next_transformation(self):
        self.active_transformation_index += 1

    def previous_transformation(self):
        self.active_transformation_index -= 1

    @property
    def _active_transformation_position(self):
        return self.transformations_layer.data[self.active_transformation_index]

    def _center_camera_on_active_transformation(self):
        if self.mode in (SubboxerMode.DEFINE_Z_AXIS,
                         SubboxerMode.ROTATE_IN_PLANE):
            self.viewer.camera.center = self._active_transformation_position

    def _select_active_transformation(self):
        self.transformations_layer.selected_data = [
            self.active_transformation_index
        ]

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value: SubboxerMode):
        self._mode = SubboxerMode(value)
        self.mode_changed.emit(str(self.mode))

    def activate_add_mode(self):
        self.mode = SubboxerMode.ADD

    def activate_define_z_mode(self):
        self.mode = SubboxerMode.DEFINE_Z_AXIS

    def activate_rotate_in_plane_mode(self):
        self.mode = SubboxerMode.ROTATE_IN_PLANE

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
            name='map',
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
                layer=self.plane_layer,
                axis=key
            )
            self.viewer.bind_key(key, callback)

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

        # plane thickness event emission
        self.plane_layer.experimental_slicing_plane.events.thickness.connect(
            partial(self.plane_thickness_changed.emit, self.plane_thickness)
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

        # add point for defining z-axis

    def disconnect_callbacks(self):
        self.viewer.mouse_drag_callbacks.remove(self._shift_plane_callback)
        self.viewer.mouse_drag_callbacks.remove(self._add_point_callback)
        for key in 'xyzo[]':
            self.viewer.keymap.pop(key.upper())

