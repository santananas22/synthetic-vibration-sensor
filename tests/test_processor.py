import pytest
from src.processor import Processor
from src.models import SensorSample

def create_mock_sample(timestamp: float, strain: float) -> SensorSample:
    return SensorSample(
        timestamp=timestamp,
        strain=strain,
    )

def test_normal_signal():
    processor = Processor()

    results = [
        processor.process(create_mock_sample(float(i), 0.1))
        for i in range(100)
    ]

    anomalies = [
        result
        for result in results
        if result is not None and result.anomaly
    ]

    assert anomalies == []

