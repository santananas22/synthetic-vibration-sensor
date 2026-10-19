from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SensorSample:
    timestamp: float
    strain: float
    temperature: float

@dataclass(frozen=True)
class Limits:
    frequency_max: Optional[float] 
    frequency_min: Optional[float]
    rms_max: Optional[float]
    rms_min: Optional[float]
    std_max: Optional[float]

@dataclass(frozen=True)
class WindowData:
    timestamp: float
    samples: int
    rms: float
    mean: float
    std: float
    dominant_frequency: Optional[float]
    anomaly: bool