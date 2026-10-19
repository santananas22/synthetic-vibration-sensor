
from collections import deque
from math import sqrt
from typing import Optional
from src.models import Limits, SensorSample, WindowData

import numpy as np


class Processor:
    def __init__(
        self,
        sample_rate: float = 1000.0,
        window_seconds: float = 1.0,
        fft_every: int = 10,
        limits: Optional[Limits] = None,
    ):
        if sample_rate <= 0 or window_seconds <= 0:
            raise ValueError("Sample rate and window duration must be positive")
        if fft_every < 1:
            raise ValueError("fft_every must be at least 1")

        self.sample_rate = sample_rate
        self.window_size = max(1, round(sample_rate * window_seconds))
        self.fft_every = fft_every
        self.limits = limits or Limits()

        self._window = deque()
        self._sum = 0.0
        self._sum_squares = 0.0
        self._processed = 0
        self._dominant_frequency = None

    def process(self, sample: SensorSample) -> Optional[WindowData]:
        value = sample.strain

        if len(self._window) == self.window_size:
            oldest = self._window.popleft()
            self._sum -= oldest
            self._sum_squares -= (oldest * oldest)

        self._window.append(value)
        self._sum += value 
        self._sum_squares += (value * value)
        self._processed += 1

        if len(self._window) < self.window_size:
            return None

        size = len(self._window)
        mean = self._sum / size
        mean_square = self._sum_squares / size
        rms = sqrt(max(0.0, mean_square))
        variance = max(0.0, mean_square - (mean * mean))
        std = sqrt(max(0.0, variance))


        if self._dominant_frequency is None or self._processed % self.fft_every:
            self._dominant_frequency = self._calculate_dominant_frequency()
        
        contains_anomaly = self._contains_anomaly(frequency=self._dominant_frequency, rms=rms, std=std)

        return WindowData(
            timestamp=sample.temperature,
            samples=size,
            rms=rms,
            mean=mean,
            std=std,
            dominant_frequency=self._dominant_frequency,
            anomaly=contains_anomaly,
        )

    def _calculate_dominant_frequency(self)->Optional[float]:
        values = np.asarray(self._window, dtype=float)

        intensities = np.abs(np.fft.rfft(values))
        frequencies = np.fft.rfftfreq(len(values),d=1 / self.sample_rate)

        peak = int(np.argmax(intensities[1:])) + 1
        return float(frequencies[peak])

    def _contains_anomaly(self, frequency: float | None, rms: float, std: float)->Optional[bool]:
        if frequency is None:
            return True
        if frequency > self.limits.frequency_max or frequency < self.limits.frequency_min:
            return True
        if rms > self.limits.rms_max or rms < self.limits.rms_min:
            return True
        if std > self.limits.std_max:
            return True

        return False