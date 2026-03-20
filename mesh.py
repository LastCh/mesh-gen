"""Главный класс приложения для 3D визуализации аудио."""

import sys
import os
import json
import datetime
import traceback
import time
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QMessageBox, QShortcut, QInputDialog
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtGui import QKeySequence, QIcon
import warnings
import logging

# Импорты модулей
from audio_processor import AudioProcessor
from mesh_generator import MeshGenerator
from mesh_cache import MeshCache
from media_controller import MediaController
from ui_components import ControlPanel, TimelineWidget
from config_manager import ConfigManager
from utils import format_time, calculate_frame_index
from visualization_settings import VisualizationSettings
from mesh_ai import extract_height_map, MeshNavigationEnv, MeshQLearningAgent
from camera_presets import CameraPresets
from full_spectrogram_window import FullSpectrogramWindow
from stft_settings_panel import STFTSettingsPanel
from help_dialog import HelpDialog
 
# Подавляем предупреждения
warnings.filterwarnings('ignore', category=UserWarning)
logging.getLogger('pyvista').setLevel(logging.ERROR)
logging.getLogger('VTK').setLevel(logging.ERROR)


class AudioMeshVisualizer(QWidget):
    """Главный класс приложения для визуализации аудио в 3D."""
    
    def __init__(self):
        """Инициализация визуализатора."""
        super().__init__()
        self.setWindowTitle("3D Аудио Визуализатор")
        self.resize(1400, 800)
        
        # Устанавливаем иконку приложения
        icon_path = os.path.join(os.path.dirname(__file__), 'photo_2025-03-04_00-35-20.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Параметры STFT
        self.n_fft = 2048
        self.hop_length = 512
        self.window_size = 150
        self.window_type = 'hann'
        
        # Компоненты
        self.audio_processor = AudioProcessor(n_fft=self.n_fft, hop_length=self.hop_length)
        
        # Обновляем параметры STFT из панели настроек
        self.stft_settings_panel = None  # Будет инициализировано в init_ui
        self.mesh_generator = MeshGenerator()
        self.mesh_cache = MeshCache(max_size=10)
        self.media_controller = MediaController()
        self.config_manager = ConfigManager()
        self.visualization_settings = VisualizationSettings()
        self.camera_presets = CameraPresets()
        self._help_dialog = None
        self._frame_counter = 0
        self._last_stats_time = time.time()
        
        # Параметры визуализации
        self.freq_max = 20000
        self.last_start_frame = -1
        self.saved_camera_position = None
        
        # Метки частоты
        self.freq_label_actors = []
        self.last_freq_max_cached = None
        
        # Меш и актор
        self.mesh_actor = None
        self.current_mesh = None
        self.ai_path_actor = None
        self._last_mesh_shape = None
        self._needs_mesh_rebuild = False
        
        # Таймеры
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.update_mesh_realtime)
        
        self._amp_update_timer = QTimer()
        self._amp_update_timer.setSingleShot(True)
        self._amp_update_timer.timeout.connect(self._apply_amp_change)
        
        self._freq_update_timer = QTimer()
        self._freq_update_timer.setSingleShot(True)
        self._freq_update_timer.timeout.connect(self._apply_freq_change)
        
        self._stats_timer = QTimer()
        self._stats_timer.setInterval(500)
        self._stats_timer.timeout.connect(self.update_stats_label)
        
        # Загружаем сохраненную позицию камеры
        saved_camera = self.config_manager.get_camera_position()
        if saved_camera:
            self.saved_camera_position = saved_camera
        
        # UI
        self.init_ui()
        self._stats_timer.start()
        
        # Подключаем сигналы медиа контроллера
        self.media_controller.connect_signals(
            position_changed=self.update_position,
            state_changed=self.on_media_state_changed
        )
    
    def init_ui(self):
        """Инициализация UI."""
        main_layout = QHBoxLayout()
        
        # Левая панель управления
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel, 0)
        
        # Панель настроек STFT
        self.stft_settings_panel = STFTSettingsPanel()
        self.stft_settings_panel.recalculate_requested.connect(self.on_stft_recalculate)
        
        # Заменяем placeholder на панель STFT
        if getattr(self.control_panel, 'stft_settings_placeholder', None):
            try:
                self.control_panel.stft_group.content_layout.removeWidget(
                    self.control_panel.stft_settings_placeholder
                )
            except Exception:
                pass
            self.control_panel.stft_settings_placeholder.setParent(None)
            self.control_panel.stft_settings_placeholder = None
        self.control_panel.stft_group.addWidget(self.stft_settings_panel)
        
        # Timeline widget
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.seek_requested.connect(self.seek_audio)
        
        # Подключаем сигналы панели управления
        self.control_panel.button.clicked.connect(self.load_audio)
        self.control_panel.freq_slider.valueChanged.connect(self.update_freq_slider)
        self.control_panel.amp_slider.valueChanged.connect(self.update_amp_label)
        # Слайдер размера окна
        self.control_panel.window_size_slider.valueChanged.connect(self.update_window_size)
        self.control_panel.volume_slider.valueChanged.connect(self.change_volume)
        self.control_panel.play_btn.clicked.connect(self.play_audio)
        self.control_panel.pause_btn.clicked.connect(self.pause_audio)
        self.control_panel.stop_btn.clicked.connect(self.stop_audio)
        self.control_panel.full_btn.clicked.connect(self.show_full_spectrogram)
        self.control_panel.export_btn.clicked.connect(self.export_mesh)
        self.control_panel.ai_train_btn.clicked.connect(self.train_ai_on_current_mesh)
        self.control_panel.ai_load_btn.clicked.connect(self.load_ai_path)
        self.control_panel.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)
        self.control_panel.range_checkbox.toggled.connect(self.on_range_checkbox_toggled)
        self.control_panel.min_db_spinbox.valueChanged.connect(self.on_range_changed)
        self.control_panel.max_db_spinbox.valueChanged.connect(self.on_range_changed)
        self.control_panel.help_btn.clicked.connect(self.show_help)
        
        # Заменяем progress bar на timeline widget
        layout = self.control_panel.layout()
        progress_index = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() == self.control_panel.progress_bar:
                progress_index = i
                break
        
        if progress_index is not None:
            layout.removeWidget(self.control_panel.progress_bar)
            self.control_panel.progress_bar.setParent(None)
            layout.insertWidget(progress_index, self.timeline_widget)
        else:
            # Если не нашли, просто добавляем
            layout.insertWidget(3, self.timeline_widget)
        
        # Область визуализации
        pv_layout = QVBoxLayout()
        self.plotter_label = QLabel("Визуализация (сегмент 0.00 - 0.00 сек) | Частота: 0 - 20 кГц")
        self.plotter_label.setStyleSheet("font-weight: bold;")
        pv_layout.addWidget(self.plotter_label)
        
        # Панель инструментов для камеры
        camera_toolbar = QHBoxLayout()
        camera_toolbar.addWidget(QLabel("Камера:"))
        
        self.camera_iso_btn = QPushButton("Изометрия")
        self.camera_iso_btn.clicked.connect(lambda: self.apply_camera_preset('iso'))
        camera_toolbar.addWidget(self.camera_iso_btn)
        
        self.camera_top_btn = QPushButton("Сверху")
        self.camera_top_btn.clicked.connect(lambda: self.apply_camera_preset('top'))
        camera_toolbar.addWidget(self.camera_top_btn)
        
        self.camera_side_btn = QPushButton("Сбоку")
        self.camera_side_btn.clicked.connect(lambda: self.apply_camera_preset('side'))
        camera_toolbar.addWidget(self.camera_side_btn)
        
        self.camera_front_btn = QPushButton("Спереди")
        self.camera_front_btn.clicked.connect(lambda: self.apply_camera_preset('front'))
        camera_toolbar.addWidget(self.camera_front_btn)
        
        camera_toolbar.addStretch()
        
        pv_layout.addLayout(camera_toolbar)
        
        self.plotter = QtInteractor(self)
        self.plotter.set_background("white")
        pv_layout.addWidget(self.plotter)
        
        # Статус бар
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(4, 2, 4, 2)
        self.status_label = QLabel("FPS: 0 | Вершин: 0 | Граней: 0 | Кэш: 0/10")
        self.status_label.setStyleSheet("font-size: 9px; color: #666; padding: 4px;")
        self.status_label.setMinimumHeight(20)
        self.status_label.setMaximumHeight(25)
        status_bar.addWidget(self.status_label)
        pv_layout.addLayout(status_bar)
        
        main_layout.addLayout(pv_layout, 1)
        self.setLayout(main_layout)
    
    def update_freq_slider(self, value):
        """Обработчик изменения слайдера частоты."""
        self.freq_max = value * 1000
        self.control_panel.freq_value_label.setText(f"{value} кГц")
        self._freq_update_timer.stop()
        self._freq_update_timer.start(200)
    
    def _apply_freq_change(self):
        """Применяет изменение частоты с дебаунсом."""
        if self.audio_processor.spectrogram_data is not None:
            if self.plotter.camera_position is not None:
                self.saved_camera_position = self.plotter.camera_position
            self.last_freq_max_cached = None
            self.mesh_cache.invalidate(freq_max=self.freq_max)
            self._request_mesh_rebuild()
    
    def update_amp_label(self, v):
        """Обработчик изменения слайдера усиления."""
        self.control_panel.amp_label.setText(f"{v / 10:.1f}x")
        self._amp_update_timer.stop()
        self._amp_update_timer.start(200)
    
    def _apply_amp_change(self):
        """Применяет изменение усиления с дебаунсом."""
        if self.audio_processor.spectrogram_data is not None:
            if self.plotter.camera_position is not None:
                self.saved_camera_position = self.plotter.camera_position
            amp = self.control_panel.amp_slider.value() / 10.0
            self.mesh_cache.invalidate(amp=amp)
            self._request_mesh_rebuild()
    
    def update_window_size(self, value):
        """Обработчик изменения размера окна."""
        self.window_size = value
        self.control_panel.window_size_label.setText(str(value))
        # Обновляем меш с новым размером окна
        if self.audio_processor.spectrogram_data is not None:
            if self.plotter.camera_position is not None:
                self.saved_camera_position = self.plotter.camera_position
            self.mesh_cache.clear()  # Очищаем кэш при изменении размера окна
            self._last_mesh_shape = None
            self._request_mesh_rebuild()
    
    def change_volume(self, value):
        """Изменяет громкость."""
        self.media_controller.set_volume(value)
        self.control_panel.volume_label.setText(f"{value}%")
    
    def on_colormap_changed(self, colormap):
        """Обработчик изменения цветовой карты."""
        self.visualization_settings.set_colormap(colormap)
        if self.mesh_actor is not None:
            # Обновляем цветовую карту
            self.mesh_actor.mapper.scalar_map_mode = 'default'
            # Пересоздаем актор с новой цветовой картой
            if self.current_mesh is not None:
                min_db, max_db = self.visualization_settings.get_active_range()
                try:
                    self.plotter.remove_actor(self.mesh_actor)
                except Exception:
                    pass
                self.mesh_actor = self.plotter.add_mesh(
                    self.current_mesh, scalars="amplitude",
                    cmap=self.visualization_settings.colormap,
                    clim=[min_db, max_db] if min_db is not None and max_db is not None else None,
                    show_edges=False, lighting=True, ambient=0.3,
                    specular=0.5, smooth_shading=True, name='audio_mesh',
                    scalar_bar_args={'title': 'Amplitude, dB', 'n_labels': 5, 'fmt': '%.1f', 'vertical': True}
                )
                self.plotter.render()
    
    def on_range_checkbox_toggled(self, checked):
        """Обработчик переключения пользовательского диапазона."""
        if checked:
            # Используем значения из spinbox
            min_db = self.control_panel.min_db_spinbox.value()
            max_db = self.control_panel.max_db_spinbox.value()
            self.visualization_settings.set_custom_range(min_db, max_db)
        else:
            # Используем глобальный диапазон
            self.visualization_settings.reset_range()
        
        # Обновляем визуализацию
        if self.mesh_actor is not None:
            min_db, max_db = self.visualization_settings.get_active_range()
            if min_db is not None and max_db is not None:
                self.mesh_actor.mapper.SetScalarRange(min_db, max_db)
                self.plotter.render()
    
    def on_range_changed(self):
        """Обработчик изменения диапазона амплитуд."""
        if self.control_panel.range_checkbox.isChecked():
            min_db = self.control_panel.min_db_spinbox.value()
            max_db = self.control_panel.max_db_spinbox.value()
            self.visualization_settings.set_custom_range(min_db, max_db)
            
            # Обновляем визуализацию
            if self.mesh_actor is not None:
                self.mesh_actor.mapper.SetScalarRange(min_db, max_db)
                self.plotter.render()
    
    def apply_camera_preset(self, preset_name):
        """Применяет пресет камеры.
        
        Args:
            preset_name: Имя пресета ('iso', 'top', 'side', 'front')
        """
        bounds = self.current_mesh.bounds if self.current_mesh is not None else None
        self.camera_presets.apply_to_plotter(self.plotter, preset_name, bounds=bounds)
        # Сохраняем позицию камеры
        if self.plotter.camera_position is not None:
            self.saved_camera_position = self.plotter.camera_position
    
    def load_audio(self):
        """Загружает аудио файл."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите аудиофайл", "", "Аудио (*.wav *.mp3)"
        )
        if not file_path:
            return
        
        try:
            self.control_panel.label.setText("Загрузка...")
            QtWidgets.QApplication.processEvents()
            
            # Загружаем аудио через AudioProcessor
            self.audio_processor.load_audio(file_path)
            self.stft_settings_panel.set_sample_rate(self.audio_processor.sample_rate)
            self.stft_settings_panel.update_info_with_sample_rate(self.audio_processor.sample_rate)
            
            # Устанавливаем глобальный диапазон dB в настройках визуализации
            self.visualization_settings.set_global_db_range(
                self.audio_processor.db_min,
                self.audio_processor.db_max
            )
            
            # Обновляем значения в spinbox
            self.control_panel.min_db_spinbox.setValue(self.audio_processor.db_min)
            self.control_panel.max_db_spinbox.setValue(self.audio_processor.db_max)
            self.control_panel.min_db_spinbox.setRange(
                self.audio_processor.db_min - 20, 
                self.audio_processor.db_max + 20
            )
            self.control_panel.max_db_spinbox.setRange(
                self.audio_processor.db_min - 20, 
                self.audio_processor.db_max + 20
            )
            
            # Подготавливаем медиа для воспроизведения
            self.media_controller.load_file(file_path, callback=self._on_media_loaded)
            
            # Обновляем UI
            info = self.audio_processor.get_audio_info()
            if info:
                self.control_panel.info_label.setText(
                    f"✓ {info['filename']}\n"
                    f"Длительность: {info['duration']:.1f} сек\n"
                    f"Sample rate: {info['sample_rate']} Гц\n"
                    f"N_fft: {info['n_fft']}\n"
                    f"Кадров: {info['frames']}\n"
                    f"Частот: {info['frequencies']}\n\n"
                    f"Диапазон амплитуды: {info['db_min']:.1f} - {info['db_max']:.1f} дБ"
                )
                
                # Устанавливаем длительность для timeline
                duration_ms = int(info['duration'] * 1000)
                self.timeline_widget.set_duration(duration_ms)
            
            self.control_panel.label.setText(f"✓ {info['filename'] if info else 'Загружено'}")
            self.control_panel.play_btn.setEnabled(True)
            self.control_panel.full_btn.setEnabled(True)
            self.control_panel.export_btn.setEnabled(True)
            self.control_panel.ai_train_btn.setEnabled(True)
            self.control_panel.ai_load_btn.setEnabled(True)
            self.control_panel.ai_save_checkbox.setEnabled(True)
            self.control_panel.ai_progress_checkbox.setEnabled(True)
            self.control_panel.ai_episodes_spin.setEnabled(True)
            self.control_panel.ai_log_paths_checkbox.setEnabled(True)
            self.control_panel.ai_log_every_spin.setEnabled(True)
            # Сбрасываем кеш для ИИ
            self._current_grid_points = None
            # Очищаем кэш
            self._clear_visualization()
            self.mesh_cache.clear()
            self.last_start_frame = -1
            # Не строим визуализацию сразу — только по Play
            
        except Exception as e:
            self.control_panel.label.setText(f"Ошибка: {str(e)[:50]}")
            traceback.print_exc()
    
    def _on_media_loaded(self, success):
        """Обработчик успешной загрузки медиа."""
        if success:
            self.control_panel.play_btn.setEnabled(True)
    
    def train_ai_on_current_mesh(self):
        """Запускает простое Q-обучение навигации по текущему мешу."""
        if self.audio_processor.spectrogram_data is None:
            QMessageBox.warning(self, "Обучение ИИ", "Сначала загрузите аудио и постройте меш.")
            return
        try:
            if self.current_mesh is None:
                self.init_mesh_static()
            if self.current_mesh is None:
                QMessageBox.warning(self, "Обучение ИИ", "Нет активного меша для обучения.")
                return

            height_map, meta = extract_height_map(self.current_mesh, max_size=96)
            grid_points = meta.get("grid_points")
            self._current_grid_points = grid_points
            if grid_points is None or grid_points.size == 0:
                QMessageBox.warning(self, "Обучение ИИ", "Не удалось подготовить сетку меша.")
                return
            amp_map = meta.get("amplitudes")

            # Старт/цель по центру частотной оси (Y=время, X=частота)
            start = (0, grid_points.shape[1] // 2)
            goal = (grid_points.shape[0] - 1, grid_points.shape[1] // 2)

            # Позволяем выбрать координаты вручную (X,Y), автокоррекция в границах
            use_custom = QMessageBox.question(
                self,
                "Обучение ИИ",
                f"Использовать пользовательские координаты?\n"
                f"X — частота (0..{grid_points.shape[1]-1}), Y — время (0..{grid_points.shape[0]-1})",
            )
            if use_custom == QMessageBox.Yes:
                sx, ok = QInputDialog.getInt(
                    self, "Старт: X (частота)", f"0 .. {grid_points.shape[1]-1}", value=start[1],
                    min=0, max=max(0, grid_points.shape[1]-1)
                )
                sy, ok2 = (QInputDialog.getInt(
                    self, "Старт: Y (время)", f"0 .. {grid_points.shape[0]-1}", value=start[0],
                    min=0, max=max(0, grid_points.shape[0]-1)
                ) if ok else (None, False))
                gx, ok3 = (QInputDialog.getInt(
                    self, "Цель: X (частота)", f"0 .. {grid_points.shape[1]-1}", value=goal[1],
                    min=0, max=max(0, grid_points.shape[1]-1)
                ) if ok2 else (None, False))
                gy, ok4 = (QInputDialog.getInt(
                    self, "Цель: Y (время)", f"0 .. {grid_points.shape[0]-1}", value=goal[0],
                    min=0, max=max(0, grid_points.shape[0]-1)
                ) if ok3 else (None, False))
                if ok and ok2 and ok3 and ok4:
                    sy = int(np.clip(sy, 0, grid_points.shape[0]-1))
                    sx = int(np.clip(sx, 0, grid_points.shape[1]-1))
                    gy = int(np.clip(gy, 0, grid_points.shape[0]-1))
                    gx = int(np.clip(gx, 0, grid_points.shape[1]-1))
                    start = (sy, sx)  # (Y, X) -> (row, col)
                    goal = (gy, gx)

            env = MeshNavigationEnv(
                height_map=height_map,
                start=start,
                goal=goal,
                slope_penalty=0.35,
                step_cost=0.01,
                goal_reward=2.0,
                out_penalty=0.6,
                max_steps=height_map.size * 3,
                amplitude_map=amp_map,
                amplitude_weight=float(self.control_panel.ai_amp_penalty.value()) if amp_map is not None else 0.0,
                slope_hard_limit=float(self.control_panel.ai_slope_limit.value()) if self.control_panel.ai_slope_block_checkbox.isChecked() else None,
            )
            agent = MeshQLearningAgent(env)
            episodes = int(self.control_panel.ai_episodes_spin.value())
            progress_dialog = None
            save_paths_per_episode = self.control_panel.ai_log_paths_checkbox.isChecked()
            log_every = int(self.control_panel.ai_log_every_spin.value())
            saved_paths_idx = []
            last_avg20 = 0.0

            def progress_cb(stat):
                if progress_dialog:
                    nonlocal last_avg20
                    # скользящее среднее по последним 20 эпизодам
                    recent = stats[-19:] + [stat] if len(stats) >= 19 else stats + [stat]
                    if recent:
                        last_avg20 = np.mean([s["total_reward"] for s in recent])
                    progress_dialog.setValue(stat["episode"])
                    progress_dialog.setLabelText(
                        f"Эпизод {stat['episode']}/{episodes}\n"
                        f"Награда: {stat['total_reward']:.2f} | ср(20): {last_avg20:.2f}\n"
                        f"ε={stat['epsilon']:.3f}"
                    )
                    QtWidgets.QApplication.processEvents()

            if self.control_panel.ai_progress_checkbox.isChecked():
                progress_dialog = QtWidgets.QProgressDialog(
                    "Обучение агента...", None, 0, episodes, self
                )
                progress_dialog.setWindowTitle("ИИ: обучение")
                progress_dialog.setAutoClose(True)
                progress_dialog.setCancelButton(None)
                progress_dialog.show()

            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            stats = agent.train(
                episodes=episodes,
                max_steps=height_map.size * 3,
                progress_cb=progress_cb,
                paths_recorder=lambda ep, path_idx: (
                    saved_paths_idx.append((ep, path_idx))
                    if save_paths_per_episode and (ep % log_every == 0 or ep == episodes)
                    else None
                ),
            )
            path, total_reward, reached = agent.rollout(
                max_steps=height_map.size * 3, explore=False
            )
            QtWidgets.QApplication.restoreOverrideCursor()
            if progress_dialog:
                progress_dialog.setValue(episodes)

            # Приводим путь к 3D-точкам меша
            def idx_path_to_points(idx_path):
                pts = []
                for i, j in idx_path:
                    if 0 <= i < grid_points.shape[0] and 0 <= j < grid_points.shape[1]:
                        pts.append(grid_points[i, j])
                return np.array(pts)

            path_points = idx_path_to_points(path)
            self._render_ai_path(np.array(path_points), reached=reached, grid_points=self._current_grid_points)

            # Показать какие координаты (X,Y,Z) реально использованы
            start_xyz = grid_points[start[0], start[1]]
            goal_xyz = grid_points[goal[0], goal[1]]

            # Конвертируем сохраненные эпизодные пути в XYZ
            saved_paths_xyz = []
            if saved_paths_idx:
                for ep_num, idx_path in saved_paths_idx:
                    saved_paths_xyz.append((ep_num, idx_path_to_points(idx_path)))

            avg_reward = (
                np.mean([s["total_reward"] for s in stats[-10:]]) if stats else total_reward
            )
            msg = (
                f"Эпизодов: {episodes}\n"
                f"Достиг цель: {'да' if reached else 'нет'}\n"
                f"Награда (последняя/средняя): {total_reward:.2f} / {avg_reward:.2f}\n"
                f"Размер сетки: {height_map.shape[0]}x{height_map.shape[1]}\n"
                f"Длина финального пути (шагов): {len(path_points)}\n"
                f"Старт (X,Y,Z): ({start[1]}, {start[0]}, {start_xyz[2]:.3f})\n"
                f"Цель (X,Y,Z): ({goal[1]}, {goal[0]}, {goal_xyz[2]:.3f})"
            )

            # Сохранение логов и пути
            if self.control_panel.ai_save_checkbox.isChecked():
                save_dir = QFileDialog.getExistingDirectory(
                    self, "Куда сохранить результаты обучения"
                )
                if save_dir:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    base = os.path.join(save_dir, f"ai_run_{ts}")
                    try:
                        np.save(base + "_path.npy", np.array(path_points))
                        if saved_paths_xyz:
                            ep_dir = base + "_episodes"
                            os.makedirs(ep_dir, exist_ok=True)
                            index = []
                            for ep_num, pts in saved_paths_xyz:
                                fn = os.path.join(ep_dir, f"path_ep{ep_num:04d}.npy")
                                np.save(fn, pts)
                                index.append({"episode": ep_num, "file": os.path.basename(fn)})
                            with open(os.path.join(ep_dir, "index.json"), "w", encoding="utf-8") as f_idx:
                                json.dump(index, f_idx, ensure_ascii=False, indent=2)
                        with open(base + "_stats.json", "w", encoding="utf-8") as f:
                            json.dump(
                                {
                                    "episodes": episodes,
                                    "reached": reached,
                                    "total_reward": total_reward,
                                    "avg_reward_last10": avg_reward,
                                    "grid_shape": list(height_map.shape),
                                    "start": list(start),
                                    "goal": list(goal),
                                    "stats": stats,
                                },
                                f,
                                ensure_ascii=False,
                                indent=2,
                            )
                        msg += f"\nСохранено: {base}_path.npy и {base}_stats.json"
                        if saved_paths_xyz:
                            msg += f"\nПути по эпизодам: {ep_dir}"
                    except Exception as save_exc:
                        msg += f"\nНе удалось сохранить: {save_exc}"

            QMessageBox.information(self, "Обучение ИИ", msg)
        except Exception as e:
            QtWidgets.QApplication.restoreOverrideCursor()
            traceback.print_exc()
            QMessageBox.warning(self, "Обучение ИИ", f"Не удалось запустить обучение: {e}")

    def load_ai_path(self):
        """Загружает сохранённый путь/лог и рисует поверх текущего меша."""
        try:
            npy_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл пути (*.npy)", "", "NumPy (*.npy)"
            )
            if not npy_path:
                return
            path_points = np.load(npy_path)
            self._render_ai_path(path_points)

            json_path = npy_path.replace("_path.npy", "_stats.json")
            stats_text = ""
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    stats_text = (
                        f"Эпизодов: {data.get('episodes')}\n"
                        f"Достиг цель: {data.get('reached')}\n"
                        f"Последняя награда: {data.get('total_reward')}\n"
                        f"Средняя (посл.10): {data.get('avg_reward_last10')}\n"
                        f"Старт: {data.get('start')}, Цель: {data.get('goal')}"
                    )
                except Exception:
                    stats_text = "Лог не удалось прочитать."

            if path_points is not None and len(path_points) > 0:
                msg = "Путь загружен и отображён."
                if stats_text:
                    msg += "\n\n" + stats_text
                QMessageBox.information(self, "Загрузка пути ИИ", msg)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Загрузка пути ИИ", f"Не удалось загрузить: {e}")

    def _render_ai_path(self, points: np.ndarray, reached: bool = True, grid_points=None, upsample=4):
        """Отрисовывает найденный путь агента на текущем меше.
        
        Args:
            points: np.ndarray shape (N,3) — путь в координатах меша
            reached: достигнута ли цель (для цвета)
            grid_points: опционально регулярная сетка для пересэмплинга по поверхности
            upsample: сколько промежуточных точек добавлять на сегмент
        """
        try:
            if self.ai_path_actor is not None:
                self.plotter.remove_actor(self.ai_path_actor)
                self.ai_path_actor = None
        except Exception:
            pass

        if points is None or len(points) < 2:
            return

        try:
            def upsample_polyline(pts, k=upsample):
                if pts is None or len(pts) < 2 or k <= 1:
                    return pts
                out = [pts[0]]
                for a, b in zip(pts[:-1], pts[1:]):
                    for t in np.linspace(0, 1, k, endpoint=False)[1:]:
                        p = a * (1 - t) + b * t
                        out.append(p)
                out.append(pts[-1])
                return np.array(out)

            pts = points.copy()
            if grid_points is not None and pts.shape[1] >= 2:
                # При наличии сетки поджимаем Z к поверхности (ближайшая ячейка)
                g0, g1 = grid_points.shape[0], grid_points.shape[1]
                for i, p in enumerate(pts):
                    y = int(np.clip(round(p[1]), 0, g0 - 1))
                    x = int(np.clip(round(p[0]), 0, g1 - 1))
                    pts[i, 2] = grid_points[y, x, 2]

            pts_up = upsample_polyline(pts, max(2, upsample))
            lines = np.hstack(([pts_up.shape[0]], np.arange(pts_up.shape[0], dtype=np.int32)))
            poly = pv.PolyData(pts_up, lines=lines)
            color = "#d62728" if reached else "#ff8c00"
            self.ai_path_actor = self.plotter.add_mesh(
                poly,
                color=color,
                line_width=6,
                name="ai_path",
                render_lines_as_tubes=True,
            )
            self.plotter.render()
        except Exception as e:
            print(f"Ошибка отрисовки пути ИИ: {e}")

    def remove_freq_labels(self):
        """Удаляет метки частот."""
        for a in list(self.freq_label_actors):
            try:
                self.plotter.remove_actor(a)
            except Exception:
                pass
        self.freq_label_actors = []
    
    def add_freq_labels(self, mesh):
        """Добавляет метки частот на меш."""
        if self.last_freq_max_cached == self.freq_max and self.freq_label_actors:
            return
        
        self.last_freq_max_cached = self.freq_max
        self.remove_freq_labels()
        
        freq_ticks = np.linspace(0, self.freq_max, 6)
        for f in freq_ticks:
            y_min, y_max = mesh.bounds[2], mesh.bounds[3]
            y_pos = y_min + (f / max(1.0, self.freq_max)) * (y_max - y_min)
            actor = self.plotter.add_point_labels(
                [[mesh.bounds[0], y_pos, mesh.bounds[5]]],
                [f"{int(f)} Гц"],
                font_size=10, text_color="#008B8B", shape=None, show_points=False,
            )
            self.freq_label_actors.append(actor)
    
    def _add_axis_labels(self, mesh):
        """Добавляет метки осей (время, частота, амплитуда)."""
        try:
            # Метки времени на оси X
            if hasattr(self, '_time_label_actors'):
                for actor in self._time_label_actors:
                    try:
                        self.plotter.remove_actor(actor)
                    except Exception:
                        pass
            else:
                self._time_label_actors = []
            
            # Добавляем метки времени (если есть временной диапазон)
            if hasattr(self, '_last_time_range'):
                t0, t1 = self._last_time_range
                time_start = self.audio_processor.times[t0] if t0 < len(self.audio_processor.times) else 0
                time_end = self.audio_processor.times[t1 - 1] if t1 > 0 and t1 <= len(self.audio_processor.times) else self.audio_processor.times[-1]
                
                # Метки времени в начале и конце
                time_ticks = [time_start, (time_start + time_end) / 2, time_end]
                for t in time_ticks:
                    x_pos = mesh.bounds[0] + (t - time_start) / (time_end - time_start + 1e-9) * (mesh.bounds[1] - mesh.bounds[0])
                    actor = self.plotter.add_point_labels(
                        [[x_pos, mesh.bounds[2], mesh.bounds[5]]],
                        [f"{t:.2f}с"],
                        font_size=9, text_color="#666666", shape=None, show_points=False,
                    )
                    self._time_label_actors.append(actor)
            
            # Метки амплитуды на оси Z (если включена глобальная нормализация)
            if hasattr(self, '_amplitude_label_actors'):
                for actor in self._amplitude_label_actors:
                    try:
                        self.plotter.remove_actor(actor)
                    except Exception:
                        pass
            else:
                self._amplitude_label_actors = []
            
            # Добавляем метки амплитуды в dB
            min_db, max_db = self.visualization_settings.get_active_range()
            if min_db is not None and max_db is not None:
                amp_ticks = np.linspace(min_db, max_db, 5)
                for amp_db in amp_ticks:
                    # Нормализуем амплитуду для Z координаты
                    amp_norm = (amp_db - min_db) / (max_db - min_db + 1e-9)
                    z_pos = mesh.bounds[4] + amp_norm * (mesh.bounds[5] - mesh.bounds[4])
                    actor = self.plotter.add_point_labels(
                        [[mesh.bounds[0], mesh.bounds[2], z_pos]],
                        [f"{amp_db:.1f}дБ"],
                        font_size=9, text_color="#666666", shape=None, show_points=False,
                    )
                    self._amplitude_label_actors.append(actor)
        except Exception as e:
            print(f"Ошибка добавления меток осей: {e}")
    
    def _create_mesh_callback(self, t0, t1, freq_max, amp):
        """Callback для создания меша (используется кэшем)."""
        mesh, actual_freq_khz = self.mesh_generator.create_mesh(
            self.audio_processor.spectrogram_data,
            t0, t1,
            freq_max,
            amp,
            self.audio_processor.freqs,
            z_min=self.audio_processor.db_min,
            z_max=self.audio_processor.db_max,
            use_global_normalization=True
        )
        return mesh
    
    def init_mesh_static(self):
        """Инициализирует статический меш."""
        if self.audio_processor.spectrogram_data is None:
            return
        
        try:
            pos_ms = self.media_controller.get_position()
            if pos_ms is None or pos_ms <= 0:
                frame_idx = self.last_start_frame if self.last_start_frame >= 0 else 0
            else:
                frame_idx = calculate_frame_index(
                    pos_ms,
                    self.audio_processor.sample_rate,
                    self.hop_length
                )
        except Exception:
            frame_idx = self.last_start_frame if self.last_start_frame >= 0 else 0
        
        t0 = max(0, frame_idx - self.window_size // 2)
        t1 = min(t0 + self.window_size, self.audio_processor.spectrogram_data.shape[0])
        
        if t0 >= t1:
            t1 = min(t0 + 1, self.audio_processor.spectrogram_data.shape[0])
        
        try:
            if self.mesh_actor is not None:
                self.plotter.remove_actor(self.mesh_actor)
                # Очищаем память
                if self.current_mesh:
                    self.current_mesh.Clear()
        except Exception:
            pass
        
        try:
            amp = self.control_panel.amp_slider.value() / 10.0
            
            # Используем кэш для получения меша
            mesh = self.mesh_cache.get_mesh(
                t0, t1, self.freq_max, amp,
                self._create_mesh_callback
            )
            
            self.current_mesh = mesh
            # Страхуем наличие скаляров 'amplitude'
            try:
                if 'amplitude' not in self.current_mesh.point_data:
                    # Получим Z для текущего окна для заполнения амплитуд
                    Z_fill, _ = self.audio_processor.get_spectrogram_segment(t0, t1, self.freq_max)
                    if Z_fill is not None and Z_fill.size > 0:
                        self.current_mesh.point_data["amplitude"] = Z_fill.ravel()
            except Exception:
                pass
            
            # Получаем actual_freq_khz
            idx_freq = np.searchsorted(self.audio_processor.freqs, self.freq_max)
            actual_freq_khz = self.audio_processor.freqs[idx_freq - 1] / 1000 if idx_freq > 0 else 0
            
            # Получаем активный диапазон для цветов
            min_db, max_db = self.visualization_settings.get_active_range()
            
            self.mesh_actor = self.plotter.add_mesh(
                mesh, scalars="amplitude", 
                cmap=self.visualization_settings.colormap,
                clim=[min_db, max_db] if min_db is not None and max_db is not None else None,
                show_edges=False, lighting=True, ambient=0.3,
                specular=0.5, smooth_shading=True, name='audio_mesh',
                scalar_bar_args={'title': 'Amplitude (dB)', 'n_labels': 5, 'fmt': '%.1f'}
            )
            
            # Частотные подписи
            self.add_freq_labels(mesh)
            
            time_start = self.audio_processor.times[t0] if t0 < len(self.audio_processor.times) else 0
            time_end = self.audio_processor.times[t1 - 1] if t1 > 0 and t1 <= len(self.audio_processor.times) else self.audio_processor.times[-1]
            self.plotter_label.setText(
                f"Визуализация (сегмент {time_start:.2f} - {time_end:.2f} сек) | Частота: 0 - {actual_freq_khz:.1f} кГц"
            )
            
            if self.saved_camera_position is not None:
                self.plotter.camera_position = self.saved_camera_position
            else:
                self.plotter.camera_position = 'iso'
            
            self.plotter.render()
            self._frame_counter += 1
            self.last_start_frame = t0
            self._last_time_range = (t0, t1)
            self._needs_mesh_rebuild = False
            
        except Exception as e:
            print(f"Ошибка в init_mesh_static: {e}")
            traceback.print_exc()
    
    def update_mesh_realtime(self):
        """Оптимизированное обновление меша в реальном времени."""
        if self.audio_processor.spectrogram_data is None or self.mesh_actor is None:
            return
        
        try:
            position = self.media_controller.get_position()
        except Exception:
            position = 0
        
        frame_idx = calculate_frame_index(
            position,
            self.audio_processor.sample_rate,
            self.hop_length
        )
        t0 = max(0, frame_idx - self.window_size // 2)
        t1 = min(t0 + self.window_size, self.audio_processor.spectrogram_data.shape[0])
        
        if t0 == self.last_start_frame:
            return
        
        self.last_start_frame = t0
        
        try:
            # Получаем сегмент спектрограммы
            Z, actual_freq_khz = self.audio_processor.get_spectrogram_segment(t0, t1, self.freq_max)
            
            if Z is None or Z.size == 0:
                return
            
            amp = self.control_panel.amp_slider.value() / 10.0
            
            # Оптимизация: обновляем только вершины если структура меша не изменилась
            if self.current_mesh is not None:
                # Проверяем, изменилась ли структура (размеры)
                Tn, Fn = Z.shape
                if hasattr(self, '_last_mesh_shape') and self._last_mesh_shape == (Tn, Fn):
                    # Обновляем только Z координаты
                    self.mesh_generator.update_mesh_vertices(
                        self.current_mesh, Z, amp,
                        z_min=self.audio_processor.db_min,
                        z_max=self.audio_processor.db_max,
                        use_global_normalization=True
                    )
                    
                    # Обновляем актор - используем SetInputDataObject для обновления
                    self.mesh_actor.mapper.SetInputDataObject(self.current_mesh)
                    self.mesh_actor.mapper.Update()
                    # Обновляем scalars для цветовой карты
                    self.mesh_actor.mapper.scalar_map_mode = 'default'
                else:
                    # Структура изменилась, создаем новый меш
                    self._last_mesh_shape = (Tn, Fn)
                    mesh = self.mesh_cache.get_mesh(
                        t0, t1, self.freq_max, amp,
                        self._create_mesh_callback
                    )
                    self.current_mesh = mesh
                    # Страхуем наличие скаляров 'amplitude'
                    try:
                        if 'amplitude' not in self.current_mesh.point_data:
                            self.current_mesh.point_data["amplitude"] = Z.ravel()
                    except Exception:
                        pass
                    self.mesh_actor.mapper.SetInputDataObject(mesh)
                    self.mesh_actor.mapper.Update()
            else:
                # Нет текущего меша, создаем новый
                mesh = self.mesh_cache.get_mesh(
                    t0, t1, self.freq_max, amp,
                    self._create_mesh_callback
                )
                self.current_mesh = mesh
                self._last_mesh_shape = Z.shape
                try:
                    if 'amplitude' not in self.current_mesh.point_data:
                        self.current_mesh.point_data["amplitude"] = Z.ravel()
                except Exception:
                    pass
                self.mesh_actor.mapper.SetInputDataObject(mesh)
                self.mesh_actor.mapper.Update()
            
            # Обновляем частотные подписи
            self.add_freq_labels(self.current_mesh)
            
            time_start = self.audio_processor.times[t0] if t0 < len(self.audio_processor.times) else 0
            time_end = self.audio_processor.times[t1 - 1] if t1 > 0 and t1 <= len(self.audio_processor.times) else self.audio_processor.times[-1]
            self.plotter_label.setText(
                f"Визуализация (сегмент {time_start:.2f} - {time_end:.2f} сек) | Частота: 0 - {actual_freq_khz:.1f} кГц"
            )
            
            # Сохраняем временной диапазон для меток
            self._last_time_range = (t0, t1)
            
            self.plotter.render()
            self._frame_counter += 1
            
        except Exception as e:
            print("Ошибка обновления визуализации:", e)
            traceback.print_exc()
    
    def play_audio(self):
        """Начинает воспроизведение."""
        if self.audio_processor.spectrogram_data is None:
            return
        # Если визуализация ещё не построена — построим
        if self.mesh_actor is None or self._needs_mesh_rebuild:
            self.init_mesh_static()
        self.media_controller.play()
        self.sync_timer.start(16)
        self.control_panel.pause_btn.setEnabled(True)
        self.control_panel.stop_btn.setEnabled(True)
        self.control_panel.play_btn.setEnabled(False)
        # Блокируем слайдеры и кнопку загрузки во время воспроизведения
        self._set_controls_enabled(False)
        self._set_stft_controls_enabled(False)
    
    def pause_audio(self):
        """Приостанавливает воспроизведение."""
        self.media_controller.pause()
        self.sync_timer.stop()
        self.control_panel.play_btn.setEnabled(True)
        # На паузе параметры остаются заблокированными до полного останова
        self._set_controls_enabled(False)
        self._set_stft_controls_enabled(False)
    
    def stop_audio(self):
        """Останавливает воспроизведение."""
        self.media_controller.stop()
        self.sync_timer.stop()
        self.control_panel.play_btn.setEnabled(True)
        self.control_panel.pause_btn.setEnabled(False)
        self.control_panel.stop_btn.setEnabled(False)
        self.timeline_widget.set_position(0)
        duration = getattr(self.timeline_widget, '_duration', 0)
        self.timeline_widget.update_time_label(0, duration if duration else 0)
        self.last_start_frame = -1
        # Полностью очищаем визуализацию
        self._clear_visualization()
        try:
            self.plotter.render()
        except Exception:
            pass
        # Разблокируем контролы
        self._set_controls_enabled(True)
        self._set_stft_controls_enabled(True)
    
    def seek_audio(self, position_ms):
        """Перематывает аудио на указанную позицию."""
        self.media_controller.seek(position_ms)
    
    def _set_controls_enabled(self, enabled):
        """Блокирует/разблокирует слайдеры частоты, усиления и кнопку загрузки.
        
        Args:
            enabled: True для разблокировки, False для блокировки
        """
        self.control_panel.freq_slider.setEnabled(enabled)
        self.control_panel.amp_slider.setEnabled(enabled)
        self.control_panel.button.setEnabled(enabled)
        self.control_panel.window_size_slider.setEnabled(enabled)
        # Параметры визуализации
        try:
            self.control_panel.colormap_combo.setEnabled(enabled)
            self.control_panel.range_checkbox.setEnabled(enabled)
            self.control_panel.min_db_spinbox.setEnabled(enabled and self.control_panel.range_checkbox.isChecked())
            self.control_panel.max_db_spinbox.setEnabled(enabled and self.control_panel.range_checkbox.isChecked())
        except Exception:
            pass

    def _set_stft_controls_enabled(self, enabled):
        """Включает/выключает панель STFT настроек."""
        try:
            self.stft_settings_panel.setEnabled(enabled)
            if hasattr(self.control_panel, 'stft_group'):
                self.control_panel.stft_group.toggle_btn.setEnabled(enabled)
        except Exception:
            pass
    
    def _request_mesh_rebuild(self):
        """Запрашивает перестроение меша при следующем воспроизведении или сразу, если оно активное."""
        if self.audio_processor.spectrogram_data is None:
            return
        self._needs_mesh_rebuild = True
        if self.media_controller.get_state() == QMediaPlayer.PlayingState:
            self.init_mesh_static()
    
    def _clear_visualization(self):
        """Полностью удаляет текущую визуализацию."""
        try:
            self.remove_freq_labels()
            if self.mesh_actor is not None:
                self.plotter.remove_actor(self.mesh_actor)
                self.mesh_actor = None
            if self.ai_path_actor is not None:
                self.plotter.remove_actor(self.ai_path_actor)
                self.ai_path_actor = None
            if self.current_mesh is not None:
                self.current_mesh.Clear()
                self.current_mesh = None
        except Exception:
            pass
        self._last_mesh_shape = None
        self._needs_mesh_rebuild = True
    
    def update_stats_label(self):
        """Обновляет статусную строку с FPS и статистикой."""
        if not hasattr(self, 'status_label') or self.status_label is None:
            return
        now = time.time()
        if self._last_stats_time is None:
            self._last_stats_time = now
        elapsed = max(now - self._last_stats_time, 1e-6)
        fps = self._frame_counter / elapsed
        self._frame_counter = 0
        self._last_stats_time = now
        points = int(self.current_mesh.n_points) if self.current_mesh is not None else 0
        faces = int(self.current_mesh.n_cells) if self.current_mesh is not None else 0
        cache_stats = self.mesh_cache.get_stats()
        cache_size = cache_stats['size']
        cache_max = cache_stats['max_size']
        cache_text = f"{cache_size}/{cache_max}"
        
        # Показываем hit rate только если есть статистика
        total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
        if total_requests > 0:
            hit_rate = cache_stats.get('hit_rate', 0.0)
            self.status_label.setText(
                f"FPS: {fps:.1f} | Вершин: {points} | Граней: {faces} | Кэш: {cache_text} (hit: {hit_rate:.0f}%)"
            )
        else:
            # Если нет запросов, показываем только размер
            self.status_label.setText(
                f"FPS: {fps:.1f} | Вершин: {points} | Граней: {faces} | Кэш: {cache_text}"
            )
    
    def update_position(self, ms):
        """Обновляет позицию воспроизведения."""
        duration = self.media_controller.get_duration()
        if duration and duration > 0:
            self.timeline_widget.set_position(ms)
            self.timeline_widget.update_time_label(ms, duration)
        else:
            if self.audio_processor.audio_data is not None:
                total_ms = int((len(self.audio_processor.audio_data) / self.audio_processor.sample_rate) * 1000)
                self.timeline_widget.update_time_label(ms, total_ms)
    
    def on_media_state_changed(self, state):
        """Обработчик изменения состояния медиаплеера."""
        if state == QMediaPlayer.StoppedState:
            self.sync_timer.stop()
            self.control_panel.play_btn.setEnabled(True)
            self.control_panel.pause_btn.setEnabled(False)
            self.control_panel.stop_btn.setEnabled(False)
            # Разблокируем слайдеры и кнопку загрузки после остановки
            self._set_controls_enabled(True)
            self._set_stft_controls_enabled(True)
    
    def show_full_spectrogram(self):
        """Показывает полную спектрограмму в отдельном окне."""
        if self.audio_processor.spectrogram_data is None:
            return
        
        try:
            # Создаем улучшенное окно полной спектрограммы
            self.full_spectrogram_window = FullSpectrogramWindow(
                self.audio_processor.spectrogram_data,
                self.audio_processor.freqs,
                self.audio_processor.times,
                self.audio_processor,
                self.mesh_generator,
                self.visualization_settings,
                self.freq_max,
                self.control_panel,
                self
            )
            
            # Подключаем сигнал выбора сегмента
            self.full_spectrogram_window.segment_selected.connect(self.on_segment_selected)
            
            # Подключаем сигналы изменений настроек для обновления полной спектрограммы
            self.control_panel.freq_slider.valueChanged.connect(self._update_full_spectrogram)
            self.control_panel.amp_slider.valueChanged.connect(self._update_full_spectrogram)
            self.control_panel.colormap_combo.currentTextChanged.connect(self._update_full_spectrogram)
            self.control_panel.range_checkbox.toggled.connect(self._update_full_spectrogram)
            self.control_panel.min_db_spinbox.valueChanged.connect(self._update_full_spectrogram)
            self.control_panel.max_db_spinbox.valueChanged.connect(self._update_full_spectrogram)
            
            self.full_spectrogram_window.show()
            
        except Exception as e:
            print("Ошибка полной спектрограммы:", e)
            traceback.print_exc()
    
    def show_help(self):
        """Открывает окно подсказок."""
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(self)
        self._help_dialog.show()
        self._help_dialog.raise_()
        self._help_dialog.activateWindow()
    
    def _update_full_spectrogram(self):
        """Обновляет визуализацию полной спектрограммы при изменении настроек."""
        if hasattr(self, 'full_spectrogram_window') and self.full_spectrogram_window is not None:
            if self.full_spectrogram_window.isVisible():
                # Используем таймер для дебаунса обновлений
                if not hasattr(self, '_full_spectrogram_update_timer'):
                    self._full_spectrogram_update_timer = QTimer()
                    self._full_spectrogram_update_timer.setSingleShot(True)
                    self._full_spectrogram_update_timer.timeout.connect(self._apply_full_spectrogram_update)
                
                self._full_spectrogram_update_timer.stop()
                self._full_spectrogram_update_timer.start(300)  # Дебаунс 300мс
    
    def _apply_full_spectrogram_update(self):
        """Применяет обновление полной спектрограммы после дебаунса."""
        if hasattr(self, 'full_spectrogram_window') and self.full_spectrogram_window is not None:
            if self.full_spectrogram_window.isVisible():
                # Проверяем, есть ли выбранный сегмент
                if (hasattr(self.full_spectrogram_window, 'selected_t0') and 
                    hasattr(self.full_spectrogram_window, 'selected_t1')):
                    t0 = self.full_spectrogram_window.selected_t0
                    t1 = self.full_spectrogram_window.selected_t1
                    # Обновляем только если сегмент был выбран (не полная спектрограмма)
                    if t0 > 0 or t1 < self.audio_processor.spectrogram_data.shape[0]:
                        self.full_spectrogram_window.update_mesh_for_segment(t0, t1)
                    else:
                        # Обновляем полную спектрограмму
                        self.full_spectrogram_window.create_full_mesh()
                else:
                    # Обновляем полную спектрограмму
                    self.full_spectrogram_window.create_full_mesh()
    
    def on_segment_selected(self, t0, t1):
        """Обработчик выбора сегмента из полной спектрограммы.
        
        Args:
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра
        """
        # Вычисляем время начала сегмента для перемотки
        start_time = self.audio_processor.times[t0] if t0 < len(self.audio_processor.times) else 0
        start_time_ms = int(start_time * 1000)
        
        # Перематываем аудио на начало сегмента
        self.media_controller.seek(start_time_ms)
        self.timeline_widget.set_position(start_time_ms)
        
        # Обновляем размер окна только если он отличается
        new_window_size = t1 - t0
        if new_window_size != self.window_size:
            self.window_size = new_window_size
            # Обновляем слайдер только если значение в допустимом диапазоне
            if (self.control_panel.window_size_slider.minimum() <= self.window_size <= 
                self.control_panel.window_size_slider.maximum()):
                self.control_panel.window_size_slider.setValue(self.window_size)
            self.control_panel.window_size_label.setText(str(self.window_size))
        
        # Обновляем меш
        self.last_start_frame = t0
        self.mesh_cache.clear()
        self._last_mesh_shape = None
        self._request_mesh_rebuild()
    
    def on_stft_recalculate(self, settings):
        """Обработчик запроса пересчета спектрограммы с новыми параметрами STFT.
        
        Args:
            settings: Словарь с настройками STFT
        """
        if self.audio_processor.audio_data is None:
            return
        
        try:
            # Показываем прогресс
            self.stft_settings_panel.show_progress(True)
            self.stft_settings_panel.set_progress(10)
            QtWidgets.QApplication.processEvents()
            
            # Проверяем, не воспроизводится ли трек
            if self.media_controller.get_state() == QMediaPlayer.PlayingState:
                reply = QMessageBox.question(
                    self, "Воспроизведение активно",
                    "Трек воспроизводится. Пересчет спектрограммы остановит воспроизведение. Продолжить?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    self.stft_settings_panel.show_progress(False)
                    return
                self.media_controller.stop()
                self.sync_timer.stop()
            
            self.stft_settings_panel.set_progress(30)
            QtWidgets.QApplication.processEvents()
            
            # Пересчитываем спектрограмму
            self.audio_processor.compute_spectrogram(
                audio_data=self.audio_processor.audio_data,
                sample_rate=self.audio_processor.sample_rate,
                n_fft=settings['n_fft'],
                hop_length=settings['hop_length'],
                window=settings['window_type']
            )
            self.n_fft = settings['n_fft']
            self.hop_length = settings['hop_length']
            self.window_type = settings['window_type']
            self.stft_settings_panel.set_sample_rate(self.audio_processor.sample_rate)
            
            self.stft_settings_panel.set_progress(70)
            QtWidgets.QApplication.processEvents()
            
            # Обновляем глобальный диапазон
            self.visualization_settings.set_global_db_range(
                self.audio_processor.db_min,
                self.audio_processor.db_max
            )
            
            # Обновляем значения в spinbox
            self.control_panel.min_db_spinbox.setValue(self.audio_processor.db_min)
            self.control_panel.max_db_spinbox.setValue(self.audio_processor.db_max)
            
            self.stft_settings_panel.set_progress(90)
            QtWidgets.QApplication.processEvents()
            
            # Синхронизируем размер окна с актуальным числом кадров
            max_frames = self.audio_processor.spectrogram_data.shape[0] if self.audio_processor.spectrogram_data is not None else 0
            if max_frames and self.window_size > max_frames:
                self.window_size = max_frames
                if max_frames >= self.control_panel.window_size_slider.minimum():
                    self.control_panel.window_size_slider.setValue(self.window_size)
                self.control_panel.window_size_label.setText(str(self.window_size))
            
            # Очищаем кэш и обновляем меш
            self._clear_visualization()
            self.mesh_cache.clear()
            self.last_start_frame = -1
            self._request_mesh_rebuild()
            
            self.stft_settings_panel.set_progress(100)
            QtWidgets.QApplication.processEvents()
            
            # Обновляем информацию в панели STFT
            self.stft_settings_panel.update_info_with_sample_rate(self.audio_processor.sample_rate)
            self.last_freq_max_cached = None
            
            # Скрываем прогресс
            QTimer.singleShot(500, lambda: self.stft_settings_panel.show_progress(False))
            
            # Обновляем информацию в UI
            info = self.audio_processor.get_audio_info()
            if info:
                duration_ms = int(info['duration'] * 1000)
                self.timeline_widget.set_duration(duration_ms)
                self.control_panel.info_label.setText(
                    f"✓ {info['filename']}\n"
                    f"Длительность: {info['duration']:.1f} сек\n"
                    f"Sample rate: {info['sample_rate']} Гц\n"
                    f"N_fft: {info['n_fft']}\n"
                    f"Кадров: {info['frames']}\n"
                    f"Частот: {info['frequencies']}\n\n"
                    f"Диапазон амплитуды: {info['db_min']:.1f} - {info['db_max']:.1f} дБ"
                )
            
        except Exception as e:
            self.stft_settings_panel.show_progress(False)
            QMessageBox.critical(
                self, "Ошибка пересчета",
                f"Ошибка при пересчете спектрограммы:\n{str(e)}"
            )
            traceback.print_exc()
    
    def export_mesh(self):
        """Экспортирует полную спектрограмму в файл."""
        if self.audio_processor.spectrogram_data is None:
            QMessageBox.warning(self, "Нет данных", "Сначала загрузите аудиофайл.")
            return
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Экспорт меша", "", "VTK (*.vtk);;OBJ (*.obj);;STL (*.stl)"
        )
        if not file_path:
            return
        
        # Определяем формат из расширения
        if file_path.endswith('.obj'):
            format_type = 'obj'
        elif file_path.endswith('.stl'):
            format_type = 'stl'
        else:
            format_type = 'vtk'
        
        try:
            # Показываем прогресс
            self.control_panel.label.setText("Создание меша полной спектрограммы...")
            QtWidgets.QApplication.processEvents()
            
            # Создаем меш полной спектрограммы
            amp = self.control_panel.amp_slider.value() / 10.0
            t0 = 0
            t1 = self.audio_processor.spectrogram_data.shape[0]
            
            # Для экспорта используем полную спектрограмму без downsampling
            # (или с минимальным downsampling для очень больших файлов)
            full_mesh, _ = self.mesh_generator.create_mesh(
                self.audio_processor.spectrogram_data,
                t0, t1,
                self.freq_max,
                amp,
                self.audio_processor.freqs,
                z_min=self.audio_processor.db_min,
                z_max=self.audio_processor.db_max,
                use_global_normalization=True
            )
            
            # Добавляем скаляры амплитуды
            Z_full, _ = self.audio_processor.get_spectrogram_segment(t0, t1, self.freq_max)
            if Z_full is not None and Z_full.size > 0:
                full_mesh.point_data["amplitude"] = Z_full.ravel()
            
            self.control_panel.label.setText("Экспорт меша...")
            QtWidgets.QApplication.processEvents()
            
            # Экспортируем полный меш
            success = self.mesh_generator.export_mesh(full_mesh, file_path, format_type)
            
            if success:
                self.control_panel.label.setText(f"✓ Полная спектрограмма экспортирована: {os.path.basename(file_path)}")
            else:
                self.control_panel.label.setText("✗ Ошибка экспорта меша")
            
            # Очищаем временный меш
            try:
                full_mesh.Clear()
            except Exception:
                pass
                
        except Exception as e:
            self.control_panel.label.setText(f"✗ Ошибка: {str(e)[:50]}")
            QMessageBox.critical(self, "Ошибка экспорта", f"Ошибка при экспорте меша:\n{str(e)}")
            traceback.print_exc()
    
    def setup_hotkeys(self):
        """Настраивает горячие клавиши."""
        # Space: Play/Pause
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play_pause)
        
        # Ctrl+S: Стоп
        QShortcut(QKeySequence("Ctrl+S"), self, self.stop_audio)
        
        # Ctrl+O: Открыть файл
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_audio)
        
        # 1-4: Пресеты камеры
        QShortcut(QKeySequence("1"), self, lambda: self.apply_camera_preset('iso'))
        QShortcut(QKeySequence("2"), self, lambda: self.apply_camera_preset('top'))
        QShortcut(QKeySequence("3"), self, lambda: self.apply_camera_preset('side'))
        QShortcut(QKeySequence("4"), self, lambda: self.apply_camera_preset('front'))
    
    def toggle_play_pause(self):
        """Переключает воспроизведение/паузу."""
        if self.media_controller.get_state() == QMediaPlayer.PlayingState:
            self.pause_audio()
        else:
            self.play_audio()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        try:
            self._stats_timer.stop()
        except Exception:
            pass
        # Сохраняем позицию камеры
        if self.plotter.camera_position is not None:
            self.config_manager.save_camera_position(self.plotter.camera_position)
        
        # Очищаем ресурсы
        self.mesh_cache.clear()
        self.media_controller.cleanup()
        
        if self.current_mesh:
            try:
                self.current_mesh.Clear()
            except Exception:
                pass
        
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Устанавливаем иконку приложения для всего приложения
    icon_path = os.path.join(os.path.dirname(__file__), 'photo_2025-03-04_00-35-20.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    w = AudioMeshVisualizer()
    w.show()
    sys.exit(app.exec_())
