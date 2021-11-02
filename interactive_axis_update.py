import napari
import numpy as np
from vispy import scene
from vispy.visuals.transforms import STTransform

viewer = napari.Viewer(ndisplay=3)
viewer.add_points([
    [0, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
    [1, 0, 0],
    [0, 1, 1],
    [1, 1, 0],
    [1, 0, 1],
    [1, 1, 1],
    ], edge_width=0.05, face_color='blue', size=0.1)

transformations = viewer.add_points(
    [0.5, 0.5, 0.5],
    face_color='magenta',
    edge_width=0.05,
    size=0.1,
    n_dimensional=True,
    blending='translucent_no_depth',
)

orientations = viewer.add_points(
    data=[],
    ndim=3,
    size=0.1,
    face_color='green',
    edge_width=0.05,
)

qt_viewer = viewer.window.qt_viewer
canvas = qt_viewer.canvas
vispy_scene = viewer.view.scene
axis = scene.visuals.XYZAxis(parent=vispy_scene, order=1e6)
s = STTransform(translate=np.array(canvas.size) / 2, scale=(50, 50, 50,
                                                                 1))


@viewer.mouse_drag_callbacks.append
def update_axis(viewer, event):
    original_camera_position = np.copy(viewer.camera.center)
    yield

    while event.type == 'mouse_move':
        selected_point = transformations.data[0]  # placeholder for selected point
        viewer.camera.center = selected_point
        z_point = selected_point + viewer.camera.view_direction

        print(z_point)
        orientations.data = z_point
        orientations.size = 0.01
        yield
    viewer.camera.center = original_camera_position

napari.run()