# Overview

This project implements a data processing pipeline to process simulated vibration sensor data. It reads sensor measurements from the base dataset, processes said measurements to find anomalies and uses a SeaweedFS container to store data objects.

### Main Components
- Dataset reader - Reads measurements from the base dataset
- Data processor - Retrieves said measurements and calculates statistics to detect anomalies
- Cloud sync - Persists events into a sqlite outbox and uploads them to the SeaweedFS object storage

### Dataset Reader
This part is responsible for extracting the data and converting it into objects for downstream processing.
- Reading the input dataset.
- Extracting timestamps and sensor measurements.
- Converting raw values into the application's sample representation.
- Handling missing or invalid data according to the reader's validation rules.
- Providing samples to the processing pipeline.

Transforms the mentioned measurements into the following class:

```json
@dataclass(frozen=True)
class SensorSample:
    timestamp: float
    strain: float
    temperature: float
```

### Data Processor
Processes the retrived structures and applies signal processing and anomaly detection.
- Maintain a window or buffer of recent measurements.
- Calcule signal characteristics.
- Apply anomaly-detection rules.
- Perform frequency-domain analysis, such as FFT, when configured.
- Produce processing results that indicate whether an anomaly was detected.

Transforms the data into the following class:

```json
@dataclass(frozen=True)
class WindowData:
    timestamp: float
    samples: int
    rms: float
    mean: float
    std: float
    dominant_frequency: Optional[float]
    anomaly: bool
```

### Cloud Sync
Takes care of the transfer of events to S3 compatible object storage. It uses SQLite as a local outbox and Seaweedfs as object storage.

- Accepts processed events from the pipeline.
- Serializes events into JSON.
- Stores pending events in a local SQLite database.
- Uploades batches to an S3-compatible bucket.
- Marks events as synchronized only after a successful upload.
- Retries pending uploads when the storage service is temporarily unavailable.

#### Local outbox
The synchronization flow is as follows:
- A event is added to the outbox
- The sync worker checks and retrives a batch of pending events
- Serializes this batch into JSON
- Upload this data onto seaweedfs
- Mark events as synchronized

If this fails, the events should stay pending for later processing.

#### Object storage
Seaweedfs provides a compatible S3 API. The JSON payloads and keys follow this naming convention:
```
batches/<first_event_id>_<last_event_id>.json
```

### How to run 
Create and activate a Python virtual environment:
```
python -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:
```
pip install -r requirements.txt
```

Next, start the seaweedfs container:

```
docker compose up -d
```

And run the python code:

```
python src/main.py
```

### Missing steps

Due to time concerns, I was not able to implement the tests needed to properly cover this. I would add:

- Dataset reader
    - Valid dataset. Verifies that the logic correctly reads the measurements
    - Empty dataset. Handles a file with no data without crashing
    - Missing values. Handles blank fields according to the expected input rules without silently replacing them with zero.
- Data Processor
    - Injected fault. Correctly detects an injected fault.
    - Insufficient samples. Handles incomplete windows without crashing.
    - Fault recovery. Behaves correctly when returning to a normal signal.
    - Threshold boundaries — correctly handles values immediately below, at, and above detection thresholds.
- Cloud Sync
    - Correctly enqueues event.
    - Successfully uploads batch to object storage.
    - Retries after failure.

- Integration tests:
    - Successfull end-to-end pipeline.
    - Integration with object storage. Verifies that, in case of a failure, data is eventually uploaded onto the object storage.
    - Successfull anomaly detection. 