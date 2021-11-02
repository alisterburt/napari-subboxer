from qtpy.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont


from typing import Callable


class LabelBetweenArrows(QWidget):
    def __init__(self, label_func: Callable, decrease_callback: Callable,
                 increase_callback: Callable, *args,
    **kwargs):
        super().__init__(*args, **kwargs)
        self.label_func = label_func

        self.label = QLabel(label_func(), parent=self)
        self.decrease_button = QToolButton(parent=self)
        self.increase_button = QToolButton(parent=self)

        self.decrease_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.increase_button.setArrowType(Qt.ArrowType.RightArrow)

        self.setLayout(QHBoxLayout())
        self.layout().addStretch(1)
        self.layout().addWidget(self.decrease_button)
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.increase_button)
        self.layout().addStretch(1)

        self.decrease_button.clicked.connect(
            decrease_callback
        )
        self.increase_button.clicked.connect(
            increase_callback
        )
        for button in (self.increase_button, self.decrease_button):
            button.clicked.connect(self.update_label)

    def update_label(self):
        self.label.setText(f'<pre>{self.label_func()}</pre>')