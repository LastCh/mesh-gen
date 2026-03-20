"""Стили для UI приложения."""

# Светлая тема (по умолчанию)
LIGHT_THEME = """
QWidget {
    background-color: #ffffff;
    color: #000000;
}

QPushButton {
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #e0e0e0;
}

QPushButton:pressed {
    background-color: #d0d0d0;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    color: #999999;
}

QSlider::groove:horizontal {
    border: 1px solid #cccccc;
    height: 8px;
    background: #f0f0f0;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #008B8B;
    border: 1px solid #006666;
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #00AAAA;
}

QSlider::handle:horizontal:pressed {
    background: #006666;
}

QComboBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 3px 5px;
    background-color: #ffffff;
}

QComboBox:hover {
    border-color: #008B8B;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    border: 1px solid #cccccc;
    selection-background-color: #008B8B;
    selection-color: #ffffff;
}

QDoubleSpinBox, QSpinBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 3px;
    background-color: #ffffff;
}

QDoubleSpinBox:hover, QSpinBox:hover {
    border-color: #008B8B;
}

QCheckBox {
    spacing: 5px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #008B8B;
    border-color: #006666;
}

QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    background-color: #f0f0f0;
}

QProgressBar::chunk {
    background-color: #008B8B;
    border-radius: 3px;
}
"""

# Темная тема
DARK_THEME = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}

QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 20px;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #4c4c4c;
}

QPushButton:pressed {
    background-color: #2c2c2c;
}

QPushButton:disabled {
    background-color: #252525;
    color: #666666;
}

QSlider::groove:horizontal {
    border: 1px solid #555555;
    height: 8px;
    background: #3c3c3c;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #008B8B;
    border: 1px solid #006666;
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #00AAAA;
}

QComboBox {
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px 5px;
    background-color: #3c3c3c;
    color: #ffffff;
}

QComboBox:hover {
    border-color: #008B8B;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    border: 1px solid #555555;
    background-color: #3c3c3c;
    selection-background-color: #008B8B;
    selection-color: #ffffff;
}

QDoubleSpinBox, QSpinBox {
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px;
    background-color: #3c3c3c;
    color: #ffffff;
}

QDoubleSpinBox:hover, QSpinBox:hover {
    border-color: #008B8B;
}

QCheckBox {
    spacing: 5px;
    color: #ffffff;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #3c3c3c;
}

QCheckBox::indicator:checked {
    background-color: #008B8B;
    border-color: #006666;
}

QGroupBox {
    border: 1px solid #555555;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QProgressBar {
    border: 1px solid #555555;
    border-radius: 4px;
    text-align: center;
    background-color: #3c3c3c;
    color: #ffffff;
}

QProgressBar::chunk {
    background-color: #008B8B;
    border-radius: 3px;
}

QLabel {
    color: #ffffff;
}
"""

