from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_model import SubParticlePose
    from .subboxer import Subboxer
    from napari import Viewer


def in_plane_rotation(viewer: Viewer, subboxer: Subboxer):
    # disable interactivity of selected layer
    viewer.layers.selection.active.interactive = False

    pass