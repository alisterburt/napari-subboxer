from napari.layers.base import Layer


def reset_contrast_limits(*layers: Layer):
    for layer in layers:
        layer.reset_contrast_limits_range()
        layer.reset_contrast_limits()
