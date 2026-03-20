"""UI компоненты для AudioMeshVisualizer."""

from PyQt5.QtWidgets import (
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QSlider, QProgressBar, QComboBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal

# Единый цвет для всех меток
LABEL_COLOR = "font-weight: bold; color: #008B8B;"


class CollapsibleGroup(QWidget):
    """Сворачиваемая группа виджетов."""
    
    def __init__(self, title):
        """Инициализация сворачиваемой группы.
        
        Args:
            title: Заголовок группы
        """
        super().__init__()
        self.init_ui(title)
    
    def init_ui(self, title):
        """Создает UI сворачиваемой группы."""
        layout = QVBoxLayout()
        layout.setSpacing(4)
        
        # Кнопка заголовка - стандартизированный стиль
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setStyleSheet(
            "text-align: left; font-weight: bold; font-size: 11px; "
            "padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px;"
        )
        self.toggle_btn.setArrowType(Qt.DownArrow)
        self.toggle_btn.clicked.connect(self.toggle)
        
        # Контент - стандартизированные отступы
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(8, 6, 8, 6)
        self.content_layout.setSpacing(6)
        self.content_widget.setLayout(self.content_layout)
        
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        self.setLayout(layout)
    
    def toggle(self):
        """Переключает видимость содержимого."""
        checked = self.toggle_btn.isChecked()
        self.content_widget.setVisible(checked)
        self.toggle_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
    
    def addWidget(self, widget):
        """Добавляет виджет в группу."""
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout_item):
        """Добавляет layout в группу."""
        self.content_layout.addLayout(layout_item)


class ControlPanel(QWidget):
    """Панель управления с кнопками и слайдерами."""
    
    def __init__(self):
        """Инициализация панели управления."""
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Создает UI панели управления."""
        layout = QVBoxLayout()
        
        # Заголовок
        self.label = QLabel("Загрузите аудиофайл (WAV или MP3)")
        layout.addWidget(self.label)
        
        # Группа "Воспроизведение"
        playback_group = CollapsibleGroup("▶ Воспроизведение")
        
        # Кнопка загрузки
        self.button = QPushButton("📂 Загрузить аудио")
        playback_group.addWidget(self.button)
        
        # Progress bar (скрыт, так как используется timeline_widget)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1000)
        self.progress_bar.setVisible(False)  # Скрываем, так как есть timeline
        
        # Slider громкости
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Громкость:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        vol_layout.addWidget(self.volume_slider, 1)
        self.volume_label = QLabel("70%")
        self.volume_label.setStyleSheet(LABEL_COLOR)
        vol_layout.addWidget(self.volume_label)
        playback_group.addLayout(vol_layout)
        
        # Кнопки управления
        controls = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setEnabled(False)
        controls.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setEnabled(False)
        controls.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setEnabled(False)
        controls.addWidget(self.stop_btn)
        playback_group.addLayout(controls)
        
        # Кнопка полной спектрограммы
        self.full_btn = QPushButton("Полная спектрограмма")
        self.full_btn.setEnabled(False)
        playback_group.addWidget(self.full_btn)
        
        # Кнопка экспорта
        self.export_btn = QPushButton("Экспорт меша")
        self.export_btn.setEnabled(False)
        playback_group.addWidget(self.export_btn)
        
        layout.addWidget(playback_group)
        
        # Группа "Визуализация"
        viz_group = CollapsibleGroup("🎨 Визуализация")
        
        # Slider частоты
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Макс. частота:"))
        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_slider.setMinimum(2)
        self.freq_slider.setMaximum(22)
        self.freq_slider.setValue(20)
        self.freq_slider.setTickInterval(2)
        self.freq_slider.setTickPosition(QSlider.TicksBelow)
        freq_layout.addWidget(self.freq_slider, 1)
        self.freq_value_label = QLabel("20 кГц")
        self.freq_value_label.setStyleSheet(LABEL_COLOR)
        freq_layout.addWidget(self.freq_value_label)
        viz_group.addLayout(freq_layout)
        
        # Slider усиления
        amp_layout = QHBoxLayout()
        amp_layout.addWidget(QLabel("Усиление:"))
        self.amp_slider = QSlider(Qt.Horizontal)
        self.amp_slider.setMinimum(10)
        self.amp_slider.setMaximum(200)
        self.amp_slider.setValue(50)
        amp_layout.addWidget(self.amp_slider, 1)
        self.amp_label = QLabel("5.0x")
        self.amp_label.setStyleSheet(LABEL_COLOR)
        amp_layout.addWidget(self.amp_label)
        viz_group.addLayout(amp_layout)
        
        # Slider размера окна
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Размер окна:"))
        self.window_size_slider = QSlider(Qt.Horizontal)
        self.window_size_slider.setMinimum(50)
        self.window_size_slider.setMaximum(500)
        self.window_size_slider.setValue(150)
        self.window_size_slider.setTickInterval(50)
        self.window_size_slider.setTickPosition(QSlider.TicksBelow)
        window_layout.addWidget(self.window_size_slider, 1)
        self.window_size_label = QLabel("150")
        self.window_size_label.setStyleSheet(LABEL_COLOR)
        window_layout.addWidget(self.window_size_label)
        viz_group.addLayout(window_layout)
        
        # Выбор цветовой карты
        colormap_layout = QHBoxLayout()
        colormap_layout.addWidget(QLabel("Цветовая карта:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            'viridis', 'plasma', 'inferno', 'magma', 'turbo', 'spectral',
            'coolwarm', 'rainbow', 'jet', 'hot', 'cool', 'spring', 'summer',
            'autumn', 'winter', 'gray', 'bone', 'copper', 'pink'
        ])
        self.colormap_combo.setCurrentText('viridis')
        colormap_layout.addWidget(self.colormap_combo)
        viz_group.addLayout(colormap_layout)
        
        # Настройка диапазона амплитуд
        self.range_checkbox = QCheckBox("Использовать пользовательский диапазон")
        viz_group.addWidget(self.range_checkbox)
        
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Min dB:"))
        self.min_db_spinbox = QDoubleSpinBox()
        self.min_db_spinbox.setRange(-200.0, 0.0)
        self.min_db_spinbox.setValue(-80.0)
        self.min_db_spinbox.setDecimals(1)
        self.min_db_spinbox.setEnabled(False)
        range_layout.addWidget(self.min_db_spinbox)
        
        range_layout.addWidget(QLabel("Max dB:"))
        self.max_db_spinbox = QDoubleSpinBox()
        self.max_db_spinbox.setRange(-200.0, 0.0)
        self.max_db_spinbox.setValue(0.0)
        self.max_db_spinbox.setDecimals(1)
        self.max_db_spinbox.setEnabled(False)
        range_layout.addWidget(self.max_db_spinbox)
        viz_group.addLayout(range_layout)
        
        # Подключаем сигналы
        self.range_checkbox.toggled.connect(
            lambda checked: self.min_db_spinbox.setEnabled(checked)
        )
        self.range_checkbox.toggled.connect(
            lambda checked: self.max_db_spinbox.setEnabled(checked)
        )
        
        layout.addWidget(viz_group)
        
        # Группа "ИИ"
        ai_group = CollapsibleGroup("🤖 ИИ")
        ai_layout = QVBoxLayout()

        episodes_layout = QHBoxLayout()
        episodes_layout.addWidget(QLabel("Эпизоды:"))
        self.ai_episodes_spin = QSpinBox()
        self.ai_episodes_spin.setRange(20, 1000)
        self.ai_episodes_spin.setValue(150)
        episodes_layout.addWidget(self.ai_episodes_spin)
        ai_layout.addLayout(episodes_layout)

        self.ai_progress_checkbox = QCheckBox("Показывать прогресс обучения")
        self.ai_progress_checkbox.setChecked(True)
        ai_layout.addWidget(self.ai_progress_checkbox)

        self.ai_save_checkbox = QCheckBox("Сохранять лог и путь после обучения")
        self.ai_save_checkbox.setChecked(True)
        ai_layout.addWidget(self.ai_save_checkbox)

        amp_penalty_layout = QHBoxLayout()
        amp_penalty_layout.addWidget(QLabel("Штраф за амплитуду:"))
        self.ai_amp_penalty = QDoubleSpinBox()
        self.ai_amp_penalty.setRange(0.0, 2.0)
        self.ai_amp_penalty.setSingleStep(0.05)
        self.ai_amp_penalty.setValue(0.30)
        self.ai_amp_penalty.setToolTip("0 = игнорировать высоту/амплитуду; больше — обходить высокие/громкие места.")
        amp_penalty_layout.addWidget(self.ai_amp_penalty)
        ai_layout.addLayout(amp_penalty_layout)

        slope_layout = QHBoxLayout()
        self.ai_slope_block_checkbox = QCheckBox("Крутой уклон = стена")
        self.ai_slope_block_checkbox.setChecked(True)
        slope_layout.addWidget(self.ai_slope_block_checkbox)
        self.ai_slope_limit = QDoubleSpinBox()
        self.ai_slope_limit.setRange(0.01, 1.0)
        self.ai_slope_limit.setSingleStep(0.01)
        self.ai_slope_limit.setValue(0.12)
        self.ai_slope_limit.setToolTip("Макс. разница высот между соседями.\nМеньше порог — больше стен.")
        slope_layout.addWidget(QLabel("Порог уклона:"))
        slope_layout.addWidget(self.ai_slope_limit)
        ai_layout.addLayout(slope_layout)

        self.ai_hint_label = QLabel(
            "Пояснения:\n"
            "• Эпизоды — сколько раз агент учится.\n"
            "• Штраф за амплитуду — избегать высоких/громких зон (0 = игнорировать).\n"
            "• Крутой уклон = стена — блокировать резкие перепады (порог ниже → больше стен).\n"
            "• X/Y — индекс частоты/времени; Z берётся с поверхности автоматически, чтобы точки были на меше."
        )
        self.ai_hint_label.setWordWrap(True)
        self.ai_hint_label.setStyleSheet("font-size: 10px; color: #555;")
        ai_layout.addWidget(self.ai_hint_label)

        save_paths_layout = QHBoxLayout()
        self.ai_log_paths_checkbox = QCheckBox("Сохранять пути по эпизодам")
        save_paths_layout.addWidget(self.ai_log_paths_checkbox, 1)
        self.ai_log_every_spin = QSpinBox()
        self.ai_log_every_spin.setRange(1, 50)
        self.ai_log_every_spin.setValue(5)
        save_paths_layout.addWidget(QLabel("Каждый N эпизодов:"))
        save_paths_layout.addWidget(self.ai_log_every_spin)
        ai_layout.addLayout(save_paths_layout)

        self.ai_train_btn = QPushButton("ИИ: обучение на меше")
        self.ai_train_btn.setEnabled(False)
        ai_layout.addWidget(self.ai_train_btn)

        self.ai_load_btn = QPushButton("Загрузить путь/лог ИИ")
        self.ai_load_btn.setEnabled(False)
        ai_layout.addWidget(self.ai_load_btn)

        ai_group.addLayout(ai_layout)
        layout.addWidget(ai_group)

        # Секция для STFT настроек (будет добавлена позже)
        self.stft_group = CollapsibleGroup("⚙ STFT")
        self.stft_settings_placeholder = QLabel("Настройки STFT появятся после инициализации.")
        self.stft_settings_placeholder.setWordWrap(True)
        self.stft_settings_placeholder.setStyleSheet(
            "font-size: 9px; color: #666; padding: 6px;"
        )
        self.stft_group.addWidget(self.stft_settings_placeholder)
        layout.addWidget(self.stft_group)
        
        # Кнопка помощи - вне сворачиваемой группы
        self.help_btn = QPushButton("Помощь")
        self.help_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        layout.addWidget(self.help_btn)
        
        # Скрытый info_label для использования в других местах кода
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "font-size: 9px; color: #666; padding: 8px; "
            "background: #f9f9f9; border-radius: 4px;"
        )
        self.info_label.setVisible(False)  # Скрываем, так как информация дублируется
        layout.addStretch()
        
        self.setLayout(layout)
        # Стандартизированная ширина для всех панелей
        self.setMaximumWidth(320)
        self.setMinimumWidth(320)


class TimelineWidget(QWidget):
    """Виджет timeline с возможностью перетаскивания для перемотки."""
    
    # Сигнал для перемотки
    seek_requested = pyqtSignal(int)  # позиция в миллисекундах
    
    def __init__(self):
        """Инициализация timeline виджета."""
        super().__init__()
        self._is_dragging = False
        self.init_ui()
    
    def init_ui(self):
        """Создает UI timeline."""
        layout = QVBoxLayout()
        
        # Progress bar как timeline
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 1000)
        self.timeline_slider.setValue(0)
        
        # Подключаем сигналы для перетаскивания
        self.timeline_slider.sliderPressed.connect(self._on_slider_pressed)
        self.timeline_slider.sliderReleased.connect(self._on_slider_released)
        self.timeline_slider.valueChanged.connect(self._on_slider_value_changed)
        
        layout.addWidget(self.timeline_slider)
        
        # Метка времени
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self.time_label)
        
        self.setLayout(layout)
    
    def _on_slider_pressed(self):
        """Обработчик нажатия на слайдер."""
        self._is_dragging = True
    
    def _on_slider_released(self):
        """Обработчик отпускания слайдера."""
        if self._is_dragging:
            self._is_dragging = False
            # Вычисляем позицию в миллисекундах
            duration = getattr(self, '_duration', 0)
            if duration > 0:
                position_ms = int((self.timeline_slider.value() / 1000.0) * duration)
                self.seek_requested.emit(position_ms)
    
    def _on_slider_value_changed(self, value):
        """Обработчик изменения значения слайдера."""
        if self._is_dragging:
            # Обновляем метку времени во время перетаскивания
            duration = getattr(self, '_duration', 0)
            if duration > 0:
                from utils import format_time
                position_ms = int((value / 1000.0) * duration)
                current_time = format_time(position_ms)
                total_time = format_time(duration)
                self.time_label.setText(f"{current_time} / {total_time}")
    
    def set_duration(self, duration_ms):
        """Устанавливает длительность аудио.
        
        Args:
            duration_ms: Длительность в миллисекундах
        """
        self._duration = duration_ms
    
    def set_position(self, position_ms, is_user_action=False):
        """Устанавливает позицию на timeline.
        
        Args:
            position_ms: Позиция в миллисекундах
            is_user_action: True если это действие пользователя (не обновлять)
        """
        if not self._is_dragging or not is_user_action:
            duration = getattr(self, '_duration', 0)
            if duration > 0:
                progress = min(int((position_ms / duration) * 1000), 1000)
                self.timeline_slider.setValue(progress)
    
    def update_time_label(self, current_ms, total_ms):
        """Обновляет метку времени.
        
        Args:
            current_ms: Текущее время в миллисекундах
            total_ms: Общее время в миллисекундах
        """
        from utils import format_time
        current_time = format_time(current_ms)
        total_time = format_time(total_ms)
        self.time_label.setText(f"{current_time} / {total_time}")


class InfoPanel(QWidget):
    """Панель с информацией о загруженном аудио."""
    
    def __init__(self):
        """Инициализация информационной панели."""
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Создает UI информационной панели."""
        layout = QVBoxLayout()
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "font-size: 9px; color: #666; padding: 8px; "
            "background: #f9f9f9; border-radius: 4px;"
        )
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
    
    def set_info(self, info_dict):
        """Устанавливает информацию о аудио.
        
        Args:
            info_dict: Словарь с информацией
        """
        if info_dict is None:
            self.info_label.setText("")
            return
        
        text = (
            f"✓ {info_dict.get('filename', 'Unknown')}\n"
            f"Длительность: {info_dict.get('duration', 0):.1f} сек\n"
            f"Sample rate: {info_dict.get('sample_rate', 0)} Гц\n"
            f"N_fft: {info_dict.get('n_fft', 0)}\n"
            f"Кадров: {info_dict.get('frames', 0)}\n"
            f"Частот: {info_dict.get('frequencies', 0)}\n\n"
            f"Диапазон амплитуды: {info_dict.get('db_min', 0):.1f} - "
            f"{info_dict.get('db_max', 0):.1f} дБ"
        )
        self.info_label.setText(text)

