"""Настройки визуализации: цветовые карты, диапазоны амплитуд."""

import numpy as np
import pyvista as pv


class VisualizationSettings:
    """Класс для управления настройками визуализации."""
    
    # Доступные цветовые карты
    COLORMAPS = [
        'viridis', 'plasma', 'inferno', 'magma', 'turbo', 'spectral',
        'coolwarm', 'rainbow', 'jet', 'hot', 'cool', 'spring', 'summer',
        'autumn', 'winter', 'gray', 'bone', 'copper', 'pink'
    ]
    
    def __init__(self):
        """Инициализация настроек визуализации."""
        self.colormap = 'viridis'
        self.db_min = None  # Глобальное минимальное значение dB
        self.db_max = None  # Глобальное максимальное значение dB
        self.db_range_min = None  # Настройка диапазона для цветов (min)
        self.db_range_max = None  # Настройка диапазона для цветов (max)
        self.use_custom_range = False  # Использовать пользовательский диапазон
    
    def set_global_db_range(self, db_min, db_max):
        """Устанавливает глобальный диапазон dB.
        
        Args:
            db_min: Минимальное значение dB
            db_max: Максимальное значение dB
        """
        self.db_min = db_min
        self.db_max = db_max
        # По умолчанию используем весь диапазон
        if self.db_range_min is None:
            self.db_range_min = db_min
        if self.db_range_max is None:
            self.db_range_max = db_max
    
    def set_colormap(self, colormap):
        """Устанавливает цветовую карту.
        
        Args:
            colormap: Имя цветовой карты (должно быть в COLORMAPS)
        """
        if colormap in self.COLORMAPS:
            self.colormap = colormap
        else:
            print(f"Предупреждение: неизвестная цветовая карта {colormap}, используется viridis")
            self.colormap = 'viridis'
    
    def set_custom_range(self, db_min, db_max):
        """Устанавливает пользовательский диапазон для цветов.
        
        Args:
            db_min: Минимальное значение dB для цветов
            db_max: Максимальное значение dB для цветов
        """
        self.db_range_min = db_min
        self.db_range_max = db_max
        self.use_custom_range = True
    
    def reset_range(self):
        """Сбрасывает диапазон к глобальному."""
        if self.db_min is not None and self.db_max is not None:
            self.db_range_min = self.db_min
            self.db_range_max = self.db_max
        self.use_custom_range = False
    
    def get_active_range(self):
        """Возвращает активный диапазон для визуализации.
        
        Returns:
            Кортеж (min_db, max_db)
        """
        if self.use_custom_range and self.db_range_min is not None and self.db_range_max is not None:
            return self.db_range_min, self.db_range_max
        elif self.db_min is not None and self.db_max is not None:
            return self.db_min, self.db_max
        else:
            return None, None
    
    def add_colorbar(self, plotter, mesh, label="Amplitude (dB)"):
        """Добавляет colorbar к plotter.
        
        Args:
            plotter: PyVista Plotter
            mesh: PyVista PolyData меш
            label: Подпись colorbar
        """
        try:
            # Получаем активный диапазон
            min_db, max_db = self.get_active_range()
            if min_db is None or max_db is None:
                return
            
            # Создаем colorbar
            plotter.add_scalar_bar(
                title=label,
                n_labels=5,
                title_font_size=12,
                label_font_size=10,
                fmt='%.1f',
                n_colors=256,
                color='black'
            )
            
            # Обновляем диапазон mapper
            if hasattr(plotter, 'actors') and len(plotter.actors) > 0:
                for actor in plotter.actors:
                    if hasattr(actor, 'mapper') and hasattr(actor.mapper, 'SetScalarRange'):
                        actor.mapper.SetScalarRange(min_db, max_db)
        except Exception as e:
            print(f"Ошибка добавления colorbar: {e}")

