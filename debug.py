import napari
import numpy as np

viewer = napari.Viewer(ndisplay=3)
# viewer.add_image(np.random.random(size=(28, 28, 28)))
# tsw = viewer.window.add_plugin_dock_widget(plugin_name='napari-subboxer')
napari.run()
