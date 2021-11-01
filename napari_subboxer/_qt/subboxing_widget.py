import napari.viewer
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QVBoxLayout, QFileDialog


from .open_close_buttons import OpenCloseButtonsWidget
from .named_labeled_slider import NamedLabeledSlider
from .selectable_button_list import LabeledSelectableButtonList
from .utils import enable_with_opacity, disable_with_opacity

from napari_subboxer.subboxer import Subboxer, RenderingMode


class SubboxingWidget(QWidget):
    def __init__(self, viewer: napari.viewer.Viewer):
        super().__init__()
        self.viewer = viewer
        self.subboxer = Subboxer(viewer)
        self.subboxer.plane_thickness_changed.connect(
            self._on_plane_thickness_changed
        )

        self.open_close_buttons = OpenCloseButtonsWidget(
            open_button=('open map', self._on_tomogram_open),
            close_button=('close map', self._on_tomogram_close)
        )

        self.plane_thickness_controls = NamedLabeledSlider(
            label='thickness:',
            minimum_value=1,
            maximum_value=50,
            default_value=5
        )
        self.plane_thickness_controls.slider.valueChanged.connect(
            self._on_thickness_slider_changed
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.open_close_buttons)
        self.layout().addWidget(self.plane_thickness_controls)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(8, 2, 2, 2)
        self.layout().addStretch(1)

        self.setFixedHeight(90)

    def _on_tomogram_open(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select a map file...",
            "",
            "Cryo-EM maps (*.mrc)",
            options=options
        )
        if filename == '':  # no file selected, early exit
            return
        self.subboxer.open_reconstruction(filename)


    def _on_tomogram_close(self):
        self.subboxer.close_reconstruction()
        disable_with_opacity(self.plane_thickness_controls)
        disable_with_opacity(self.plane_volume_toggle)

    def _on_render_as_volume(self):
        self.subboxer.rendering_mode = RenderingMode.VOLUME
        disable_with_opacity(self.plane_thickness_controls)

    def _on_render_as_plane(self):
        self.subboxer.rendering_mode = RenderingMode.PLANE
        enable_with_opacity(self.plane_thickness_controls)

    def _on_thickness_slider_changed(self):
        self.subboxer.plane_thickness = self.plane_thickness_controls.slider.value()

    def _on_plane_thickness_changed(self):
        self.plane_thickness_controls.slider.setValue(
            self.subboxer.plane_thickness
        )


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    widget_options = {
        "name": "subboxing widget",
        "add_vertical_stretch": False,
        "area": 'left',
    }
    return SubboxingWidget, widget_options
