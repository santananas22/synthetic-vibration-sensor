import threading
from src.dataset import read_dataset
from src.processor import Processor
from src.models import Limits
from src.cloud_sync import CloudSync

dataset_path = "./data/sample_dataset_small.csv"

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

sync = CloudSync(
        db_path="data/cloud_sync.db",
        batch_size=100,
    )

sync_thread = threading.Thread(
    target=sync.run,
    kwargs={"interval_seconds": 5},
    daemon=True,
)
sync_thread.start()

for sample in read_dataset(dataset_path):
    result = processor.process(sample)

    if result is not None:
        sync.enqueue(result)