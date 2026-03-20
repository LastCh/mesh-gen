"""Утилитарные функции для работы с аудио и временем."""

import numpy as np


def format_time(ms):
    """Форматирует время в миллисекундах в формат MM:SS.
    
    Args:
        ms: Время в миллисекундах
        
    Returns:
        Строка в формате "MM:SS"
    """
    seconds = int(ms / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def calculate_frame_index(position_ms, sample_rate, hop_length):
    """Вычисляет индекс кадра спектрограммы по позиции в миллисекундах.
    
    Args:
        position_ms: Позиция в миллисекундах
        sample_rate: Частота дискретизации аудио
        hop_length: Длина hop для STFT
        
    Returns:
        Индекс кадра
    """
    return int((position_ms / 1000) / (hop_length / sample_rate))


def normalize_spectrogram(Z, z_min=None, z_max=None):
    """Нормализует спектрограмму в диапазон [0, 1].
    
    Args:
        Z: Массив спектрограммы
        z_min: Минимальное значение (если None, вычисляется)
        z_max: Максимальное значение (если None, вычисляется)
        
    Returns:
        Нормализованный массив и (z_min, z_max)
    """
    if z_min is None:
        z_min = Z.min()
    if z_max is None:
        z_max = Z.max()
    
    if abs(z_max - z_min) < 1e-9:
        return np.ones_like(Z), z_min, z_max
    
    Z_norm = (Z - z_min) / (z_max - z_min + 1e-9)
    return Z_norm, z_min, z_max

