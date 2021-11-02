from ..label_between_arrows import LabelBetweenArrows
from unittest.mock import MagicMock
from qtpy.QtCore import Qt

import numpy as np


def test_label_between_arrows_behaviour(qtbot):
    decrease_button_callback = MagicMock()
    increase_button_callback = MagicMock()
    label_func = lambda: f'{np.random.randint(low=0, high=1000):04d}'

    widget = LabelBetweenArrows(
        label_func=label_func,
        decrease_callback=decrease_button_callback,
        increase_callback=increase_button_callback,
    )
    widget.show()
    qtbot.addWidget(widget)



