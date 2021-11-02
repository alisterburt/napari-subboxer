import napari
import numpy as np

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
    ], edge_width=0.1, face_color='blue', size=0.4)

transformations = viewer.add_points(
    [0.5, 0.5, 0.5],
    face_color='magenta',
    edge_width=0.1,
    size=1,
    n_dimensional=True,
    blending='translucent_no_depth',
)

orientations = viewer.add_points(
    ndim=3,
    size=0.4,
    face_color='green',
    edge_width=0.1,
)

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
        yield
    viewer.camera.center = original_camera_position

napari.run()