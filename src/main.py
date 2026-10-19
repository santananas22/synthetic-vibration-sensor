from src.dataset import read_dataset
from src.processor import Processor
from src.models import Limits

dataset_path = "/home/santana/projects/synthetic-vibration-sensor/data/sample_dataset_small.csv"

processor = Processor(
        sample_rate=1000,
        window_seconds=1.0,
        fft_every=10,
        limits=Limits(
            rms_min=0.0,
            rms_max=2.0,          
            std_max=1.8,
            frequency_min=40.0,
            frequency_max=60.0,
        ),
    )

for sample in read_dataset(dataset_path):
    print(processor.process(sample))