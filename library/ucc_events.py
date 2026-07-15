"""Shared ucc.event emission (G2, roadmap §4C "Idempotency + envelopes").

Dual-writes a schema-conformant `ucc.event` alongside every legacy
`LedgerManager.append()` audit record. The legacy ledger stays the primary,
unchanged read path; this is additive.

VM-Factory has no canonical `node_`/`act_` ULID ids yet (`ucc.node` and
friends are still queued per UCC-Standards §17) — node names and actor
strings are the only identity that exists today. `deterministic_id` derives
a stable, correctly-formatted-but-non-canonical id from those strings so
events about "the same" node/actor correlate consistently across the
stream. Once real canonical ids land, replace this with the genuine id.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ucc_contracts import new_id, validate_document, ID_PREFIXES

MODULE_ID = "vm-factory"

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ucc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def deterministic_id(prefix: str, seed: str) -> str:
    if prefix not in ID_PREFIXES:
        raise ValueError(f"Unknown id prefix {prefix!r}.")
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    value = int.from_bytes(digest[:16], "big")
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return f"{prefix}_{''.join(reversed(chars))}"


def _next_producer_sequence(events_path: Path) -> int:
    if not events_path.exists():
        return 0
    with events_path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def build_event(*, event_type: str, node_name: str, actor: str,
                 payload: dict[str, Any], producer_sequence: int) -> dict[str, Any]:
    operation_id = new_id("op")
    instance_id = new_id("act")
    now = ucc_now_iso()
    event = {
        "schema": "ucc.event",
        "schema_version": 1,
        "event_id": new_id("evt"),
        "event_type": event_type,
        "occurred_at": now,
        "recorded_at": now,
        "producer": {"module_id": MODULE_ID, "instance_id": instance_id},
        "actor": {"kind": "human", "id": deterministic_id("act", f"actor:{actor}")},
        "subject": {"kind": "node", "id": deterministic_id("node", f"node:{node_name}")},
        "operation_id": operation_id,
        "request_id": new_id("req"),
        "correlation_id": new_id("corr"),
        "producer_sequence": producer_sequence,
        "payload": payload,
    }
    validate_document("event", event)
    return event


def emit_event(events_path: Path, *, event_type: str, node_name: str, actor: str,
               payload: dict[str, Any]) -> dict[str, Any]:
    sequence = _next_producer_sequence(events_path)
    event = build_event(event_type=event_type, node_name=node_name, actor=actor,
                        payload=payload, producer_sequence=sequence)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    data = line.encode("utf-8")
    fd = os.open(events_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return event
