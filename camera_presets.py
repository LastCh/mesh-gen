"""Пресеты камеры для 3D визуализации."""

import numpy as np


class CameraPresets:
    """Класс для управления пресетами камеры."""
    
    def __init__(self):
        """Инициализация пресетов камеры."""
        self.presets = {
            'iso': self._get_iso_preset(),
            'top': self._get_top_preset(),
            'side': self._get_side_preset(),
            'front': self._get_front_preset(),
        }
    
    def _get_iso_preset(self):
        """Возвращает изометрический пресет камеры."""
        # Изометрический вид: равные углы по всем осям
        position = [10, 10, 10]
        focal_point = [0, 0, 0]
        view_up = [0, 0, 1]
        return {
            'position': position,
            'focal_point': focal_point,
            'view_up': view_up
        }
    
    def _get_top_preset(self):
        """Возвращает пресет камеры сверху."""
        # Вид сверху: камера высоко по Z, смотрит вниз
        position = [0, 0, 20]
        focal_point = [0, 0, 0]
        view_up = [0, 1, 0]
        return {
            'position': position,
            'focal_point': focal_point,
            'view_up': view_up
        }
    
    def _get_side_preset(self):
        """Возвращает пресет камеры сбоку."""
        # Вид сбоку: камера справа по X, смотрит на центр
        position = [15, 0, 5]
        focal_point = [0, 0, 0]
        view_up = [0, 0, 1]
        return {
            'position': position,
            'focal_point': focal_point,
            'view_up': view_up
        }
    
    def _get_front_preset(self):
        """Возвращает пресет камеры спереди."""
        # Вид спереди: камера спереди по Y, смотрит на центр
        position = [0, 15, 5]
        focal_point = [0, 0, 0]
        view_up = [0, 0, 1]
        return {
            'position': position,
            'focal_point': focal_point,
            'view_up': view_up
        }
    
    def get_preset(self, name):
        """Возвращает пресет камеры по имени.
        
        Args:
            name: Имя пресета ('iso', 'top', 'side', 'front')
            
        Returns:
            Словарь с параметрами камеры или None если пресет не найден
        """
        return self.presets.get(name)
    
    def apply_to_plotter(self, plotter, preset_name, bounds=None):
        """Применяет пресет камеры к plotter.
        
        Args:
            plotter: PyVista Plotter
            preset_name: Имя пресета ('iso', 'top', 'side', 'front')
            bounds: Границы сцены (xmin, xmax, ymin, ymax, zmin, zmax)
        """
        base_preset = self.get_preset(preset_name)
        preset = self._fit_to_bounds(base_preset, bounds, preset_name)
        if preset is None:
            print(f"Предупреждение: пресет {preset_name} не найден")
            return
        
        try:
            plotter.camera.position = preset['position']
            plotter.camera.focal_point = preset['focal_point']
            plotter.camera.up = preset['view_up']
            plotter.camera.reset_clipping_range()
            plotter.render()
        except Exception as e:
            print(f"Ошибка применения пресета камеры: {e}")
    
    def save_custom_preset(self, plotter, name):
        """Сохраняет текущую позицию камеры как пользовательский пресет.
        
        Args:
            plotter: PyVista Plotter
            name: Имя для сохранения пресета
        """
        try:
            self.presets[name] = {
                'position': list(plotter.camera.position),
                'focal_point': list(plotter.camera.focal_point),
                'view_up': list(plotter.camera.up)
            }
        except Exception as e:
            print(f"Ошибка сохранения пресета камеры: {e}")
    
    def get_current_camera(self, plotter):
        """Возвращает текущую позицию камеры.
        
        Args:
            plotter: PyVista Plotter
            
        Returns:
            Словарь с параметрами камеры или None
        """
        try:
            return {
                'position': list(plotter.camera.position),
                'focal_point': list(plotter.camera.focal_point),
                'view_up': list(plotter.camera.up)
            }
        except Exception:
            return None

    def _fit_to_bounds(self, preset, bounds, preset_name):
        """Подгоняет параметры камеры под границы сцены."""
        if preset is None:
            return None
        target = {
            'position': list(preset['position']),
            'focal_point': list(preset['focal_point']),
            'view_up': list(preset['view_up'])
        }
        if not bounds:
            return target
        
        xmin, xmax, ymin, ymax, zmin, zmax = bounds
        center = np.array([
            (xmin + xmax) / 2.0,
            (ymin + ymax) / 2.0,
            (zmin + zmax) / 2.0
        ], dtype=float)
        span = np.array([
            max(xmax - xmin, 1e-3),
            max(ymax - ymin, 1e-3),
            max(zmax - zmin, 1e-3)
        ], dtype=float)
        max_dim = max(span.max(), 1.0)
        
        base_position = np.array(preset['position'], dtype=float)
        base_focal = np.array(preset['focal_point'], dtype=float)
        direction = base_position - base_focal
        if np.linalg.norm(direction) < 1e-6:
            direction = np.array([0.0, 0.0, 1.0])
        direction = direction / np.linalg.norm(direction)
        
        padding = 1.6
        if preset_name == 'iso':
            padding = 1.8
        elif preset_name in ('top', 'side', 'front'):
            padding = 2.0
        
        distance = max_dim * padding
        new_position = center + direction * distance
        
        target['position'] = new_position.tolist()
        target['focal_point'] = center.tolist()
        return target

