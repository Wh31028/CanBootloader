"""P02 reproducible loss, deadlines, and append-only trial records."""
import csv
import hashlib
import json
import os
import random
import time
from datetime import datetime, timezone

MODEL_VERSION = "p02-frame-omission-v1"
CSV_HEADERS = ["attempt_id", "timestamp_utc", "protocol", "loss_rate", "seed",
    "firmware_sha256", "transaction_status", "boot_status", "failure_stage",
    "elapsed_sec", "send_attempts", "software_drops", "socket_send_success",
    "send_errors", "protocol_rx", "invalid_protocol_rx", "retransmit_attempts",
    "retransmit_send_success", "drop_events_json", "note"]

class DeadlineExceeded(RuntimeError):
    pass

class LossModel:
    """Independent Bernoulli omission for eligible DATA-carrying frames only."""
    def __init__(self, seed, rate):
        self.seed, self.rate = int(seed), float(rate)
        self.random = random.Random(self.seed)
        self.events = []
    def drop(self, role, block, frame_index, retransmit=False):
        # START/END/JUMP, Custom headers, ISO-TP FF, ACK/NACK/FC are not eligible.
        if role not in ("custom_data", "isotp_cf"):
            return False
        dropped = self.random.random() < self.rate
        if dropped:
            self.events.append({"role": role, "block": block, "frame_index": frame_index,
                                "retransmit": bool(retransmit)})
        return dropped

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for part in iter(lambda: source.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def require_deadline(deadline, stage):
    if time.monotonic() >= deadline:
        raise DeadlineExceeded(stage)

def append_result(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in CSV_HEADERS})

def append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as output:
        output.write(json.dumps(record, sort_keys=True) + "\n")
