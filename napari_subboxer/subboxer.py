from enum import auto
from functools import partial, reduce
from typing import Optional, Dict

import mrcfile
import napari
import napari.layers
import numpy as np
from napari.utils.misc import StringEnum
from psygnal import Signal
import eulerangles
import pandas as pd
import starfile

from .data_model import SubParticlePose
from .layer_utils import reset_contrast_limits
from .oriented_points_controls import update_in_plane_rotation
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
    active_subparticle_changed = Signal(int)

    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        self.viewer.dims.ndisplay = 3

        self.subparticles: Dict[int, SubParticlePose] = {}

        self.volume_layer: napari.layers.Image = self.create_volume_layer()
        self.plane_layer: napari.layers.Image = self.create_plane_layer()
        self.bounding_box_layer: napari.layers.Points = self.create_bounding_box_layer()
        self.subparticles_layer: napari.layers.Points = self.create_subparticles_layer()
        self.current_subparticle_z_layer: napari.layers.Points = self.create_current_subparticle_z_layer()
        self.subparticle_z_vectors_layer = \
            self.create_subparticle_z_vectors_layer()
        self.subparticle_y_vectors_layer = \
            self.create_subparticle_y_vectors_layer()
        self.subparticle_x_vectors_layer = \
            self.create_subparticle_x_vectors_layer()

        self.mode: SubboxerMode = SubboxerMode.ADD
        self._active_transformation_index: int = 0
        self._volume_center: Optional[int] = None

    @property
    def n_subparticles(self):
        return len(self.subparticle_ids)

    @property
    def subparticle_ids(self):
        return np.sort(np.unique(self.subparticles_layer.properties['id']))

    @property
    def active_subparticle_id(self):
        # active subparticle is defined by selection of point in napari
        if self.n_subparticles == 0:
            return 0
        idx = next(iter(self.subparticles_layer.selected_data))
        return self.subparticles_layer.properties['id'][idx]

    @active_subparticle_id.setter
    def active_subparticle_id(self, id: int):
        # find data index of active subparticle
        idx = list(self.subparticles_layer.properties['id']).index(id)
        self.subparticles_layer.selected_data = [idx]
        self.active_subparticle_changed.emit(id)
        self._on_active_subparticle_change()

    @property
    def active_subparticle(self):
        return self.subparticles[self.active_subparticle_id]

    @property
    def _next_subparticle_id(self):
        return np.max(self.subparticle_ids) + 1

    def next_subparticle(self, event=None):
        current_idx = list(self.subparticle_ids).index(
            self.active_subparticle_id
        )
        next_idx = (current_idx + 1) % self.n_subparticles
        self.active_subparticle_id = self.subparticle_ids[next_idx]

    def previous_subparticle(self, event=None):
        current_idx = list(self.subparticle_ids).index(
            self.active_subparticle_id
        )
        next_idx = (current_idx - 1) % self.n_subparticles
        self.active_subparticle_id = self.subparticle_ids[next_idx]

    @property
    def _active_subparticle_center(self):
        return tuple(self.subparticles_layer.data[self.active_subparticle_id])

    @property
    def _active_subparticle_z_point(self):
        return tuple(self.current_subparticle_z_layer.data[0])

    def _on_active_subparticle_change(self):
        if self.mode in (SubboxerMode.DEFINE_Z_AXIS,
                         SubboxerMode.ROTATE_IN_PLANE):
            self.viewer.camera.center = self._active_subparticle_center
            self.viewer.camera.zoom = 5
        if self.mode == SubboxerMode.ROTATE_IN_PLANE:
            self.plane_layer.visible = False
        else:
            self.plane_layer.visible = True
        self.current_subparticle_z_layer.visible = False

    def _select_active_transformation_in_viewer(self):
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
        self._on_active_subparticle_change()

    def activate_add_mode(self):
        self.mode = SubboxerMode.ADD
        self.viewer.camera.center = self._volume_center
        self._on_mode_change()

    def activate_define_z_mode(self):
        self.mode = SubboxerMode.DEFINE_Z_AXIS
        self._on_mode_change()

    def activate_rotate_in_plane_mode(self):
        self.mode = SubboxerMode.ROTATE_IN_PLANE
        self._on_mode_change()

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
            map = mrc.data
        normalised_map = (map - np.mean(map)) / np.std(map)

        self.volume_layer.data = normalised_map
        self.plane_layer.data = normalised_map
        self._volume_center = np.array(map.shape) / 2
        self.plane_layer.experimental_slicing_plane.position = self._volume_center
        self.update_bounding_box()

        for layer in self.volume_layer, self.plane_layer:
            layer.visible = True
            reset_contrast_limits(layer)

        self.connect_callbacks()
        self.viewer.reset_view()
        self.viewer.camera.angles = (140, -55, -140)
        self.viewer.camera.zoom = 0.8
        self.viewer.layers.selection.active = self.volume_layer

    def close_map(self):
        self.disconnect_callbacks()
        self.viewer.layers.remove(self.volume_layer)
        self.viewer.layers.remove(self.bounding_box_layer)

    def create_volume_layer(self):
        volume_layer = self.viewer.add_image(
            data=np.zeros((32, 32, 32)),
            name='map',
            visible=False,
            colormap='gray',
            rendering='mip',
        )
        return volume_layer

    def create_plane_layer(self):
        plane_parameters = {
            'enabled': True,
            'position': (0, 0, 0),
            'normal': (1, 0, 0),
            'thickness': 5,
        }
        plane_layer = self.viewer.add_image(
            data=np.zeros((32, 32, 32)),
            name='plane',
            visible=False,
            colormap='magenta',
            gamma=2.0,
            rendering='mip',
            blending='additive',
            experimental_slicing_plane=plane_parameters
        )
        return plane_layer

    def create_subparticles_layer(self):
        subparticles_layer = self.viewer.add_points(
            name='subparticles',
            data=[0, 0, 0],  # adding point to initialise properties correctly
            properties={'id': [0]},
            ndim=3,
            face_color='magenta',
            n_dimensional=True
        )
        # remove fake point, properties are preserved
        subparticles_layer.selected_data = [0]
        subparticles_layer.remove_selected()

        return subparticles_layer

    def create_current_subparticle_z_layer(self):
        current_subparticle_z_layer = self.viewer.add_points(
            name='current subparticle z',
            ndim=3,
            face_color='green',
            n_dimensional=True
        )
        return current_subparticle_z_layer

    def create_bounding_box_layer(self):
        bounding_box_layer = self.viewer.add_points(
            name='bounding box',
            ndim=3,
            blending='opaque',
            face_color='cornflowerblue',
            edge_color='black',
            edge_width=2,
            size=10,
        )
        return bounding_box_layer

    def update_bounding_box(self):
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
        self.bounding_box_layer.data = bounding_box_points

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

    def if_rotate_in_plane_mode_enabled(self, func):
        def inner(*args, **kwargs):
            if self.mode == SubboxerMode.ROTATE_IN_PLANE:
                return func(*args, **kwargs)

        return inner

    def _on_add_subparticle_center(self):
        # update id to be assigned to next particle
        self.subparticles_layer.current_properties[
            'id'] = self._next_subparticle_id

        # create subparticle and add to dict of subparticles
        z, y, x = self._active_subparticle_center
        subparticle = SubParticlePose(x=x, y=y, z=z)
        self.subparticles[self.active_subparticle_id] = subparticle
        self.active_subparticle_changed.emit(self.active_subparticle_id)
        self.populate_subparticle_vectors_layers()

    def _on_add_subparticle_z(self):
        start = np.asarray(self._active_subparticle_center)
        end = np.asarray(self._active_subparticle_z_point)
        z_vector = end - start
        self.subparticles[self.active_subparticle_id].z_vector = z_vector[::-1]
        self.current_subparticle_z_layer.visible = True
        self.populate_subparticle_vectors_layers()

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
            append=True,
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
            append=False,
            callback=self._on_add_subparticle_z
        )
        self.viewer.mouse_drag_callbacks.append(
            self._define_z_axis_callback
        )

        # left right to navigate subparticles
        self.viewer.bind_key('Left', self.previous_subparticle)
        self.viewer.bind_key('Right', self.next_subparticle)

        # rotate in plane callback
        self._rotate_in_plane_callback = partial(
            self.if_rotate_in_plane_mode_enabled(update_in_plane_rotation),
            subboxer=self,
            callback=self.populate_subparticle_vectors_layers
        )

        self.viewer.mouse_drag_callbacks.append(
            self._rotate_in_plane_callback
        )

    def disconnect_callbacks(self):
        self.viewer.mouse_drag_callbacks.remove(self._shift_plane_callback)
        self.viewer.mouse_drag_callbacks.remove(
            self._add_subparticle_callback)
        for key in 'xyzo[]':
            self.viewer.keymap.pop(key.upper())

    def create_subparticle_z_vectors_layer(self):
        z_vectors_layer = self.viewer.add_vectors(
            data=np.zeros(6).reshape((1, 2, 3)),
            length=18,
            name='subparticle z vectors',
            edge_color='blue',
            edge_width=3
        )
        return z_vectors_layer

    def create_subparticle_y_vectors_layer(self):
        y_vectors_layer = self.viewer.add_vectors(
            data=np.zeros(6).reshape((1, 2, 3)),
            ndim=3,
            length=8,
            name='subparticle y vectors',
            edge_color='orange',
            edge_width=3
        )
        return y_vectors_layer

    def create_subparticle_x_vectors_layer(self):
        x_vectors_layer = self.viewer.add_vectors(
            data=np.zeros(6).reshape((1, 2, 3)),
            ndim=3,
            length=8,
            name='subparticle x vectors',
            edge_color='green',
            edge_width=3
        )
        return x_vectors_layer

    def populate_subparticle_vectors_layers(self):
        vectors_data_attributes = [f'{ax}_vector_napari' for ax in 'xyz']
        vectors_layers = (
            self.subparticle_x_vectors_layer,
            self.subparticle_y_vectors_layer,
            self.subparticle_z_vectors_layer
        )
        for attr, layer in zip(vectors_data_attributes, vectors_layers):
            vector_data = [
                getattr(subparticle, attr)
                for subparticle in self.subparticles.values()
                if getattr(subparticle, attr) is not None
            ]
            if len(vector_data) > 0:
                layer.data = np.stack(vector_data, axis=0)

    def save_subparticles(self, output_filename):
        shifts = []
        eulers = []
        for subparticle in self.subparticles.values():
            dx = subparticle.x - self._volume_center[2]
            dy = subparticle.y - self._volume_center[1]
            dz = subparticle.z - self._volume_center[0]
            subparticle_shifts = np.array([dx, dy, dz])
            shifts.append(subparticle_shifts)

            orientation = np.column_stack(
                (
                    subparticle.x_vector,
                    subparticle.y_vector,
                    subparticle.z_vector
                )
            )
            subparticle_eulers = eulerangles.matrix2euler(
                orientation.swapaxes(-1, -2),
                axes='zyz',
                intrinsic=True,
                right_handed_rotation=True
            )
            eulers.append(subparticle_eulers)

        data = {
            'subboxerShiftX': np.array([shift[0] for shift in shifts]),
            'subboxerShiftY': np.array([shift[1] for shift in shifts]),
            'subboxerShiftZ': np.array([shift[2] for shift in shifts]),
            'subboxerAngleRot': np.array(triplet[0] for triplet in eulers),
            'subboxerAngleTilt': np.array(triplet[1] for triplet in eulers),
            'subboxerAnglePsi': np.array(triplet[2] for triplet in eulers),
        }
        df = pd.DataFrame.from_dict(data)
        starfile.write(df, output_filename, force_loop=True, overwrite=True)





