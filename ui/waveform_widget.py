"""
Waveform visualization widget for real-time audio display
"""
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPointF, QTimer
from collections import deque


class WaveformWidget(QWidget):
    """Widget to display real-time audio waveform"""

    def __init__(self, parent=None, buffer_size=50):
        """
        Initialize waveform widget

        Args:
            parent: Parent widget
            buffer_size: Number of audio chunks to display (reduced for performance)
        """
        super().__init__(parent)
        self.buffer_size = buffer_size
        self.audio_buffer = deque(maxlen=buffer_size)
        self.is_recording = False
        self._pending_data = []

        # Set minimum size
        self.setMinimumHeight(100)

        # Rate limiting timer - update display at max 30 FPS
        self.update_timer = QTimer()
        self.update_timer.setInterval(33)  # ~30 FPS
        self.update_timer.timeout.connect(self._process_pending_data)

        # Initialize with zeros
        self._reset_buffer()

    def _reset_buffer(self):
        """Reset the audio buffer with zeros"""
        self.audio_buffer.clear()
        for _ in range(self.buffer_size):
            self.audio_buffer.append(np.zeros(1))

    def update_waveform(self, audio_data):
        """
        Update waveform with new audio data (rate-limited)

        Args:
            audio_data: Numpy array of audio samples
        """
        if not self.is_recording or audio_data is None or len(audio_data) == 0:
            return

        # For mono, ensure we have a 1D array
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]

        # Aggressive downsampling for performance
        target_samples = 128  # Reduced from 512
        if len(audio_data) > target_samples:
            step = len(audio_data) // target_samples
            audio_data = audio_data[::step]

        # Store in pending queue instead of immediately updating
        self._pending_data.append(audio_data)

    def _process_pending_data(self):
        """Process pending audio data and update display (called by timer)"""
        if not self._pending_data:
            return

        # Process all pending data at once
        for audio_data in self._pending_data:
            self.audio_buffer.append(audio_data)

        self._pending_data.clear()
        self.update()  # Single repaint for all accumulated data

    def start_recording(self):
        """Start recording mode"""
        self.is_recording = True
        self._reset_buffer()
        self._pending_data.clear()
        self.update_timer.start()  # Start the rate-limited update timer
        self.update()

    def stop_recording(self):
        """Stop recording mode"""
        self.is_recording = False
        self.update_timer.stop()  # Stop the update timer
        self._pending_data.clear()
        self._reset_buffer()
        self.update()

    def paintEvent(self, event):
        """Paint the waveform"""
        painter = QPainter(self)
        # Disable antialiasing for better performance
        # painter.setRenderHint(QPainter.Antialiasing)

        # Get widget dimensions
        width = self.width()
        height = self.height()

        # Draw background
        painter.fillRect(0, 0, width, height, QColor(20, 20, 30))

        if not self.is_recording:
            # Draw placeholder text when not recording
            painter.setPen(QColor(100, 100, 120))
            painter.drawText(
                0, 0, width, height,
                Qt.AlignCenter,
                "Waveform-Anzeige\n(Aufnahme starten, um zu visualisieren)"
            )
            return

        # Draw center line
        center_y = height / 2
        painter.setPen(QPen(QColor(50, 50, 60), 1))
        painter.drawLine(0, int(center_y), width, int(center_y))

        # Calculate points per pixel
        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        if total_samples == 0:
            return

        # Draw waveform - optimized rendering
        painter.setPen(QPen(QColor(0, 200, 100), 1))  # Thinner line for performance

        # Limit maximum number of points to draw (performance optimization)
        max_points = width  # One point per pixel maximum
        all_samples = []
        for chunk in self.audio_buffer:
            all_samples.extend(chunk)

        if len(all_samples) == 0:
            return

        # Downsample to match widget width
        if len(all_samples) > max_points:
            step = len(all_samples) // max_points
            all_samples = all_samples[::step]

        # Create points
        pixels_per_sample = width / len(all_samples) if len(all_samples) > 0 else 0
        prev_x, prev_y = 0, center_y

        for i, sample in enumerate(all_samples):
            x = i * pixels_per_sample
            # Normalize sample to widget height
            y = center_y - (sample * height * 0.4)  # 0.4 to leave margin
            y = max(0, min(height, y))  # Clamp to widget bounds

            # Draw line from previous point
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
            prev_x, prev_y = x, y

        # Draw level indicators
        painter.setPen(QPen(QColor(80, 80, 90), 1))
        # +/- 0.5 level lines
        for level in [0.5, -0.5]:
            y = center_y - (level * height * 0.4)
            painter.drawLine(0, int(y), width, int(y))
