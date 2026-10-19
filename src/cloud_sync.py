from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


logger = logging.getLogger(__name__)

create_events_schema = """
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0
                        CHECK (synced IN (0, 1))
                )
                """

create_events_index = """
                CREATE INDEX IF NOT EXISTS
                idx_outbox_pending
                ON outbox (synced, id)
                """

insert_into_outbox = """
                INSERT INTO outbox (
                    event_id, payload, created_at
                )
                VALUES (?, ?, ?)
                """

get_count = """SELECT COUNT(*) AS count FROM outbox WHERE synced = 0"""

get_event = """
                SELECT id, event_id, payload, created_at
                FROM outbox
                WHERE synced = 0
                ORDER BY id
                LIMIT ?
                """

class CloudSync:
    def __init__(
        self,
        db_path: str | Path = "data/cloud_sync.db",
        *,
        endpoint_url: str | None = None,
        bucket: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        batch_size: int = 100,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size

        self.bucket = bucket or os.getenv(
            "S3_BUCKET", "synthetic-vibration-sensor-events"
        )

        self.s3 = boto3.client(
                "s3",
                endpoint_url=endpoint_url or os.getenv(
                    "S3_ENDPOINT_URL", "http://localhost:8333"
                ),
                region_name=region or "us-east-1",
                aws_access_key_id=access_key or os.getenv(
                    "AWS_ACCESS_KEY_ID", "admin"
                ),
                aws_secret_access_key=secret_key or os.getenv(
                    "AWS_SECRET_ACCESS_KEY", "secret"
                ),
                config=Config(s3={"addressing_style": "path"}),
            )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:

            connection.execute(
                create_events_schema
            )

            connection.execute(
                create_events_index
            )

    def enqueue(self, event: Any) -> str:
        if is_dataclass(event) and not isinstance(event, type):
            event = asdict(event)

        if not isinstance(event, Mapping):
           raise TypeError(
               "event must be mapping or dataclass instance"
           )

        event_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        payload = json.dumps(
            dict(event),
            separators=(",", ":"),
            allow_nan=False,
        )

        with self._connect() as connection:
            connection.execute(
                insert_into_outbox,
                (event_id, payload, created_at)
            )

        return event

    def pending_events(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                get_count
            ).fetchone()
        
        return int(row["count"])

    def sync_batch(self) -> int:
        with self._connect() as connection:
            rows = connection.execute(
                get_event,
                (self.batch_size,)
            ).fetchall()

        if not rows:
            return 0

        events = [
            {
                "event_id": row["event_id"],
                "created_at": row["created_at"],
                "data": json.loads(row["payload"]),
            } for row in rows
        ]

        first_row_id = rows[0]["event_id"]
        last_row_id = rows[-1]["event_id"]
        object_name = f"batches/{first_row_id}-{last_row_id}.json" 

        batch = {
            "batch_id": f"{first_row_id}-{last_row_id}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(events),
            "events": events
        }

        upload_body = json.dumps(
            batch,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

        self.s3.put_object(
            Bucket=self.bucket,
            Key=object_name,
            Body=upload_body,
            ContentType="application/json",
        )

        row_ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in row_ids)

        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE outbox
                SET synced = 1
                WHERE synced = 0
                  AND id IN ({placeholders})
                """,
                row_ids,
            )

        logger.info(
            "Uploaded %d events to s3://%s/%s",
            len(events),
            self.bucket,
            object_name,
        )

        return len(events)

    def sync_all_pending(self) -> int:
        total_synced = 0

        while True:
            synced = self.sync_batch()

            if synced == 0:
                break

            total_synced += synced

        return total_synced

    def run(self, interval_seconds: float = 5.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

        logger.info("Cloud sync worker started")

        while True:
            try:
                self.sync_all_pending()
            except (BotoCoreError, ClientError):
                logger.exception(
                    "Cloud upload failed; events remain pending"
                )
            except sqlite3.Error:
                logger.exception("Local outbox database error")
            except (ValueError, TypeError):
                logger.exception(
                    "Invalid event payload; check queued data"
                )

            time.sleep(interval_seconds)