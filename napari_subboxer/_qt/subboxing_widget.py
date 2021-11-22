from functools import partial

import napari.viewer
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QPushButton


from .open_close_buttons import OpenCloseButtonsWidget
from .named_labeled_slider import NamedLabeledSlider
from .label_between_arrows import LabelBetweenArrows
from .selectable_button_list import LabeledSelectableButtonList
from .utils import enable_with_opacity, disable_with_opacity

from napari_subboxer.subboxer import Subboxer, SubboxerMode


class SubboxingWidget(QWidget):
    def __init__(self, viewer: napari.viewer.Viewer):
        super().__init__()
        self.viewer = viewer
        self.subboxer = Subboxer(viewer)

        self.open_close_buttons = OpenCloseButtonsWidget(
            open_button=('open map', self._on_tomogram_open),
            close_button=('close map', self._on_tomogram_close)
        )
        self.active_transformation_controls = LabelBetweenArrows(
            label_func=self.generate_label,
            decrease_callback=self.subboxer.previous_subparticle,
            increase_callback=self.subboxer.next_subparticle,
        )
        self.mode_controls = LabeledSelectableButtonList(
            label='mode:',
            button_data=[
                ('add point', self.subboxer.activate_add_mode),
                ('set z axis', self.subboxer.activate_define_z_mode),
                ('in plane', self.subboxer.activate_rotate_in_plane_mode)
            ]
        )
        self.save_transformations_button = QPushButton('save transformations')

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.open_close_buttons)
        self.layout().addWidget(self.mode_controls)
        self.layout().addWidget(self.active_transformation_controls)
        self.layout().addWidget(self.save_transformations_button)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(8, 2, 2, 2)
        self.layout().addStretch(1)

        self.mode_controls.setStyleSheet(
            "QPushButton{font-size: 10px;}"
        )

        self.subboxer.active_subparticle_changed.connect(
            self._on_active_subparticle_changed
        )
        self.save_transformations_button.clicked.connect(
            self._on_save_subparticles
        )

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
        self.subboxer.open_map(filename)

    def _on_tomogram_close(self):
        self.subboxer.close_map()
        disable_with_opacity(self.plane_thickness_controls)
        disable_with_opacity(self.plane_volume_toggle)

    def _on_save_subparticles(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save file...",
            f"subparticle_transformations.star",
            "subboxer transformations (*.star)",
            options=options
        )
        if filename == '':  # no file selected, early exit
            return
        self.subboxer.save_subparticles(output_filename=filename)

    def generate_label(self):
        return f'{self.subboxer.active_subparticle_id:03d}'

    def _on_active_subparticle_changed(self, id: int = None):
        self.active_transformation_controls.update_label()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    widget_options = {
        "name": "subboxer",
        "add_vertical_stretch": False,
        "area": 'left',
    }
    return SubboxingWidget, widget_options
