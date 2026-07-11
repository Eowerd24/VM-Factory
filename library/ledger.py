import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Generator
from library.models import LedgerRecord, LedgerAction

class LedgerError(Exception):
    """Custom exception for ledger operations."""
    pass

class LedgerManager:
    """Manages append-only JSONL audit logs."""

    def __init__(self, ledger_file: Path):
        self.ledger_file = ledger_file

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
            return record
        except Exception as e:
            raise LedgerError(f"Failed to append to ledger at {self.ledger_file}: {e}")

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
