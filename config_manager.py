"""Управление конфигурацией приложения."""

import os
import json
from pathlib import Path


class ConfigManager:
    """Класс для работы с конфигурацией приложения."""
    
    def __init__(self, config_name="audiomesh"):
        """Инициализация менеджера конфигурации.
        
        Args:
            config_name: Имя приложения для создания директории конфига
        """
        self.config_name = config_name
        self.config_dir = Path.home() / f".{config_name}"
        self.config_file = self.config_dir / "config.json"
        
        # Создаем директорию если её нет
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self):
        """Загружает конфигурацию из файла.
        
        Returns:
            Словарь с конфигурацией или пустой словарь
        """
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")
            return {}
    
    def save_config(self, config):
        """Сохраняет конфигурацию в файл.
        
        Args:
            config: Словарь с конфигурацией
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")
    
    def get_camera_position(self):
        """Возвращает сохраненную позицию камеры.
        
        Returns:
            Позиция камеры или None
        """
        config = self.load_config()
        return config.get("camera_position")
    
    def save_camera_position(self, camera_position):
        """Сохраняет позицию камеры.
        
        Args:
            camera_position: Позиция камеры (список или кортеж)
        """
        config = self.load_config()
        config["camera_position"] = list(camera_position) if camera_position is not None else None
        self.save_config(config)
    
    def get_default_volume(self):
        """Возвращает сохраненную громкость по умолчанию.
        
        Returns:
            Громкость (0-100) или None
        """
        config = self.load_config()
        return config.get("default_volume")
    
    def save_default_volume(self, volume):
        """Сохраняет громкость по умолчанию.
        
        Args:
            volume: Громкость от 0 до 100
        """
        config = self.load_config()
        config["default_volume"] = volume
        self.save_config(config)

