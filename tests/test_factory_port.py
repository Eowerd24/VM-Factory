"""G3: FactoryPort adapter conformance. All 10 methods must exist and be
Protocol-structural; the 3 with real behavior (list_eligible_nodes,
get_node_health, reset_node) are exercised against a real (mock-backed)
engine; the other 7 honestly refuse DEPENDENCY_UNAVAILABLE."""
from pathlib import Path

import yaml
import pytest

from library.engine import NodeLifecycleEngine
from library.factory_port import VMFactoryFactoryPort, build_factory_port
from library.models import NodeState
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
    assert {"name": "w-01", "type": "ai-worker"} in result.value["nodes"]


def test_list_eligible_nodes_excludes_non_ready(engine, ready_node):
    engine.assign("w-01", repo_url="https://example.com/x.git")  # ready -> assigned
    port = VMFactoryFactoryPort(engine)
    result = port.list_eligible_nodes({})
    assert result.value["nodes"] == []


def test_get_node_health_reports_lifecycle_and_runtime_state(engine, ready_node):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({"name": "w-01"})
    assert result.ok is True
    assert result.value["lifecycle_state"] == "ready"
    assert result.value["runtime_state"] in {"running", "shutoff", "paused", "unknown"}


def test_get_node_health_missing_node_refuses_without_fabricating(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({"name": "does-not-exist"})
    assert result.ok is False
    assert result.disposition == "refused"
    # ucc-contracts v0.2.0 (D6): typed now, not refusal_code=None.
    assert result.refusal_code == RefusalCode.NODE_NOT_FOUND


def test_get_node_health_missing_name_field_is_validation_error(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.get_node_health({})
    assert result.refusal_code == RefusalCode.VALIDATION_ERROR


def test_reset_node_real_behavior(engine, ready_node):
    # reset() transitions reporting -> ready; reaching "reporting" requires
    # the full assign -> collect flow (assigned -> reporting), matching
    # engine.reset()'s own state-machine precondition.
    engine.assign("w-01", repo_url="https://example.com/x.git")
    engine.collect("w-01", remote_outbox_dir=Path("/home/agent/outbox"))
    port = VMFactoryFactoryPort(engine)
    result = port.reset_node({"name": "w-01"})
    assert result.ok is True
    assert result.value["state"] == "ready"


def test_reset_node_missing_snapshot_fails_not_refuses(engine, ready_node):
    # w-01 is ready but was never assigned, so it has no sx-ready snapshot —
    # engine.reset() raises EngineError; the port must surface it as a
    # genuine operational failure, not a typed refusal it doesn't have.
    port = VMFactoryFactoryPort(engine)
    result = port.reset_node({"name": "w-01"})
    assert result.ok is False
    assert result.disposition == "failed"


@pytest.mark.parametrize("method,payload", [
    ("release_node", {"allocation_id": "nalloc_x"}),
    ("get_execution", {"execution_id": "exec_x"}),
    ("cancel_execution", {"execution_id": "exec_x"}),
    ("quarantine_node", {"node_id": "node_x"}),
])
def test_dict_methods_refuse_dependency_unavailable(engine, method, payload):
    port = VMFactoryFactoryPort(engine)
    result = getattr(port, method)(payload)
    assert result.ok is False
    assert result.disposition == "refused"
    assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE
    assert result.retryable is True


@pytest.mark.parametrize("method", [
    "release_node", "get_execution", "cancel_execution", "quarantine_node",
])
def test_dict_stub_methods_validate_before_refusing_dependency(engine, method):
    result = getattr(VMFactoryFactoryPort(engine), method)({})
    assert result.refusal_code == RefusalCode.VALIDATION_ERROR
    assert result.retryable is False


def test_reserve_node_refuses_dependency_unavailable(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.reserve_node(ReserveNodeRequest(
        assignment_id="asn_x", capability_requirements=[], freshness_limit_seconds=60,
        idempotency_key="k"))
    assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE


def test_request_execution_refuses_dependency_unavailable(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.request_execution(ExecutionRequestEnvelope(document={}, idempotency_key="k"))
    assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE


def test_collect_handback_refuses_dependency_unavailable(engine):
    port = VMFactoryFactoryPort(engine)
    result = port.collect_handback(CollectHandbackRequest(execution_id="exec_x", idempotency_key="k"))
    assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE


def test_adapter_never_calls_fenced_string_exec_or_assign():
    """Static guard alongside tests/test_string_exec_fence.py: the port
    adapter's actual call sites (not its explanatory docstring prose) must
    never invoke the fenced legacy path."""
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
