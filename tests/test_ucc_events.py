"""G2 dual-write: every LedgerManager.append() also appends a schema-
conformant ucc.event to a sibling per-producer stream, alongside (not
instead of) the legacy audit.jsonl ledger. Explicit paths only — no
`.parent.parent` guessing that could escape the caller's chosen root."""
import json

from library.ledger import LedgerManager
from library.models import LedgerAction
from ucc_contracts import validate_document


def _read_events(path):
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l]
    return [json.loads(l) for l in lines]


def test_append_dual_writes_conformant_ucc_event(tmp_path):
    ledger_path = tmp_path / "ledger" / "audit.jsonl"
    events_path = tmp_path / "events" / "vm-factory.jsonl"
    manager = LedgerManager(ledger_path, ucc_events_file=events_path)

    manager.append(actor="sarge", action=LedgerAction.NODE_CREATE, node="w-01",
                    params={"image": "gold-v1"}, result="ok")

    events = _read_events(events_path)
    assert len(events) == 1
    validate_document("event", events[0])
    assert events[0]["event_type"] == "node.create_completed"
    assert events[0]["producer"]["module_id"] == "vm-factory"


def test_default_events_path_stays_sibling_of_ledger_file(tmp_path):
    """Regression: an earlier version derived the events path via
    ledger_file.parent.parent, which escaped an isolated tmp root whenever
    the ledger file wasn't nested two levels deep. Default must never climb
    above the caller's chosen directory."""
    ledger_path = tmp_path / "ledger.jsonl"  # flat, one level — matches
    # the repo's own pre-existing test_library.py call pattern.
    manager = LedgerManager(ledger_path)

    manager.append(actor="sarge", action=LedgerAction.NODE_CREATE, node="w-01",
                    params={}, result="ok")

    assert manager._ucc_events_file.exists()
    assert manager._ucc_events_file.parent == tmp_path


def test_failed_result_maps_to_failed_event_type(tmp_path):
    ledger_path = tmp_path / "ledger" / "audit.jsonl"
    events_path = tmp_path / "events" / "vm-factory.jsonl"
    manager = LedgerManager(ledger_path, ucc_events_file=events_path)

    manager.append(actor="sarge", action=LedgerAction.NODE_RESET, node="w-01",
                    params={}, result="error")

    events = _read_events(events_path)
    assert events[0]["event_type"] == "node.reset_failed"


def test_same_node_name_correlates_across_events(tmp_path):
    ledger_path = tmp_path / "ledger" / "audit.jsonl"
    events_path = tmp_path / "events" / "vm-factory.jsonl"
    manager = LedgerManager(ledger_path, ucc_events_file=events_path)

    manager.append(actor="sarge", action=LedgerAction.NODE_CREATE, node="w-01",
                    params={}, result="ok")
    manager.append(actor="sarge", action=LedgerAction.NODE_RESET, node="w-01",
                    params={}, result="ok")

    events = _read_events(events_path)
    assert events[0]["subject"]["id"] == events[1]["subject"]["id"]


def test_legacy_ledger_still_written_alongside_ucc_event(tmp_path):
    ledger_path = tmp_path / "ledger" / "audit.jsonl"
    events_path = tmp_path / "events" / "vm-factory.jsonl"
    manager = LedgerManager(ledger_path, ucc_events_file=events_path)

    manager.append(actor="sarge", action=LedgerAction.NODE_CREATE, node="w-01",
                    params={}, result="ok")

    assert ledger_path.exists()
    assert len(list(manager.stream())) == 1
    assert len(_read_events(events_path)) == 1
