import csv
from pathlib import Path
from collections.abc import Iterator
from datetime import datetime
from src.models import SensorSample

def check_file_valid(dataset_columns: set[str], actual_columns: set[str]):
    missing_columns = dataset_columns - actual_columns
    if missing_columns:
        raise ValueError(
            "Invalid file, missing columns"
        )

def read_dataset(file_path: str | Path) -> Iterator[SensorSample]:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError("Dataset not found")

    with path.open("r", newline="") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")

        dataset_columns = {"date_time", "strain", "temperature"}
        actual_columns = set(reader.fieldnames or [])

        check_file_valid(dataset_columns=dataset_columns, actual_columns=actual_columns)

        for idx, row in enumerate(reader, start=2):
            strain_str = (row.get("strain") or "").strip()
            if not strain_str:
                continue

            try:
                timestamp = datetime.fromisoformat(
                    row["date_time"].strip().replace("Z", "+00:00")
                ).timestamp()

                strain = float(strain_str)

                temperature_str = (row.get("temperature") or "").strip()
                temperature = (
                    float(temperature_str) if temperature_str else None
                )
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError(
                    f"Invalid data at row: {row}: {exc}"
                ) from exc
            
            yield SensorSample(
                timestamp=timestamp,
                strain=strain,
                temperature=temperature,
            )