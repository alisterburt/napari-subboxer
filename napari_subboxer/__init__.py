
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from ._qt.subboxing_widget import napari_experimental_provide_dock_widget

