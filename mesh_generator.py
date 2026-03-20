"""Генерация 3D мешей из спектрограммы."""

import numpy as np
import pyvista as pv
from utils import normalize_spectrogram


class MeshGenerator:
    """Класс для генерации 3D мешей из спектрограммы."""
    
    def __init__(self):
        """Инициализация генератора мешей."""
        self._cached_mesh_structure = None  # Кэш структуры меша (points, faces без Z)
    
    def create_mesh(self, spectrogram_data, t0, t1, freq_max, amp, freqs, 
                    z_min=None, z_max=None, use_global_normalization=True):
        """Создает 3D меш из сегмента спектрограммы.
        
        Args:
            spectrogram_data: Полная спектрограмма (кадры x частоты)
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра (не включительно)
            freq_max: Максимальная частота в Гц
            amp: Коэффициент усиления для Z координат
            freqs: Массив частот
            z_min: Глобальное минимальное значение dB (для глобальной нормализации)
            z_max: Глобальное максимальное значение dB (для глобальной нормализации)
            use_global_normalization: Использовать глобальную нормализацию (True) или локальную (False)
            
        Returns:
            Кортеж (mesh, actual_freq_khz) где mesh - PyVista PolyData,
            actual_freq_khz - фактическая максимальная частота в кГц
        """
        Z = spectrogram_data[t0:t1, :]
        idx_freq = np.searchsorted(freqs, freq_max)
        Z = Z[:, :max(1, idx_freq)]
        
        if Z.size == 0:
            points = np.array([[0, 0, 0]])
            faces = np.array([3, 0, 0, 0], dtype=np.int32)
            mesh = pv.PolyData(points, faces)
            return mesh, 0.0
        
        # Нормализуем и усиливаем
        if use_global_normalization and z_min is not None and z_max is not None:
            # Используем глобальные значения для корректного отображения
            Z_norm, _, _ = normalize_spectrogram(Z, z_min=z_min, z_max=z_max)
        else:
            # Локальная нормализация (для сравнения)
            Z_norm, _, _ = normalize_spectrogram(Z)
        Z_amplified = Z_norm * amp
        
        # Создаем координатную сетку
        Tn, Fn = Z.shape
        x = np.arange(Tn)
        y = np.arange(Fn)
        xx, yy = np.meshgrid(x, y, indexing='ij')
        
        # Создаем точки
        points = np.c_[xx.ravel(), yy.ravel(), Z_amplified.ravel()]
        
        # Создаем грани
        faces = self._create_faces(Tn, Fn)
        
        mesh = pv.PolyData(points, faces)
        mesh.point_data["amplitude"] = Z.ravel()
        # Сохраняем форму сетки для downstream-логики (навигация и т.п.)
        mesh.field_data["grid_shape"] = np.array([Tn, Fn], dtype=np.int32)
        
        actual_freq_khz = freqs[idx_freq - 1] / 1000 if idx_freq > 0 else 0
        
        # Кэшируем структуру меша (без Z координат)
        self._cached_mesh_structure = {
            "Tn": Tn,
            "Fn": Fn,
            "faces": faces,
            "xx": xx,
            "yy": yy
        }
        
        return mesh, actual_freq_khz
    
    def update_mesh_vertices(self, mesh, new_Z_values, amp, z_min=None, z_max=None, 
                            use_global_normalization=True):
        """Обновляет только Z координаты вершин существующего меша.
        
        Args:
            mesh: PyVista PolyData меш
            new_Z_values: Новые значения спектрограммы (2D массив)
            amp: Коэффициент усиления
            z_min: Глобальное минимальное значение dB (для глобальной нормализации)
            z_max: Глобальное максимальное значение dB (для глобальной нормализации)
            use_global_normalization: Использовать глобальную нормализацию (True) или локальную (False)
            
        Returns:
            Обновленный меш
        """
        if mesh is None or new_Z_values.size == 0:
            return mesh
        
        # Нормализуем и усиливаем
        if use_global_normalization and z_min is not None and z_max is not None:
            Z_norm, _, _ = normalize_spectrogram(new_Z_values, z_min=z_min, z_max=z_max)
        else:
            Z_norm, _, _ = normalize_spectrogram(new_Z_values)
        Z_amplified = Z_norm * amp
        
        # Обновляем только Z координаты
        mesh.points[:, 2] = Z_amplified.ravel()
        
        # Обновляем амплитуду для цветовой карты
        mesh.point_data["amplitude"] = new_Z_values.ravel()
        
        return mesh
    
    def create_lod_mesh(self, spectrogram_data, t0, t1, freq_max, amp, freqs, lod_factor=2,
                       z_min=None, z_max=None, use_global_normalization=True):
        """Создает упрощенный меш с пониженным разрешением (LOD).
        
        Args:
            spectrogram_data: Полная спектрограмма
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра
            freq_max: Максимальная частота в Гц
            amp: Коэффициент усиления
            freqs: Массив частот
            lod_factor: Фактор уменьшения разрешения (2 = половина точек)
            z_min: Глобальное минимальное значение dB (для глобальной нормализации)
            z_max: Глобальное максимальное значение dB (для глобальной нормализации)
            use_global_normalization: Использовать глобальную нормализацию (True) или локальную (False)
            
        Returns:
            Кортеж (mesh, actual_freq_khz)
        """
        Z = spectrogram_data[t0:t1, :]
        idx_freq = np.searchsorted(freqs, freq_max)
        Z = Z[:, :max(1, idx_freq)]
        
        if Z.size == 0:
            points = np.array([[0, 0, 0]])
            faces = np.array([3, 0, 0, 0], dtype=np.int32)
            mesh = pv.PolyData(points, faces)
            return mesh, 0.0
        
        # Уменьшаем разрешение
        Tn, Fn = Z.shape
        Tn_lod = max(1, Tn // lod_factor)
        Fn_lod = max(1, Fn // lod_factor)
        
        # Децимация (усреднение)
        Z_lod = np.zeros((Tn_lod, Fn_lod))
        for i in range(Tn_lod):
            for j in range(Fn_lod):
                i_start = i * lod_factor
                i_end = min((i + 1) * lod_factor, Tn)
                j_start = j * lod_factor
                j_end = min((j + 1) * lod_factor, Fn)
                Z_lod[i, j] = np.mean(Z[i_start:i_end, j_start:j_end])
        
        # Нормализуем и усиливаем
        if use_global_normalization and z_min is not None and z_max is not None:
            Z_norm, _, _ = normalize_spectrogram(Z_lod, z_min=z_min, z_max=z_max)
        else:
            Z_norm, _, _ = normalize_spectrogram(Z_lod)
        Z_amplified = Z_norm * amp
        
        # Создаем координатную сетку
        x = np.arange(Tn_lod)
        y = np.arange(Fn_lod)
        xx, yy = np.meshgrid(x, y, indexing='ij')
        
        points = np.c_[xx.ravel(), yy.ravel(), Z_amplified.ravel()]
        faces = self._create_faces(Tn_lod, Fn_lod)
        
        mesh = pv.PolyData(points, faces)
        mesh.point_data["amplitude"] = Z_lod.ravel()
        mesh.field_data["grid_shape"] = np.array([Tn_lod, Fn_lod], dtype=np.int32)
        
        actual_freq_khz = freqs[idx_freq - 1] / 1000 if idx_freq > 0 else 0
        
        return mesh, actual_freq_khz
    
    def export_mesh(self, mesh, file_path, format='vtk'):
        """Экспортирует меш в файл.
        
        Args:
            mesh: PyVista PolyData меш
            file_path: Путь к файлу для сохранения
            format: Формат экспорта ('vtk', 'obj', 'stl')
            
        Returns:
            True если успешно, False иначе
        """
        try:
            if format.lower() == 'vtk':
                mesh.save(file_path)
            elif format.lower() == 'obj':
                # PyVista поддерживает OBJ через save
                if not file_path.endswith('.obj'):
                    file_path += '.obj'
                mesh.save(file_path)
            elif format.lower() == 'stl':
                # STL требует триангулированный меш
                if not mesh.is_all_triangles():
                    mesh = mesh.triangulate()
                if not file_path.endswith('.stl'):
                    file_path += '.stl'
                mesh.save(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат: {format}")
            return True
        except Exception as e:
            print(f"Ошибка экспорта меша: {e}")
            return False
    
    def _create_faces(self, Tn, Fn):
        """Создает массив граней для меша.
        
        Args:
            Tn: Количество точек по времени
            Fn: Количество точек по частоте
            
        Returns:
            Массив граней в формате PyVista
        """
        faces = []
        
        def idx(i, j):
            return i * Fn + j
        
        for i in range(Tn - 1):
            for j in range(Fn - 1):
                v0, v1, v2, v3 = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
                faces.extend([3, v0, v1, v2])
                faces.extend([3, v0, v2, v3])
        
        return np.array(faces, dtype=np.int32)

