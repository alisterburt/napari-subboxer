from enum import auto
from functools import partial
from typing import Optional, Sequence, List, Dict

import mrcfile
import napari
import napari.layers
import numpy as np
from napari.utils.misc import StringEnum
from psygnal import Signal

from .plane_controls import shift_plane_along_normal, set_plane_normal_axis, \
    orient_plane_perpendicular_to_camera
from .points_controls import add_point
from .data_model import SubParticlePose


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

        self.subparticles: Dict[int, SubParticlePose] = {}

        self.volume_layer: Optional[napari.layers.Image] = None
        self.plane_layer: Optional[napari.layers.Image] = None
        self.bounding_box_layer: Optional[napari.layers.Points] = None
        self.subparticles_layer: Optional[napari.layers.Points] = None
        self.current_subparticle_z_layer: Optional[napari.layers.Points] = None

        self.mode: SubboxerMode = SubboxerMode.ADD
        self._active_transformation_index: int = 0
        self._volume_center: Optional[int] = None

    @property
    def n_transformations(self):
        if self.subparticles_layer is None:
            return 0
        return len(set(self.subparticles_layer.properties['id']))

    @property
    def active_subparticle_id(self):
        idx = self.subparticles_layer.selected_data
        active_subparticle_id = self.subparticles_layer.properties['id'][idx]
        return active_subparticle_id

    @active_subparticle_id.setter
    def active_subparticle_id(self, value: int):
        if value > self.n_transformations - 1:
            value -= self.n_transformations
        elif value < 0:
            value = self.n_transformations + value
        self.subparticles_layer.selected_data = [value]
        self._select_active_transformation()
        self._center_camera_on_active_transformation()

    @property
    def _next_subparticle_id(self):
        return np.max(self.subparticles_layer.properties['id']) + 1

    def next_subparticle(self):
        self.active_subparticle_id += 1

    def previous_subparticle(self):
        self.active_subparticle_id -= 1

    @property
    def _active_subparticle_center(self):
        return self.subparticles_layer.data[self.active_subparticle_id]

    def _center_camera_on_active_transformation(self):
        if self.mode in (SubboxerMode.DEFINE_Z_AXIS,
                         SubboxerMode.ROTATE_IN_PLANE):
            self.viewer.camera.center = self._active_subparticle_center
            self.viewer.camera.zoom = 3

    def _select_active_transformation(self):
        self.subparticles_layer.selected_data = [
            self.active_subparticle_id
        ]

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value: SubboxerMode):
        self._mode = SubboxerMode(value)
        self.mode_changed.emit(str(self.mode))

    def _on_mode_change(self):
        self._center_camera_on_active_transformation()

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

    def open_map(self, map_file: str):
        with mrcfile.open(map_file) as mrc:
            tomogram = mrc.data
        self.add_volume_layer(tomogram)
        self.add_plane_layer(tomogram)
        self.add_subparticles_layer()
        self.add_current_subparticle_z_layer()
        self.add_bounding_box_layer()

        self._volume_center = np.array(tomogram.shape) / 2
        self.connect_callbacks()

        self.viewer.reset_view()
        self.viewer.camera.angles = (140, -55, -140)
        self.viewer.camera.zoom = 0.8
        self.viewer.layers.selection.active = self.volume_layer

    def close_map(self):
        self.disconnect_callbacks()
        self.viewer.layers.remove(self.volume_layer)
        self.viewer.layers.remove(self.bounding_box_layer)

    def add_volume_layer(self, data: np.ndarray):
        self.volume_layer = self.viewer.add_image(
            data=data,
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

    def add_subparticles_layer(self):
        self.subparticles_layer = self.viewer.add_points(
            name='subparticles',
            data=[0, 0, 0],  # adding point to initialise properties correctly
            properties={'id': [0]},
            ndim=3,
            face_color='magenta',
            n_dimensional=True
        )
        # remove fake point, properties are preserved
        self.subparticles_layer.selected_data = [0]
        self.subparticles_layer.remove_selected()

    def add_current_subparticle_z_layer(self):
        self.current_subparticle_z_layer = self.viewer.add_points(
            name='current subparticle z',
            ndim=3,
            face_color='green',
            n_dimensional=True
        )

    def add_bounding_box_layer(self):
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

    def if_add_mode_enabled(self, func):
        def inner(*args, **kwargs):
            if self.mode == SubboxerMode.ADD:
                return func(*args, **kwargs)

        return inner

    def if_define_z_mode_enabled(self, func):
        def inner(*args, **kwargs):
            if self.mode == SubboxerMode.DEFINE_Z_AXIS:
                return func(*args, **kwargs)

        return inner

    def if_in_plane_mode_enabled(self, func):
        def inner(*args, **kwargs):
            if self.mode == SubboxerMode.DEFINE_Z_AXIS:
                return func(*args, **kwargs)

        return inner

    def _on_add_subparticle_center(self):
        current_subparticle_id = int(self.active_subparticle_id)

        # update id for next particle
        self.subparticles_layer.current_properties['id'] += 1

        # create subparticle and add to dict of subparticles
        shifts = self._active_subparticle_center - self._volume_center
        subparticle = SubParticlePose(
            dx=shifts[-1], dy=shifts[-2], dz=shifts[0]
        )
        self.subparticles[current_subparticle_id] = subparticle

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

        # plane orientation (camera)
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

        # add subparticle (in add mode)
        self._add_subparticle_callback = partial(
            self.if_add_mode_enabled(add_point),
            points_layer=self.subparticles_layer,
            plane_layer=self.plane_layer,
            callback=self._on_add_subparticle_center,
        )
        self.viewer.mouse_drag_callbacks.append(
            self._add_subparticle_callback
        )

        # add point for defining z-axis
        self._define_z_axis_callback = partial(
            self.if_define_z_mode_enabled(add_point),
            points_layer=self.current_subparticle_z_layer,
            plane_layer=self.plane_layer,
        )
        self.viewer.mouse_drag_callbacks.append(
            self._define_z_axis_callback
        )

    def disconnect_callbacks(self):
        self.viewer.mouse_drag_callbacks.remove(self._shift_plane_callback)
        self.viewer.mouse_drag_callbacks.remove(
            self._add_subparticle_callback)
        for key in 'xyzo[]':
            self.viewer.keymap.pop(key.upper())
