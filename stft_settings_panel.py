"""Панель настроек STFT."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal


class STFTSettingsPanel(QWidget):
    """Панель настроек параметров STFT."""
    
    # Сигнал для пересчета
    recalculate_requested = pyqtSignal(dict)  # словарь с параметрами
    
    # Пресеты STFT
    PRESETS = {
        'Быстрое': {'n_fft': 1024, 'hop_length': 256},
        'Стандарт': {'n_fft': 2048, 'hop_length': 512},
        'Высокое разрешение': {'n_fft': 4096, 'hop_length': 1024},
        'Максимальное': {'n_fft': 8192, 'hop_length': 2048},
    }
    
    # Типы окон
    WINDOW_TYPES = {
        'Hamming': 'hamming',
        'Hann': 'hann',
        'Blackman': 'blackman',
        'Bartlett': 'bartlett',
    }
    
    def __init__(self):
        """Инициализация панели настроек STFT."""
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Создает UI панели настроек."""
        layout = QVBoxLayout()
        
        # Группа настроек STFT
        stft_group = QGroupBox("Настройки STFT")
        stft_layout = QVBoxLayout()
        
        # Пресеты
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Пресет:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.PRESETS.keys()))
        self.preset_combo.setCurrentText('Стандарт')
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        stft_layout.addLayout(preset_layout)
        
        # n_fft
        n_fft_layout = QHBoxLayout()
        n_fft_layout.addWidget(QLabel("N_FFT:"))
        self.n_fft_slider = QSlider(Qt.Horizontal)
        self.n_fft_slider.setMinimum(512)
        self.n_fft_slider.setMaximum(8192)
        self.n_fft_slider.setValue(2048)
        self.n_fft_slider.setTickInterval(512)
        self.n_fft_slider.setTickPosition(QSlider.TicksBelow)
        self.n_fft_slider.valueChanged.connect(self.on_n_fft_changed)
        n_fft_layout.addWidget(self.n_fft_slider, 1)
        self.n_fft_label = QLabel("2048")
        self.n_fft_label.setStyleSheet("font-weight: bold; color: #008B8B;")
        n_fft_layout.addWidget(self.n_fft_label)
        stft_layout.addLayout(n_fft_layout)
        
        # Предустановки n_fft
        n_fft_presets_layout = QHBoxLayout()
        for preset_value in [512, 1024, 2048, 4096, 8192]:
            btn = QPushButton(str(preset_value))
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, v=preset_value: self.n_fft_slider.setValue(v))
            n_fft_presets_layout.addWidget(btn)
        n_fft_presets_layout.addStretch()
        stft_layout.addLayout(n_fft_presets_layout)
        
        # hop_length
        hop_layout = QHBoxLayout()
        hop_layout.addWidget(QLabel("Hop Length:"))
        self.hop_slider = QSlider(Qt.Horizontal)
        self.hop_slider.setMinimum(128)
        self.hop_slider.setMaximum(2048)
        self.hop_slider.setValue(512)
        self.hop_slider.setTickInterval(128)
        self.hop_slider.setTickPosition(QSlider.TicksBelow)
        self.hop_slider.valueChanged.connect(self.on_hop_changed)
        hop_layout.addWidget(self.hop_slider, 1)
        self.hop_label = QLabel("512")
        self.hop_label.setStyleSheet("font-weight: bold; color: #008B8B;")
        hop_layout.addWidget(self.hop_label)
        stft_layout.addLayout(hop_layout)
        
        # Тип окна
        # Окно применяется к каждому кадру перед FFT для уменьшения спектральных утечек.
        # Различия:
        # - Hann: универсальное сглаживание, хороший баланс
        # - Hamming: похож на Hann, но сохраняет чуть больше высоких частот
        # - Blackman: сильнее подавляет боковые лепестки, но хуже частотное разрешение
        # - Bartlett: треугольное окно, компромисс по шуму
        # Тип окна передается в librosa.stft() и влияет на форму спектрограммы
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Тип окна:"))
        self.window_type_combo = QComboBox()
        self.window_type_combo.addItems(list(self.WINDOW_TYPES.keys()))
        self.window_type_combo.setCurrentText('Hamming')
        window_layout.addWidget(self.window_type_combo)
        stft_layout.addLayout(window_layout)
        
        # Нормализация
        norm_layout = QHBoxLayout()
        self.norm_global_checkbox = QCheckBox("Глобальная нормализация")
        self.norm_global_checkbox.setChecked(True)
        norm_layout.addWidget(self.norm_global_checkbox)
        stft_layout.addLayout(norm_layout)
        
        # Информация о параметрах
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "font-size: 9px; color: #666; padding: 4px; "
            "background: #f0f0f0; border-radius: 2px;"
        )
        stft_layout.addWidget(self.info_label)
        
        # Кнопка применения
        self.apply_btn = QPushButton("Применить настройки")
        self.apply_btn.clicked.connect(self.on_apply_clicked)
        stft_layout.addWidget(self.apply_btn)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        stft_layout.addWidget(self.progress_bar)
        
        stft_group.setLayout(stft_layout)
        layout.addWidget(stft_group)
        
        self.setLayout(layout)
        
        # Обновляем информацию
        self.update_info()
    
    def on_preset_changed(self, preset_name):
        """Обработчик изменения пресета."""
        if preset_name in self.PRESETS:
            preset = self.PRESETS[preset_name]
            self.n_fft_slider.setValue(preset['n_fft'])
            self.hop_slider.setValue(preset['hop_length'])
            self.update_info()
    
    def on_n_fft_changed(self, value):
        """Обработчик изменения n_fft."""
        self.n_fft_label.setText(str(value))
        self.update_info()
    
    def on_hop_changed(self, value):
        """Обработчик изменения hop_length."""
        self.hop_label.setText(str(value))
        self.update_info()
    
    def update_info(self):
        """Обновляет информацию о параметрах."""
        n_fft = self.n_fft_slider.value()
        hop_length = self.hop_slider.value()
        
        # Вычисляем разрешение (примерное, нужен sample_rate)
        # sample_rate будет передан позже
        if hasattr(self, 'sample_rate') and self.sample_rate is not None:
            freq_resolution = self.sample_rate / n_fft
            time_resolution = hop_length / self.sample_rate
            info_text = (
                f"N_FFT: {n_fft}\n"
                f"Hop Length: {hop_length}\n"
                f"Frequency resolution: {freq_resolution:.2f} Hz\n"
                f"Time resolution: {time_resolution*1000:.2f} ms"
            )
        else:
            info_text = (
                f"N_FFT: {n_fft}\n"
                f"Hop Length: {hop_length}\n"
                f"Frequency resolution: N/A (load audio)\n"
                f"Time resolution: N/A (load audio)"
            )
        self.info_label.setText(info_text)
    
    def set_sample_rate(self, sample_rate):
        """Устанавливает sample_rate для расчета разрешения.
        
        Args:
            sample_rate: Частота дискретизации
        """
        self.sample_rate = sample_rate
        self.update_info()
    
    def update_info_with_sample_rate(self, sample_rate):
        """Обновляет информацию о параметрах с учетом sample_rate.
        
        Args:
            sample_rate: Частота дискретизации
        """
        n_fft = self.n_fft_slider.value()
        hop_length = self.hop_slider.value()
        
        freq_resolution = sample_rate / n_fft
        time_resolution = hop_length / sample_rate
        
        info_text = (
            f"N_FFT: {n_fft}\n"
            f"Hop Length: {hop_length}\n"
            f"Частотное разрешение: {freq_resolution:.2f} Гц\n"
            f"Временное разрешение: {time_resolution*1000:.2f} мс"
        )
        self.info_label.setText(info_text)
    
    def get_settings(self):
        """Возвращает текущие настройки STFT.
        
        Returns:
            Словарь с настройками
        """
        return {
            'n_fft': self.n_fft_slider.value(),
            'hop_length': self.hop_slider.value(),
            'window_type': self.WINDOW_TYPES[self.window_type_combo.currentText()],
            'use_global_normalization': self.norm_global_checkbox.isChecked()
        }
    
    def set_settings(self, settings):
        """Устанавливает настройки STFT.
        
        Args:
            settings: Словарь с настройками
        """
        if 'n_fft' in settings:
            self.n_fft_slider.setValue(settings['n_fft'])
        if 'hop_length' in settings:
            self.hop_slider.setValue(settings['hop_length'])
        if 'window_type' in settings:
            # Находим ключ по значению
            for key, value in self.WINDOW_TYPES.items():
                if value == settings['window_type']:
                    self.window_type_combo.setCurrentText(key)
                    break
        if 'use_global_normalization' in settings:
            self.norm_global_checkbox.setChecked(settings['use_global_normalization'])
        self.update_info()
    
    def on_apply_clicked(self):
        """Обработчик нажатия кнопки применения."""
        settings = self.get_settings()
        self.recalculate_requested.emit(settings)
    
    def show_progress(self, show=True):
        """Показывает/скрывает прогресс-бар.
        
        Args:
            show: True для показа, False для скрытия
        """
        self.progress_bar.setVisible(show)
        if not show:
            self.progress_bar.setValue(0)
    
    def set_progress(self, value):
        """Устанавливает значение прогресс-бара.
        
        Args:
            value: Значение от 0 до 100
        """
        self.progress_bar.setValue(value)

