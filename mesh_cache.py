"""Кэширование мешей для оптимизации производительности."""

import gc
import pyvista as pv
from collections import OrderedDict


class MeshCache:
    """LRU кэш для мешей с ограничением по памяти."""
    
    def __init__(self, max_size=10):
        """Инициализация кэша.
        
        Args:
            max_size: Максимальное количество мешей в кэше
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, t0, t1, freq_max, amp):
        """Создает ключ для кэша.
        
        Args:
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра
            freq_max: Максимальная частота
            amp: Коэффициент усиления
            
        Returns:
            Кортеж-ключ
        """
        return (t0, t1, int(freq_max), int(amp * 10))  # int для избежания проблем с float
    
    def get_mesh(self, t0, t1, freq_max, amp, generator_func):
        """Получает меш из кэша или создает новый.
        
        Args:
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра
            freq_max: Максимальная частота
            amp: Коэффициент усиления
            generator_func: Функция для создания меша, если его нет в кэше
                           Должна принимать (t0, t1, freq_max, amp) и возвращать mesh
            
        Returns:
            PyVista PolyData меш
        """
        key = self._make_key(t0, t1, freq_max, amp)
        
        if key in self.cache:
            # Перемещаем в конец (самый недавно использованный)
            mesh = self.cache.pop(key)
            self.cache[key] = mesh
            self.hits += 1
            # Возвращаем копию, чтобы не менять оригинал
            return mesh.copy()
        else:
            # Создаем новый меш
            mesh = generator_func(t0, t1, freq_max, amp)
            self.cache[key] = mesh
            
            # Удаляем старые меши если превышен лимит
            if len(self.cache) > self.max_size:
                self._evict_oldest()
            
            self.misses += 1
            return mesh
    
    def _evict_oldest(self):
        """Удаляет самый старый меш из кэша."""
        if len(self.cache) == 0:
            return
        
        # Удаляем первый элемент (самый старый)
        key, mesh = self.cache.popitem(last=False)
        
        # Очищаем память
        self._cleanup_mesh(mesh)
    
    def _cleanup_mesh(self, mesh):
        """Очищает память, занимаемую мешем.
        
        Args:
            mesh: PyVista PolyData меш
        """
        try:
            if mesh is not None:
                mesh.Clear()
        except Exception:
            pass
    
    def clear(self):
        """Очищает весь кэш."""
        for mesh in self.cache.values():
            self._cleanup_mesh(mesh)
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        gc.collect()
    
    def cleanup_old(self, keep_count=5):
        """Очищает старые меши, оставляя только последние N.
        
        Args:
            keep_count: Количество мешей для сохранения
        """
        while len(self.cache) > keep_count:
            self._evict_oldest()
        gc.collect()
    
    def invalidate(self, t0=None, t1=None, freq_max=None, amp=None):
        """Удаляет меши из кэша по критериям.
        
        Args:
            t0: Удалить меши с этим t0 (если None, игнорируется)
            t1: Удалить меши с этим t1 (если None, игнорируется)
            freq_max: Удалить меши с этим freq_max (если None, игнорируется)
            amp: Удалить меши с этим amp (если None, игнорируется)
        """
        keys_to_remove = []
        
        for key in self.cache.keys():
            k_t0, k_t1, k_freq_max, k_amp = key
            
            match = True
            if t0 is not None and k_t0 != t0:
                match = False
            if t1 is not None and k_t1 != t1:
                match = False
            if freq_max is not None and k_freq_max != int(freq_max):
                match = False
            if amp is not None and k_amp != int(amp * 10):
                match = False
            
            if match:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            mesh = self.cache.pop(key)
            self._cleanup_mesh(mesh)
        
        gc.collect()
    
    def get_stats(self):
        """Возвращает статистику кэша.
        
        Returns:
            Словарь с статистикой
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }

