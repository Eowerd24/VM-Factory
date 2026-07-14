import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Generator
from library.models import LedgerRecord, LedgerAction
from library.ucc_events import emit_event

class LedgerError(Exception):
    """Custom exception for ledger operations."""
    pass

class LedgerManager:
    """Manages append-only JSONL audit logs."""

    def __init__(self, ledger_file: Path, ucc_events_file: Optional[Path] = None):
        self.ledger_file = ledger_file
        # Explicit, not derived by path arithmetic from ledger_file: guessing
        # a "state root" via `.parent.parent` broke the moment a caller (e.g.
        # a test) didn't use the `<state_dir>/ledger/audit.jsonl` shape,
        # writing outside the caller's chosen root. Default is a plain
        # sibling of ledger_file itself, which can never escape it.
        self._ucc_events_file = ucc_events_file or (self.ledger_file.parent / "ucc-events.jsonl")

    def append(self, actor: str, action: LedgerAction, node: str, params: dict, result: str, sha256: Optional[dict] = None) -> LedgerRecord:
        """Appends a new audit record to the ledger file."""
        record = LedgerRecord(
            schema_version=1,
            ts=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            node=node,
            params=params,
            result=result,
            sha256=sha256
        )

        try:
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_file, "a") as f:
                f.write(record.model_dump_json() + "\n")
        except Exception as e:
            raise LedgerError(f"Failed to append to ledger at {self.ledger_file}: {e}")

        # Dual-write (roadmap §4C "Idempotency + envelopes"): the legacy
        # ledger above stays the primary, unchanged read path; this is
        # additive and must never block a legacy-ledger write that already
        # succeeded.
        event_type = f"{action.value}_completed" if result == "ok" else f"{action.value}_failed"
        emit_event(
            self._ucc_events_file,
            event_type=event_type,
            node_name=node,
            actor=actor,
            payload={"action": action.value, "result": result, "params": params},
        )
        return record

    def query(self, node: Optional[str] = None, action: Optional[LedgerAction] = None, actor: Optional[str] = None) -> List[LedgerRecord]:
        """Queries the ledger for matching records."""
        results = []
        for record in self.stream():
            if node and record.node != node:
                continue
            if action and record.action != action:
                continue
            if actor and record.actor != actor:
                continue
            results.append(record)
        return results

    def stream(self) -> Generator[LedgerRecord, None, None]:
        """Yields ledger records sequentially from the file."""
        if not self.ledger_file.exists():
            return

        try:
            with open(self.ledger_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield LedgerRecord.model_validate_json(line)
        except Exception as e:
            raise LedgerError(f"Failed to read ledger from {self.ledger_file}: {e}")
