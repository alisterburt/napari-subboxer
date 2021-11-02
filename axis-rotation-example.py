import numpy as np
from vispy import app, scene, io
from vispy.visuals.transforms import STTransform


# Prepare canvas
canvas_size = (800, 600)
canvas = scene.SceneCanvas(keys='interactive', size=canvas_size, show=True)
canvas.measure_fps()

vol1 = np.load(io.load_data_file('volume/stent.npz'))['arr_0']

# Set up a viewbox to display the image with interactive pan/zoom
view = canvas.central_widget.add_view()

volume1 = scene.visuals.Volume(vol1, parent=view.scene, threshold=0.225)
volume1.transform = scene.STTransform(translate=(64, 64, 64))

# Create three cameras (Fly, Turntable and Arcball)
fov = 60.
view.camera = scene.cameras.TurntableCamera(parent=view.scene, fov=fov,
                                     name='Turntable')

# Create an XYZAxis visual
axis = scene.visuals.XYZAxis(parent=view)
s = STTransform(translate=np.array(canvas_size) / 2, scale=(50, 50, 50, 1))
affine = s.as_matrix()
axis.transform = affine



# Implement axis connection with cam2
@canvas.events.mouse_move.connect
def on_mouse_move(event):
    if event.button == 1 and event.is_dragging:
        axis.transform.reset()

        # axis.transform.rotate(view.camera.roll, (0, 0, 1))
        # axis.transform.rotate(view.camera.elevation, (1, 0, 0))
        # axis.transform.rotate(view.camera.azimuth, (0, 1, 0))

        axis.transform.scale((50, 50, 0.001))
        axis.transform.translate(np.array(canvas_size) / 2)
        axis.update()


if __name__ == '__main__':
    print(__doc__)
    app.run()