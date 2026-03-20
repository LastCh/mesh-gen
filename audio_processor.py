"""Обработка аудио и вычисление спектрограммы."""

import os
import warnings
import numpy as np
import librosa


class AudioProcessor:
    """Класс для обработки аудио файлов и вычисления спектрограммы."""
    
    def __init__(self, n_fft=2048, hop_length=512):
        """Инициализация процессора аудио.
        
        Args:
            n_fft: Размер окна FFT
            hop_length: Длина hop для STFT
        """
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        self.audio_data = None
        self.sample_rate = None
        self.spectrogram_data = None
        self.freqs = None
        self.times = None
        self.db_min = None
        self.db_max = None
        self.audio_file_path = None
    
    def load_audio(self, file_path):
        """Загружает аудио файл и вычисляет спектрограмму.
        
        Args:
            file_path: Путь к аудио файлу
            
        Returns:
            True если успешно, False иначе
            
        Raises:
            Exception: При ошибке загрузки или обработки
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y, sr = librosa.load(file_path, sr=None, mono=True)
        
        if len(y) == 0:
            raise ValueError("Пустой аудиофайл")
        
        self.audio_data = y
        self.sample_rate = sr
        self.audio_file_path = file_path
        
        # Вычисляем спектрограмму
        self.compute_spectrogram(y, sr)
        
        return True
    
    def compute_spectrogram(self, audio_data=None, sample_rate=None, 
                           n_fft=None, hop_length=None, window='hann'):
        """Вычисляет спектрограмму из аудио данных.
        
        Args:
            audio_data: Массив аудио данных (если None, использует self.audio_data)
            sample_rate: Частота дискретизации (если None, использует self.sample_rate)
            n_fft: Размер окна FFT (если None, использует self.n_fft)
            hop_length: Длина hop для STFT (если None, использует self.hop_length)
            window: Тип окна ('hann', 'hamming', 'blackman', 'kaiser', 'bartlett')
        """
        if audio_data is None:
            audio_data = self.audio_data
        if sample_rate is None:
            sample_rate = self.sample_rate
        if n_fft is None:
            n_fft = self.n_fft
        if hop_length is None:
            hop_length = self.hop_length
        
        if audio_data is None or sample_rate is None:
            raise ValueError("Аудио данные не загружены")
        
        # Обновляем параметры
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        # Вычисляем STFT с указанным окном
        # Для некоторых окон нужны параметры, поэтому используем только простые типы
        if window == 'kaiser':
            # Kaiser требует параметр beta, используем hann вместо него
            window = 'hann'
        
        S = np.abs(librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length, window=window))
        S_db = librosa.amplitude_to_db(S, ref=np.max)
        
        self.db_min = float(S_db.min())
        self.db_max = float(S_db.max())
        self.spectrogram_data = S_db.T
        
        # Вычисляем частоты и времена
        self.freqs = librosa.fft_frequencies(sr=sample_rate, n_fft=self.n_fft)
        self.times = librosa.frames_to_time(
            np.arange(self.spectrogram_data.shape[0]),
            sr=sample_rate,
            hop_length=self.hop_length,
            n_fft=self.n_fft
        )
    
    def get_audio_info(self):
        """Возвращает информацию о загруженном аудио.
        
        Returns:
            Словарь с информацией или None если аудио не загружено
        """
        if self.audio_data is None or self.sample_rate is None:
            return None
        
        duration = len(self.audio_data) / self.sample_rate
        filename = os.path.basename(self.audio_file_path) if self.audio_file_path else "Unknown"
        
        info = {
            "filename": filename,
            "duration": duration,
            "sample_rate": self.sample_rate,
            "n_fft": self.n_fft,
            "frames": self.spectrogram_data.shape[0] if self.spectrogram_data is not None else 0,
            "frequencies": self.spectrogram_data.shape[1] if self.spectrogram_data is not None else 0,
            "db_min": self.db_min,
            "db_max": self.db_max
        }
        
        return info
    
    def get_spectrogram_segment(self, t0, t1, freq_max=None):
        """Получает сегмент спектрограммы для заданного временного окна.
        
        Args:
            t0: Начальный индекс кадра
            t1: Конечный индекс кадра (не включительно)
            freq_max: Максимальная частота в Гц (если None, используется вся)
            
        Returns:
            Кортеж (Z, actual_freq_khz) где Z - сегмент спектрограммы,
            actual_freq_khz - фактическая максимальная частота в кГц
        """
        if self.spectrogram_data is None:
            return None, 0.0
        
        Z = self.spectrogram_data[t0:t1, :]
        
        if freq_max is not None:
            idx_freq = np.searchsorted(self.freqs, freq_max)
            Z = Z[:, :max(1, idx_freq)]
            actual_freq_khz = self.freqs[idx_freq - 1] / 1000 if idx_freq > 0 else 0
        else:
            actual_freq_khz = self.freqs[-1] / 1000 if len(self.freqs) > 0 else 0
        
        return Z, actual_freq_khz

