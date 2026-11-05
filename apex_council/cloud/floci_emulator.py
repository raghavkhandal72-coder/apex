#!/usr/bin/env python3
"""
Apex-Sovereign: Floci Local AWS Cloud Emulator
Inspired by floci-io/floci (Zero-cost AWS local emulator)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass
class S3Object:
    bucket: str
    key: str
    data: bytes
    content_type: str
    etag: str
    size: int
    last_modified: float


@dataclasses.dataclass
class SQSMessage:
    message_id: str
    receipt_handle: str
    body: str
    attributes: Dict[str, Any]
    sent_at: float
    visible_after: float


class FlociCloudEmulator:
    """
    Hermetic local AWS emulator for S3, SQS, and DynamoDB.
    Runs in-memory with optional persistence to disk (.apex/floci/).
    Enables autonomous agent pipelines to test cloud workflows with 0 AWS bill.
    """

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = storage_dir or ".apex/floci"
        # S3 storage: bucket_name -> Dict[key, S3Object]
        self._s3_buckets: Dict[str, Dict[str, S3Object]] = {}
        # SQS storage: queue_name -> List[SQSMessage]
        self._sqs_queues: Dict[str, List[SQSMessage]] = {}
        # DynamoDB storage: table_name -> Dict[partition_key_value, Dict[str, Any]]
        self._dynamo_tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._dynamo_schemas: Dict[str, str] = {}  # table_name -> primary_key_field
        self._receipt_counter = 0
        self._state_file = os.path.join(self.storage_dir, "cloud_state.json")
        self._load_state()

    def _save_state(self) -> None:
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            serializable_s3 = {}
            for b, objs in self._s3_buckets.items():
                serializable_s3[b] = {}
                for k, obj in objs.items():
                    serializable_s3[b][k] = {
                        "bucket": obj.bucket,
                        "key": obj.key,
                        "data_b64": base64.b64encode(obj.data).decode("ascii"),
                        "content_type": obj.content_type,
                        "etag": obj.etag,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                    }
            state = {
                "s3": serializable_s3,
                "dynamo": self._dynamo_tables,
                "dynamo_schemas": self._dynamo_schemas,
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self) -> None:
        if not os.path.isfile(self._state_file):
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            for b, objs in state.get("s3", {}).items():
                self._s3_buckets[b] = {}
                for k, data in objs.items():
                    raw = base64.b64decode(data["data_b64"])
                    self._s3_buckets[b][k] = S3Object(
                        bucket=data["bucket"],
                        key=data["key"],
                        data=raw,
                        content_type=data["content_type"],
                        etag=data["etag"],
                        size=data["size"],
                        last_modified=data["last_modified"],
                    )
            self._dynamo_tables = state.get("dynamo", {})
            self._dynamo_schemas = state.get("dynamo_schemas", {})
        except Exception:
            pass

    # =========================================================================
    # S3 Emulator APIs
    # =========================================================================

    def s3_create_bucket(self, bucket_name: str) -> bool:
        if bucket_name in self._s3_buckets:
            return False
        self._s3_buckets[bucket_name] = {}
        self._save_state()
        return True

    def s3_put_object(
        self,
        bucket: str,
        key: str,
        body: bytes | str,
        content_type: str = "application/octet-stream",
    ) -> S3Object:
        if bucket not in self._s3_buckets:
            self.s3_create_bucket(bucket)

        if isinstance(body, str):
            raw_data = body.encode("utf-8")
        else:
            raw_data = body

        etag = hashlib.md5(raw_data).hexdigest()
        obj = S3Object(
            bucket=bucket,
            key=key,
            data=raw_data,
            content_type=content_type,
            etag=etag,
            size=len(raw_data),
            last_modified=time.time(),
        )
        self._s3_buckets[bucket][key] = obj
        self._save_state()
        return obj

    def s3_get_object(self, bucket: str, key: str) -> Optional[S3Object]:
        if bucket not in self._s3_buckets:
            return None
        return self._s3_buckets[bucket].get(key)

    def s3_list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        if bucket not in self._s3_buckets:
            return []
        results = []
        for key, obj in self._s3_buckets[bucket].items():
            if not prefix or key.startswith(prefix):
                results.append({
                    "Key": obj.key,
                    "Size": obj.size,
                    "ETag": obj.etag,
                    "LastModified": obj.last_modified,
                    "ContentType": obj.content_type,
                })
        return sorted(results, key=lambda x: x["Key"])

    def s3_delete_object(self, bucket: str, key: str) -> bool:
        if bucket in self._s3_buckets and key in self._s3_buckets[bucket]:
            del self._s3_buckets[bucket][key]
            self._save_state()
            return True
        return False

    # =========================================================================
    # SQS Emulator APIs
    # =========================================================================

    def sqs_create_queue(self, queue_name: str) -> str:
        if queue_name not in self._sqs_queues:
            self._sqs_queues[queue_name] = []
        return f"http://localhost:4566/000000000000/{queue_name}"

    def sqs_send_message(
        self, queue_name: str, body: str, attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        if queue_name not in self._sqs_queues:
            self.sqs_create_queue(queue_name)

        now = time.time()
        self._receipt_counter += 1
        msg_id = f"msg-{int(now * 1000)}-{self._receipt_counter}"
        receipt = hashlib.sha256(f"{msg_id}:{now}".encode()).hexdigest()[:32]

        msg = SQSMessage(
            message_id=msg_id,
            receipt_handle=receipt,
            body=body,
            attributes=attributes or {},
            sent_at=now,
            visible_after=now,
        )
        self._sqs_queues[queue_name].append(msg)
        return msg_id

    def sqs_receive_messages(
        self, queue_name: str, max_messages: int = 1, visibility_timeout: float = 30.0
    ) -> List[SQSMessage]:
        if queue_name not in self._sqs_queues:
            return []

        now = time.time()
        available = []
        for msg in self._sqs_queues[queue_name]:
            if msg.visible_after <= now:
                msg.visible_after = now + visibility_timeout
                available.append(msg)
                if len(available) >= max_messages:
                    break
        return available

    def sqs_delete_message(self, queue_name: str, receipt_handle: str) -> bool:
        if queue_name not in self._sqs_queues:
            return False
        initial_len = len(self._sqs_queues[queue_name])
        self._sqs_queues[queue_name] = [
            m for m in self._sqs_queues[queue_name] if m.receipt_handle != receipt_handle
        ]
        return len(self._sqs_queues[queue_name]) < initial_len

    def sqs_get_queue_attributes(self, queue_name: str) -> Dict[str, Any]:
        if queue_name not in self._sqs_queues:
            return {"ApproximateNumberOfMessages": 0, "ApproximateNumberOfMessagesNotVisible": 0}
        now = time.time()
        visible = sum(1 for m in self._sqs_queues[queue_name] if m.visible_after <= now)
        in_flight = sum(1 for m in self._sqs_queues[queue_name] if m.visible_after > now)
        return {
            "ApproximateNumberOfMessages": visible,
            "ApproximateNumberOfMessagesNotVisible": in_flight,
            "TotalMessages": len(self._sqs_queues[queue_name]),
        }

    # =========================================================================
    # DynamoDB Emulator APIs
    # =========================================================================

    def dynamo_create_table(self, table_name: str, primary_key: str = "id") -> bool:
        if table_name in self._dynamo_tables:
            return False
        self._dynamo_tables[table_name] = {}
        self._dynamo_schemas[table_name] = primary_key
        self._save_state()
        return True

    def dynamo_put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        if table_name not in self._dynamo_tables:
            self.dynamo_create_table(table_name)

        pk_field = self._dynamo_schemas.get(table_name, "id")
        if pk_field not in item:
            raise ValueError(f"Missing primary key field '{pk_field}' in DynamoDB item")

        pk_val = str(item[pk_field])
        self._dynamo_tables[table_name][pk_val] = dict(item)
        self._save_state()
        return True

    def dynamo_get_item(self, table_name: str, key_val: Any) -> Optional[Dict[str, Any]]:
        if table_name not in self._dynamo_tables:
            return None
        return self._dynamo_tables[table_name].get(str(key_val))

    def dynamo_scan(
        self, table_name: str, filter_fn: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        if table_name not in self._dynamo_tables:
            return []
        items = list(self._dynamo_tables[table_name].values())
        if filter_fn:
            items = [item for item in items if filter_fn(item)]
        return items

    def dynamo_delete_item(self, table_name: str, key_val: Any) -> bool:
        if table_name in self._dynamo_tables and str(key_val) in self._dynamo_tables[table_name]:
            del self._dynamo_tables[table_name][str(key_val)]
            return True
        return False

    # =========================================================================
    # Global Snapshot & Stats
    # =========================================================================

    def get_cloud_stats(self) -> Dict[str, Any]:
        return {
            "s3_buckets_count": len(self._s3_buckets),
            "s3_objects_count": sum(len(objs) for objs in self._s3_buckets.values()),
            "sqs_queues_count": len(self._sqs_queues),
            "sqs_total_messages": sum(len(msgs) for msgs in self._sqs_queues.values()),
            "dynamodb_tables_count": len(self._dynamo_tables),
            "dynamodb_items_count": sum(len(items) for items in self._dynamo_tables.values()),
        }
