"""Управление воспроизведением аудио через QMediaPlayer."""

import os
import tempfile
import warnings
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
import librosa
import soundfile as sf


class MediaController:
    """Класс для управления воспроизведением аудио."""
    
    def __init__(self):
        """Инициализация медиа контроллера."""
        self.media_player = QMediaPlayer()
        self.default_volume = 50
        self.media_player.setVolume(self.default_volume)
        
        self.audio_file_path = None
        self._temp_wav_path = None
        self._conversion_attempted = False
        self._attempts = 0
        
        # Подключаем обработчики ошибок
        self.media_player.error.connect(self._on_media_error)
    
    def load_file(self, file_path, callback=None):
        """Загружает аудио файл для воспроизведения.
        
        Args:
            file_path: Путь к аудио файлу
            callback: Функция обратного вызова при успешной загрузке (опционально)
        """
        self.audio_file_path = file_path
        self._temp_wav_path = None
        self._conversion_attempted = False
        self._attempts = 0
        
        self._try_prepare_media(file_path, callback)
    
    def _try_prepare_media(self, path, callback=None):
        """Пытается подготовить медиа для воспроизведения.
        
        Args:
            path: Путь к файлу
            callback: Функция обратного вызова
        """
        self._attempts += 1
        self._last_try_path = path
        
        self.media_player.stop()
        try:
            self.media_player.setPlaylist(None)
        except Exception:
            pass
        
        url = QUrl.fromLocalFile(path)
        self.media_player.setMedia(QMediaContent(url))
        
        QTimer.singleShot(800, lambda: self._check_media_ready(path, callback))
    
    def _check_media_ready(self, tried_path, callback=None):
        """Проверяет готовность медиа для воспроизведения.
        
        Args:
            tried_path: Путь к проверяемому файлу
            callback: Функция обратного вызова
        """
        try:
            duration = self.media_player.duration()
            if duration and duration > 100:
                print(f"Media ready: {tried_path} ({duration / 1000:.2f} сек)")
                self._conversion_attempted = False
                if callback:
                    callback(True)
                return
            
            # Пытаемся конвертировать MP3 в WAV
            if tried_path.lower().endswith(".mp3") and not self._conversion_attempted:
                print("MP3 not playable, converting to WAV...")
                self._conversion_attempted = True
                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                tmpf.close()
                self._temp_wav_path = tmpf.name
                
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        y, sr = librosa.load(tried_path, sr=None, mono=True)
                    sf.write(self._temp_wav_path, y, sr)
                    print("Converted to:", self._temp_wav_path)
                    self._try_prepare_media(self._temp_wav_path, callback)
                    return
                except Exception as e:
                    print("Conversion failed:", e)
            
            # Пытаемся использовать playlist
            if self._attempts <= 3:
                print("Trying playlist fallback...")
                try:
                    playlist = QMediaPlaylist()
                    playlist.addMedia(QMediaContent(QUrl.fromLocalFile(tried_path)))
                    playlist.setCurrentIndex(0)
                    self.media_player.setPlaylist(playlist)
                    QTimer.singleShot(800, lambda: self._check_media_ready(tried_path, callback))
                    return
                except Exception as e:
                    print("Playlist fallback failed:", e)
            
            print("Media failed to prepare:", tried_path)
            self.media_player.stop()
            if callback:
                callback(False)
            
        except Exception as e:
            print("Ошибка при проверке media readiness:", e)
            if callback:
                callback(False)
    
    def play(self):
        """Начинает воспроизведение."""
        current_media = self.media_player.media()
        if current_media.isNull():
            fallback = self._temp_wav_path if self._temp_wav_path else self.audio_file_path
            if fallback:
                self._try_prepare_media(fallback)
                QTimer.singleShot(1400, lambda: self.media_player.play())
            return
        
        self.media_player.play()
    
    def pause(self):
        """Приостанавливает воспроизведение."""
        try:
            self.media_player.pause()
        except Exception:
            pass
    
    def stop(self):
        """Останавливает воспроизведение."""
        try:
            self.media_player.stop()
        except Exception:
            pass
    
    def seek(self, position_ms):
        """Перемещает позицию воспроизведения.
        
        Args:
            position_ms: Позиция в миллисекундах
        """
        self.media_player.setPosition(position_ms)
    
    def set_volume(self, volume):
        """Устанавливает громкость.
        
        Args:
            volume: Громкость от 0 до 100
        """
        self.media_player.setVolume(volume)
    
    def get_position(self):
        """Возвращает текущую позицию воспроизведения.
        
        Returns:
            Позиция в миллисекундах или 0
        """
        try:
            return self.media_player.position()
        except Exception:
            return 0
    
    def get_duration(self):
        """Возвращает длительность аудио.
        
        Returns:
            Длительность в миллисекундах или 0
        """
        try:
            return self.media_player.duration()
        except Exception:
            return 0
    
    def get_state(self):
        """Возвращает состояние плеера.
        
        Returns:
            Состояние QMediaPlayer (PlayingState, PausedState, StoppedState)
        """
        return self.media_player.state()
    
    def connect_signals(self, position_changed=None, state_changed=None, error=None):
        """Подключает сигналы медиаплеера.
        
        Args:
            position_changed: Слот для сигнала positionChanged
            state_changed: Слот для сигнала stateChanged
            error: Слот для сигнала error
        """
        if position_changed:
            self.media_player.positionChanged.connect(position_changed)
        if state_changed:
            self.media_player.stateChanged.connect(state_changed)
        if error:
            self.media_player.error.connect(error)
    
    def _on_media_error(self, err):
        """Обработчик ошибок медиаплеера.
        
        Args:
            err: Код ошибки
        """
        print("QMediaPlayer error:", err, self.media_player.errorString())
    
    def cleanup(self):
        """Очищает временные файлы."""
        try:
            if self._temp_wav_path and os.path.exists(self._temp_wav_path):
                os.remove(self._temp_wav_path)
        except Exception:
            pass

