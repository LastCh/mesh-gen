"""Улучшенное окно полной спектрограммы с инструментами навигации."""

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QDoubleSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import os


class FullSpectrogramWindow(QWidget):
    """Окно для просмотра полной спектрограммы с инструментами навигации."""
    
    # Сигнал для выбора сегмента
    segment_selected = pyqtSignal(int, int)  # t0, t1
    
    def __init__(self, spectrogram_data, freqs, times, audio_processor, mesh_generator, 
                 visualization_settings, freq_max=20000, control_panel=None, main_window=None):
        """Инициализация окна полной спектрограммы.
        
        Args:
            spectrogram_data: Полная спектрограмма
            freqs: Массив частот
            times: Массив времен
            audio_processor: AudioProcessor для получения данных
            mesh_generator: MeshGenerator для создания меша
            visualization_settings: VisualizationSettings для настроек
            freq_max: Максимальная частота
            control_panel: ControlPanel для получения текущих настроек
            main_window: Главное окно для получения настроек и подписки на изменения
        """
        super().__init__()
        self.spectrogram_data = spectrogram_data
        self.freqs = freqs
        self.times = times
        self.audio_processor = audio_processor
        self.mesh_generator = mesh_generator
        self.visualization_settings = visualization_settings
        self.freq_max = freq_max
        self.control_panel = control_panel
        self.main_window = main_window
        
        self.mesh = None
        self.mesh_actor = None
        self.plotter = None
        # Инициализируем как полную спектрограмму (весь диапазон)
        self.selected_t0 = 0
        self.selected_t1 = self.spectrogram_data.shape[0] if self.spectrogram_data is not None else 0
        
        self.setWindowTitle("Полная спектрограмма")
        self.resize(1200, 800)
        
        # Устанавливаем иконку окна
        icon_path = os.path.join(os.path.dirname(__file__), 'photo_2025-03-04_00-35-20.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация UI."""
        layout = QVBoxLayout()
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        # Кнопки управления
        self.reset_view_btn = QPushButton("Сброс вида")
        self.reset_view_btn.clicked.connect(self.reset_view)
        toolbar.addWidget(self.reset_view_btn)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(self.zoom_out_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Панель выбора сегмента будет добавлена ниже, рядом с полями времени
        
        # Создаем plotter widget
        self.plotter = QtInteractor(self)
        self.plotter.set_background("white")
        
        # Создаем меш полной спектрограммы
        self.create_full_mesh()
        
        # Добавляем plotter в layout
        layout.addWidget(self.plotter)
        
        # Timeline для выбора временного диапазона - более заметный
        timeline_group = QHBoxLayout()
        timeline_group.setContentsMargins(8, 8, 8, 8)
        timeline_group.addWidget(QLabel("От:"))
        
        self.start_time_spinbox = QDoubleSpinBox()
        self.start_time_spinbox.setRange(0.0, self.times[-1] if len(self.times) > 0 else 0.0)
        self.start_time_spinbox.setDecimals(2)
        self.start_time_spinbox.setSuffix(" сек")
        self.start_time_spinbox.setMinimumWidth(100)
        timeline_group.addWidget(self.start_time_spinbox)
        
        timeline_group.addWidget(QLabel("До:"))
        
        self.end_time_spinbox = QDoubleSpinBox()
        self.end_time_spinbox.setRange(0.0, self.times[-1] if len(self.times) > 0 else 0.0)
        self.end_time_spinbox.setDecimals(2)
        self.end_time_spinbox.setSuffix(" сек")
        self.end_time_spinbox.setMinimumWidth(100)
        if len(self.times) > 0:
            self.end_time_spinbox.setValue(self.times[-1])
        timeline_group.addWidget(self.end_time_spinbox)
        
        # Кнопка выбора сегмента - рядом с полями
        self.select_segment_btn = QPushButton("✓ Применить сегмент")
        self.select_segment_btn.setStyleSheet(
            "font-weight: bold; font-size: 12px; padding: 8px 16px; "
            "background-color: #4CAF50; color: white; border-radius: 4px;"
        )
        self.select_segment_btn.clicked.connect(self.select_segment)
        timeline_group.addWidget(self.select_segment_btn)
        
        timeline_group.addStretch()
        
        # Показываем длительность выбранного сегмента
        self.segment_duration_label = QLabel("")
        self.segment_duration_label.setStyleSheet("font-weight: bold; color: #008B8B;")
        timeline_group.addWidget(self.segment_duration_label)
        
        # Обновляем длительность при изменении
        self.start_time_spinbox.valueChanged.connect(self._update_segment_duration)
        self.end_time_spinbox.valueChanged.connect(self._update_segment_duration)
        self._update_segment_duration()
        
        layout.addLayout(timeline_group)
        
        self.setLayout(layout)
    
    def create_full_mesh(self):
        """Создает меш полной спектрограммы с полной точностью."""
        try:
            # Используем текущие настройки из control_panel, если доступны
            if self.control_panel is not None:
                amp = self.control_panel.amp_slider.value() / 10.0
                self.freq_max = self.main_window.freq_max if self.main_window else self.freq_max
            else:
                amp = 5.0  # Значение по умолчанию
            
            t0 = 0
            t1 = self.spectrogram_data.shape[0]
            
            # Используем полные данные без downsampling
            data_to_use = self.spectrogram_data
            times_to_use = self.times
            freqs_to_use = self.freqs
            
            # Ограничиваем только по максимальной частоте (если задана)
            idx_freq = np.searchsorted(self.freqs, self.freq_max)
            if idx_freq < len(self.freqs):
                data_to_use = data_to_use[:, :idx_freq]
                freqs_to_use = self.freqs[:idx_freq]
            
            mesh, actual_freq_khz = self.mesh_generator.create_mesh(
                data_to_use,
                0, t1,
                self.freq_max,
                amp,
                freqs_to_use,
                z_min=self.audio_processor.db_min,
                z_max=self.audio_processor.db_max,
                use_global_normalization=True
            )
            
            self.mesh = mesh
            
            total_time = len(self.audio_processor.audio_data) / self.audio_processor.sample_rate
            
            # Получаем активный диапазон для цветов
            min_db, max_db = self.visualization_settings.get_active_range()
            
            # Используем данные из mesh для scalars
            scalars_data = data_to_use.ravel()
            
            self.mesh_actor = self.plotter.add_mesh(
                mesh,
                scalars=scalars_data,
                cmap=self.visualization_settings.colormap,
                clim=[min_db, max_db] if min_db is not None and max_db is not None else None,
                show_edges=False,
                lighting=True,
                ambient=0.3,
                specular=0.5,
                smooth_shading=True,
                scalar_bar_args={'title': 'Amplitude, dB', 'n_labels': 5, 'fmt': '%.1f', 'vertical': True}
            )
            
            # Добавляем метки частот
            freq_ticks = np.linspace(0, self.freq_max, 6)
            for f in freq_ticks:
                y_pos = (f / self.freq_max) * mesh.bounds[3]
                self.plotter.add_point_labels(
                    [[mesh.bounds[0], y_pos, mesh.bounds[5]]],
                    [f"{int(f)} Гц"],
                    font_size=10, text_color="#008B8B", shape=None, show_points=False,
                )
            
            self.plotter.camera_position = 'iso'
            self.plotter.title = f"Полная спектрограмма | Время: 0-{total_time:.1f} сек | Частота: 0-{actual_freq_khz:.1f} кГц"
            
        except Exception as e:
            print(f"Ошибка создания полной спектрограммы: {e}")
    
    def reset_view(self):
        """Сбрасывает вид камеры."""
        self.plotter.camera_position = 'iso'
        self.plotter.render()
    
    def zoom_in(self):
        """Увеличивает масштаб."""
        try:
            self.plotter.camera.zoom(1.2)
            self.plotter.render()
        except Exception:
            pass
    
    def zoom_out(self):
        """Уменьшает масштаб."""
        try:
            self.plotter.camera.zoom(0.8)
            self.plotter.render()
        except Exception:
            pass
    
    def _update_segment_duration(self):
        """Обновляет отображение длительности выбранного сегмента."""
        start_time = self.start_time_spinbox.value()
        end_time = self.end_time_spinbox.value()
        
        if end_time > start_time:
            duration = end_time - start_time
            self.segment_duration_label.setText(f"Длительность: {duration:.2f} сек")
            self.select_segment_btn.setEnabled(True)
            self.select_segment_btn.setStyleSheet(
                "font-weight: bold; font-size: 12px; padding: 8px 16px; "
                "background-color: #4CAF50; color: white; border-radius: 4px;"
            )
        else:
            self.segment_duration_label.setText("Некорректный диапазон")
            self.select_segment_btn.setEnabled(False)
            self.select_segment_btn.setStyleSheet(
                "font-weight: bold; font-size: 12px; padding: 8px 16px; "
                "background-color: #cccccc; color: #666666; border-radius: 4px;"
            )
    
    def select_segment(self):
        """Выбирает сегмент и обновляет визуализацию, показывая только выбранный диапазон."""
        start_time = self.start_time_spinbox.value()
        end_time = self.end_time_spinbox.value()
        
        if start_time >= end_time:
            return
        
        # Находим индексы кадров
        t0 = np.searchsorted(self.times, start_time)
        t1 = np.searchsorted(self.times, end_time)
        
        if t0 < t1:
            # Сохраняем выбранный диапазон
            self.selected_t0 = t0
            self.selected_t1 = t1
            
            # Обновляем визуализацию - показываем только выбранный сегмент
            self.update_mesh_for_segment(t0, t1)
            
            # Визуальная обратная связь
            self.select_segment_btn.setText("✓ Применено!")
            self.select_segment_btn.setStyleSheet(
                "font-weight: bold; font-size: 12px; padding: 8px 16px; "
                "background-color: #2196F3; color: white; border-radius: 4px;"
            )
            
            # Отправляем сигнал в главное окно (для обновления параметров)
            self.segment_selected.emit(t0, t1)
    
    def update_mesh_for_segment(self, t0, t1):
        """Обновляет меш, показывая только выбранный сегмент."""
        try:
            # Очищаем plotter для пересоздания визуализации
            # Это удалит все акторы включая меш, метки и scalar bar
            try:
                self.plotter.clear()
                # Восстанавливаем фон
                self.plotter.set_background("white")
                self.mesh_actor = None
            except Exception:
                pass
            
            # Очищаем старый меш
            if self.mesh is not None:
                try:
                    self.mesh.Clear()
                except Exception:
                    pass
            
            # Используем текущие настройки из control_panel, если доступны
            if self.control_panel is not None:
                amp = self.control_panel.amp_slider.value() / 10.0
                self.freq_max = self.main_window.freq_max if self.main_window else self.freq_max
            else:
                amp = 5.0
            
            # Берем данные только для выбранного сегмента
            segment_data = self.spectrogram_data[t0:t1, :]
            segment_times = self.times[t0:t1]
            
            # Используем полные данные без downsampling
            data_to_use = segment_data
            times_to_use = segment_times
            freqs_to_use = self.freqs
            
            # Ограничиваем только по максимальной частоте (если задана)
            idx_freq = np.searchsorted(self.freqs, self.freq_max)
            if idx_freq < len(self.freqs):
                data_to_use = data_to_use[:, :idx_freq]
                freqs_to_use = self.freqs[:idx_freq]
            
            t1_new = len(data_to_use)
            
            mesh, actual_freq_khz = self.mesh_generator.create_mesh(
                data_to_use,
                0, t1_new,
                self.freq_max,
                amp,
                freqs_to_use,
                z_min=self.audio_processor.db_min,
                z_max=self.audio_processor.db_max,
                use_global_normalization=True
            )
            
            self.mesh = mesh
            
            # Получаем активный диапазон для цветов
            min_db, max_db = self.visualization_settings.get_active_range()
            
            # Используем данные из mesh для scalars
            scalars_data = data_to_use.ravel()
            
            # Используем текущую цветовую карту из настроек
            colormap = self.visualization_settings.colormap
            
            self.mesh_actor = self.plotter.add_mesh(
                mesh,
                scalars=scalars_data,
                cmap=colormap,
                clim=[min_db, max_db] if min_db is not None and max_db is not None else None,
                show_edges=False,
                lighting=True,
                ambient=0.3,
                specular=0.5,
                smooth_shading=True,
                scalar_bar_args={'title': 'Amplitude, dB', 'n_labels': 5, 'fmt': '%.1f', 'vertical': True}
            )
            
            # Добавляем метки частот
            freq_ticks = np.linspace(0, self.freq_max, 6)
            for f in freq_ticks:
                y_pos = (f / self.freq_max) * mesh.bounds[3]
                self.plotter.add_point_labels(
                    [[mesh.bounds[0], y_pos, mesh.bounds[5]]],
                    [f"{int(f)} Гц"],
                    font_size=10, text_color="#008B8B", shape=None, show_points=False,
                )
            
            # Обновляем заголовок
            start_time_sec = self.times[t0] if t0 < len(self.times) else 0
            end_time_sec = self.times[t1 - 1] if t1 > 0 and t1 <= len(self.times) else self.times[-1] if len(self.times) > 0 else 0
            self.plotter.title = f"Полная спектрограмма | Время: {start_time_sec:.2f}-{end_time_sec:.2f} сек | Частота: 0-{actual_freq_khz:.1f} кГц"
            
            # Сбрасываем камеру для лучшего обзора
            self.plotter.camera_position = 'iso'
            self.plotter.render()
            
        except Exception as e:
            print(f"Ошибка обновления меша для сегмента: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна - очистка ресурсов OpenGL."""
        try:
            # Очищаем все акторы
            if self.plotter is not None:
                try:
                    # Удаляем все акторы
                    actors = self.plotter.renderer.GetActors()
                    actors.InitTraversal()
                    actor = actors.GetNextItem()
                    while actor:
                        self.plotter.remove_actor(actor)
                        actor = actors.GetNextItem()
                except Exception:
                    pass
                
                # Очищаем plotter
                try:
                    self.plotter.close()
                except Exception:
                    pass
            
            # Очищаем mesh
            if self.mesh is not None:
                try:
                    self.mesh.Clear()
                    self.mesh = None
                except Exception:
                    pass
            
            # Сбрасываем ссылки
            self.plotter = None
            self.mesh = None
            
        except Exception as e:
            print(f"Ошибка при закрытии окна спектрограммы: {e}")
        
        event.accept()

