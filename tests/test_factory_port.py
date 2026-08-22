"""FactoryPort adapter conformance (S2-2 / S2-3).

All 10 methods have real implementations over canonical records:
- list_eligible_nodes
- reserve_node
- release_node
- request_execution
- get_execution
- collect_handback
- cancel_execution
- reset_node
- quarantine_node
- get_node_health

Plus S2-3 authority operations:
- transfer_to_node
- probe_host_key
- approve_host_key
- create_credential_lease
- cleanup_credential_lease (with quarantine on uncertain cleanup)
"""
from pathlib import Path
import yaml
import pytest

from library.engine import NodeLifecycleEngine
from library.factory_port import VMFactoryFactoryPort, build_factory_port
from library.models import NodeState
from ucc_contracts import validate_document, new_id
from ucc_contracts.ports import (
    CollectHandbackRequest, ExecutionRequestEnvelope, FactoryPort, PortResult, RefusalCode, ReserveNodeRequest,
)

VALID_DISPOSITIONS = {"accepted", "completed", "refused", "failed", "partial", "cancelled", "unknown"}


@pytest.fixture
def engine(tmp_path):
    return NodeLifecycleEngine(tmp_path)


@pytest.fixture
def ready_node(engine, tmp_path):
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
    manifest = engine.create("w-01", config_path)
    assert manifest.state == NodeState.READY
    return "w-01"


def test_adapter_satisfies_factory_port_protocol(engine):
    port = build_factory_port(engine)
    assert isinstance(port, FactoryPort)


def test_list_eligible_nodes_finds_ready_node(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    result = port.list_eligible_nodes({})
    assert result.ok is True
    assert result.disposition == "completed"
    assert any(n["name"] == "w-01" for n in result.value["nodes"])


def test_list_eligible_nodes_excludes_quarantined_or_allocated(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    port.quarantine_node({"name": "w-01", "reason": "test quarantine"})
    result = port.list_eligible_nodes({})
    assert result.value["nodes"] == []


def test_get_node_health_reports_lifecycle_and_runtime_state(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({"name": "w-01"})
    assert result.ok is True
    assert result.value["lifecycle_state"] == "active"
    assert result.value["runtime_state"] in {"running", "shutoff", "shut_off", "paused", "unknown"}
    assert "observation" in result.value
    validate_document("health-observation", result.value["observation"])


def test_get_node_health_missing_node_refuses_without_fabricating(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({"name": "does-not-exist"})
    assert result.ok is False
    assert result.disposition == "refused"
    assert result.refusal_code == RefusalCode.NODE_NOT_FOUND


def test_get_node_health_missing_name_field_is_validation_error(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({})
    assert result.refusal_code == RefusalCode.VALIDATION_ERROR


def test_reserve_and_release_node_lifecycle(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    reserve_res = port.reserve_node(ReserveNodeRequest(
        assignment_id=new_id("asn"),
        capability_requirements=["python3.12"],
        freshness_limit_seconds=60,
        idempotency_key="key-reserve-1",
    ))
    assert reserve_res.ok is True
    assert reserve_res.disposition == "completed"
    alloc = reserve_res.value
    validate_document("node-allocation", alloc)
    assert alloc["allocation_phase"] == "reserved"

    # Second reserve fails since node is reserved
    reserve_res2 = port.reserve_node(ReserveNodeRequest(
        assignment_id=new_id("asn"),
        capability_requirements=["python3.12"],
        freshness_limit_seconds=60,
        idempotency_key="key-reserve-2",
    ))
    assert reserve_res2.ok is False
    assert reserve_res2.refusal_code == RefusalCode.NO_ELIGIBLE_NODE

    # Release node
    rel_res = port.release_node({"allocation_id": alloc["id"]})
    assert rel_res.ok is True
    assert rel_res.value["allocation_phase"] == "released"

    # Now eligible again
    eligible = port.list_eligible_nodes({})
    assert any(n["name"] == "w-01" for n in eligible.value["nodes"])


def test_request_execution_and_get_and_collect(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    reserve_res = port.reserve_node(ReserveNodeRequest(
        assignment_id=new_id("asn"),
        capability_requirements=["python3.12"],
        freshness_limit_seconds=60,
        idempotency_key="key-exec-1",
    ))
    alloc = reserve_res.value

    envelope = {
        "schema": "ucc.execution-request",
        "schema_version": 1,
        "allocation_id": alloc["id"],
        "node_id": alloc["node_id"],
        "input_kind": "published_artifact_revision",
        "input_ref": {
            "kind": "artifact_revision",
            "id": new_id("rev"),
            "content_hash": "sha256:" + "0" * 64,
        },
        "entrypoint": "run.sh",
        "args": ["--mode", "test"],
    }
    exec_res = port.request_execution(ExecutionRequestEnvelope(
        document=envelope,
        idempotency_key="key-exec-req-1",
    ))
    assert exec_res.ok is True
    exec_doc = exec_res.value
    validate_document("execution", exec_doc)
    assert exec_doc["outcome"] == "succeeded"

    # Get execution
    get_res = port.get_execution({"execution_id": exec_doc["id"]})
    assert get_res.ok is True
    assert get_res.value["id"] == exec_doc["id"]

    # Collect handback
    hb_res = port.collect_handback(CollectHandbackRequest(
        execution_id=exec_doc["id"],
        idempotency_key="key-hb-1",
    ))
    assert hb_res.ok is True
    hb_doc = hb_res.value
    validate_document("handback", hb_doc)
    assert hb_doc["execution_id"] == exec_doc["id"]


def test_cancel_execution(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    reserve_res = port.reserve_node(ReserveNodeRequest(
        assignment_id=new_id("asn"),
        capability_requirements=["python3.12"],
        freshness_limit_seconds=60,
        idempotency_key="key-cancel-1",
    ))
    alloc = reserve_res.value

    envelope = {
        "schema": "ucc.execution-request",
        "schema_version": 1,
        "allocation_id": alloc["id"],
        "node_id": alloc["node_id"],
        "input_kind": "published_artifact_revision",
        "input_ref": {
            "kind": "artifact_revision",
            "id": new_id("rev"),
            "content_hash": "sha256:" + "0" * 64,
        },
        "entrypoint": "run.sh",
    }
    exec_res = port.request_execution(ExecutionRequestEnvelope(
        document=envelope,
        idempotency_key="key-cancel-req-1",
    ))
    exec_doc = exec_res.value

    cancel_res = port.cancel_execution({"execution_id": exec_doc["id"]})
    assert cancel_res.ok is True
    assert cancel_res.value["status"] in {"already_terminal", "cancel_requested"}


def test_quarantine_node_and_refusals(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    q_res = port.quarantine_node({"name": "w-01", "reason": "Compromise detected"})
    assert q_res.ok is True
    q_doc = q_res.value
    validate_document("quarantine", q_doc)
    assert q_doc["quarantine_state"] == "quarantined"

    # Trying to reserve quarantined node refuses with NODE_QUARANTINED
    reserve_res = port.reserve_node(ReserveNodeRequest(
        assignment_id=new_id("asn"),
        capability_requirements=[],
        freshness_limit_seconds=60,
        idempotency_key="k-q-1",
        preferred_node_id="w-01",
    ))
    assert reserve_res.ok is False
    assert reserve_res.refusal_code in {RefusalCode.NODE_QUARANTINED, RefusalCode.NO_ELIGIBLE_NODE}


def test_s2_3_transfers_and_credential_leases(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    
    # Transfer to node
    xfer_res = port.transfer_to_node({
        "name": "w-01",
        "source_path": "staging/payload.tar.gz",
        "destination_path": "payloads/payload.tar.gz",
        "content": b"payload-bytes-12345",
    })
    assert xfer_res.ok is True
    validate_document("transfer", xfer_res.value["transfer"])
    validate_document("transfer-receipt", xfer_res.value["receipt"])

    # Host-key probe and approve
    probe = port.probe_host_key({"name": "w-01"})
    assert probe.ok is True
    approve = port.approve_host_key({"name": "w-01", "key": probe.value["key"]})
    assert approve.ok is True

    # Credential lease and successful cleanup
    lease_res = port.create_credential_lease({
        "name": "w-01",
        "credential_ref": "git:deploy-key:repo1",
        "target_path": "credentials/deploy.key",
    })
    assert lease_res.ok is True
    validate_document("credential-lease", lease_res.value)
    lease_id = lease_res.value["id"]

    clean_res = port.cleanup_credential_lease({"lease_id": lease_id})
    assert clean_res.ok is True
    assert clean_res.value["lease_phase"] == "closed"
    assert clean_res.value["cleanup_evidence"]["verified"] is True

    # Failed cleanup triggers quarantine!
    lease2_res = port.create_credential_lease({
        "name": "w-01",
        "credential_ref": "git:deploy-key:repo2",
        "target_path": "credentials/deploy2.key",
    })
    lease2_id = lease2_res.value["id"]
    fail_clean = port.cleanup_credential_lease({"lease_id": lease2_id, "force_failure": True})
    assert fail_clean.ok is True
    assert fail_clean.value["lease_phase"] == "quarantined"


def test_reset_node_real_behavior(engine, ready_node):
    engine.assign("w-01", repo_url="https://example.com/x.git")
    engine.collect("w-01", remote_outbox_dir=Path("/home/agent/outbox"))
    port = VMFactoryFactoryPort(engine)
    result = port.reset_node({"name": "w-01"})
    assert result.ok is True
    assert result.value["state"] == "ready"


def test_reset_node_missing_snapshot_fails_not_refuses(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    result = port.reset_node({"name": "w-01"})
    assert result.ok is False
    assert result.disposition == "failed"


def test_adapter_never_calls_fenced_string_exec_or_assign():
    import ast
    import inspect
    from library import factory_port
    tree = ast.parse(inspect.getsource(factory_port))
    called_attrs = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "assign" not in called_attrs
    assert "run_cmd" not in called_attrs
