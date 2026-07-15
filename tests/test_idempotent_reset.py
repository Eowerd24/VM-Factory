"""M-b: idempotent reset_node — the §5 idempotent-replay and idempotency-
conflict fixtures, wired against a real VM-Factory operation."""
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from library.engine import NodeLifecycleEngine
from library.factory_port import VMFactoryFactoryPort
from library.idempotency_store import IdempotencyStore
from library.models import NodeState
from ucc_contracts.ports import RefusalCode
from ucc_contracts import validate_document


@pytest.fixture
def engine(tmp_path):
    return NodeLifecycleEngine(tmp_path)


def _reset_ready_node(engine, tmp_path, name="w-01"):
    """Create a node and drive it through assign -> collect so it's in
    'reporting' state, engine.reset()'s precondition."""
    config_path = tmp_path / "project.yaml"
    config_data = {
        "repo": "https://github.com/Eowerd24/VM-Factory.git",
        "image": "gold-server-2404-v1",
        "node_type": "ai-worker",
        "resources": {"vcpu": 2, "ram_gb": 4, "disk_gb": 20},
        "branch_prefix": "ai/test",
        "credential_template": {"scopes": ["contents:rw"], "ttl_days": 7},
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)
    manifest = engine.create(name, config_path)
    assert manifest.state == NodeState.READY
    engine.assign(name, repo_url="https://example.com/x.git")
    engine.collect(name, remote_outbox_dir=Path("/home/agent/outbox"))
    return name


def test_new_key_proceeds_and_returns_a_validated_result(engine, tmp_path):
    name = _reset_ready_node(engine, tmp_path)
    port = VMFactoryFactoryPort(engine)

    result = port.reset_node({"name": name, "idempotency_key": "k1"})

    assert result.ok is True
    validate_document("result", result.value["result"])


def test_identical_replay_returns_the_same_stored_result(engine, tmp_path):
    name = _reset_ready_node(engine, tmp_path)
    port = VMFactoryFactoryPort(engine)

    first = port.reset_node({"name": name, "idempotency_key": "k1"})
    second = port.reset_node({"name": name, "idempotency_key": "k1"})

    assert first.value == second.value
    assert first.value["result"]["result_id"] == second.value["result"]["result_id"]


def test_replay_does_not_reexecute_reset(engine, tmp_path):
    """A second reset would fail (no sx-ready snapshot post-reset until
    reassigned) — replay must not attempt it. If it did, this would raise."""
    name = _reset_ready_node(engine, tmp_path)
    port = VMFactoryFactoryPort(engine)

    port.reset_node({"name": name, "idempotency_key": "k1"})
    result = port.reset_node({"name": name, "idempotency_key": "k1"})

    assert result.ok is True  # not "failed" — proves it replayed, not re-ran


def test_same_key_different_node_is_a_conflict(engine, tmp_path):
    name1 = _reset_ready_node(engine, tmp_path, name="w-01")
    name2 = _reset_ready_node(engine, tmp_path, name="w-02")
    port = VMFactoryFactoryPort(engine)

    port.reset_node({"name": name1, "idempotency_key": "k1"})
    result = port.reset_node({"name": name2, "idempotency_key": "k1"})

    assert result.ok is False
    assert result.disposition == "refused"
    assert result.refusal_code == RefusalCode.IDEMPOTENCY_CONFLICT


def test_no_idempotency_key_keeps_legacy_behavior(engine, tmp_path):
    name = _reset_ready_node(engine, tmp_path)
    port = VMFactoryFactoryPort(engine)

    result = port.reset_node({"name": name})

    assert result.ok is True
    assert "result" not in result.value  # legacy shape, no envelope wrapping
    # the idempotency path was never entered, so it never created its store file
    assert not (engine.state_dir / "idempotency.db").exists()


def test_failed_reset_is_not_stored_and_may_be_retried(engine, tmp_path):
    config_path = tmp_path / "project.yaml"
    config_data = {
        "repo": "https://github.com/Eowerd24/VM-Factory.git",
        "image": "gold-server-2404-v1", "node_type": "ai-worker",
        "resources": {"vcpu": 2, "ram_gb": 4, "disk_gb": 20},
        "branch_prefix": "ai/test", "credential_template": {"scopes": ["contents:rw"], "ttl_days": 7},
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)
    engine.create("w-01", config_path)  # ready, but never assigned -> no sx-ready snapshot
    port = VMFactoryFactoryPort(engine)

    first = port.reset_node({"name": "w-01", "idempotency_key": "k1"})
    assert first.disposition == "failed"

    store = IdempotencyStore(engine.state_dir / "idempotency.db")
    assert store.get("k1") is None

    second = port.reset_node({"name": "w-01", "idempotency_key": "k1"})
    assert second.disposition == "failed"  # retried, not a conflict


def test_ambiguous_reset_retry_refuses_without_rerunning(engine):
    port = VMFactoryFactoryPort(engine)

    with patch.object(
        engine,
        "reset",
        side_effect=RuntimeError("connection lost after dispatch"),
    ) as dispatch:
        with pytest.raises(RuntimeError):
            port.reset_node({"name": "w-01", "idempotency_key": "k-ambiguous"})
        retry = port.reset_node({"name": "w-01", "idempotency_key": "k-ambiguous"})

    assert retry.ok is False
    assert retry.refusal_code == RefusalCode.OUTCOME_UNKNOWN
    assert retry.retryable is False
    assert dispatch.call_count == 1
