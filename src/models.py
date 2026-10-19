from dataclasses import dataclass

@dataclass(frozen=True)
class SensorSample:
    timestamp: float
    strain: float
    temperature: float
