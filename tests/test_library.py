import pytest
import tempfile
import yaml
import json
import os
import sys
from pathlib import Path
from library.models import (
    NodeManifest, NodeType, NodeState, NodeResources, LedgerAction,
    CredentialRecord, CredentialStatus, PayloadManifest, PayloadTier,
    Report, CheckResult, CheckStatus, ProjectConfig, CredentialTemplate
)
from library.manifest import ManifestManager, StateTransitionError
from library.ledger import LedgerManager
from library.credentials import CredentialManager, CredentialError
from library.payloads import PayloadValidator, PayloadValidationError
from library.reports import ReportParser
from library.engine import NodeLifecycleEngine, EngineError
from library.hypervisor import MockHypervisorBackend, VMState
from library.transport import MockTransportBackend

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def sample_manifest():
    return NodeManifest(
        schema_version=1,
        name="test-node-01",
        type=NodeType.AI_WORKER,
        image="gold-server-2404-v1",
        state=NodeState.PROVISIONED,
        snapshots=[],
        created="2026-07-11T12:00:00Z",
        expires="2026-08-11T12:00:00Z",
        resources=NodeResources(vcpu=2, ram_gb=4, disk_gb=20),
        network="nat-workers"
    )

def test_manifest_save_and_load(temp_dir, sample_manifest):
    manifest_path = temp_dir / "node.yaml"

    # Save
    ManifestManager.save(sample_manifest, manifest_path)
    assert manifest_path.exists()

    # Load
    loaded = ManifestManager.load(manifest_path)
    assert loaded.name == sample_manifest.name
    assert loaded.type == sample_manifest.type
    assert loaded.resources.vcpu == sample_manifest.resources.vcpu

def test_manifest_valid_transitions(sample_manifest):
    # provisioned -> bootstrapped
    m2 = ManifestManager.transition(sample_manifest, NodeState.BOOTSTRAPPED)
    assert m2.state == NodeState.BOOTSTRAPPED

    # bootstrapped -> validated
    m3 = ManifestManager.transition(m2, NodeState.VALIDATED)
    assert m3.state == NodeState.VALIDATED

    # validated -> ready
    m4 = ManifestManager.transition(m3, NodeState.READY)
    assert m4.state == NodeState.READY

    # ready -> assigned
    m5 = ManifestManager.transition(m4, NodeState.ASSIGNED)
    assert m5.state == NodeState.ASSIGNED

    # assigned -> reporting
    m6 = ManifestManager.transition(m5, NodeState.REPORTING)
    assert m6.state == NodeState.REPORTING

    # reporting -> ready (e.g. after reset)
    m7 = ManifestManager.transition(m6, NodeState.READY)
    assert m7.state == NodeState.READY

def test_manifest_invalid_transitions(sample_manifest):
    # provisioned -> ready is invalid
    with pytest.raises(StateTransitionError):
        ManifestManager.transition(sample_manifest, NodeState.READY)

    # provisioned -> assigned is invalid
    with pytest.raises(StateTransitionError):
        ManifestManager.transition(sample_manifest, NodeState.ASSIGNED)

def test_manifest_retire_transition(sample_manifest):
    # provisioned -> retired is valid
    m_retired = ManifestManager.transition(sample_manifest, NodeState.RETIRED)
    assert m_retired.state == NodeState.RETIRED

def test_ledger_append_and_query(temp_dir):
    ledger_path = temp_dir / "ledger.jsonl"
    manager = LedgerManager(ledger_path)

    # Append
    rec1 = manager.append(
        actor="sarge",
        action=LedgerAction.NODE_CREATE,
        node="w-cliplib-01",
        params={"image": "gold-server-v1"},
        result="ok"
    )

    rec2 = manager.append(
        actor="panel",
        action=LedgerAction.PAYLOAD_FIRE,
        node="w-cliplib-01",
        params={"payload": "l2-ai-worker.sh"},
        result="ok"
    )

    assert ledger_path.exists()

    # Query all
    records = list(manager.stream())
    assert len(records) == 2
    assert records[0].actor == "sarge"
    assert records[1].actor == "panel"

    # Query specific
    create_records = manager.query(action=LedgerAction.NODE_CREATE)
    assert len(create_records) == 1
    assert create_records[0].node == "w-cliplib-01"


def test_credential_manager(temp_dir):
    db_path = temp_dir / "credentials.db"
    manager = CredentialManager(db_path)

    # Create
    cred = manager.create(
        cred_id="cred:test-pat",
        kind="github-pat-fine-grained",
        repo="you/cliplib",
        node="w-cliplib-01",
        last4="a9F2",
        expires="2026-07-26T12:00:00Z",
        scopes=["contents:rw", "pull_requests:rw"],
        vault_ref="mock:test-token"
    )
    assert cred.id == "cred:test-pat"
    assert cred.status == CredentialStatus.SCRUBBED

    # Get
    retrieved = manager.get("cred:test-pat")
    assert retrieved is not None
    assert retrieved.repo == "you/cliplib"

    # Strap
    strapped, secret = manager.strap("cred:test-pat")
    assert strapped.status == CredentialStatus.STRAPPED
    assert strapped.strapped_at is not None
    assert secret == "ghp_mock_token_test-token"

    # Scrub
    scrubbed = manager.scrub("cred:test-pat")
    assert scrubbed.status == CredentialStatus.SCRUBBED
    assert scrubbed.strapped_at is None

    # Nuke
    nuked = manager.nuke("cred:test-pat")
    assert nuked.status == CredentialStatus.NUKED
    assert nuked.strapped_at is None


def test_payload_validator(temp_dir):
    payload_file = temp_dir / "test_payload.sh"
    payload_file.write_text("echo 'hello'")

    # Calculate sha256
    expected_sha = PayloadValidator.calculate_sha256(payload_file)
    assert len(expected_sha) == 64

    manifest = PayloadManifest(
        schema_version=1,
        name="test_payload.sh",
        sha256=expected_sha,
        tier=PayloadTier.APPROVED,
        allowed_node_types=[NodeType.AI_WORKER],
        allowed_states=[NodeState.BOOTSTRAPPED],
        approved_by="sarge",
        approved_at="2026-07-11T12:00:00Z"
    )

    # Valid validation
    PayloadValidator.validate(payload_file, manifest, NodeType.AI_WORKER, NodeState.BOOTSTRAPPED)

    # Invalid node type
    with pytest.raises(PayloadValidationError, match="is not allowed on node type"):
        PayloadValidator.validate(payload_file, manifest, NodeType.DEV_DESKTOP, NodeState.BOOTSTRAPPED)

    # Invalid node state
    with pytest.raises(PayloadValidationError, match="is not allowed in node state"):
        PayloadValidator.validate(payload_file, manifest, NodeType.AI_WORKER, NodeState.READY)

    # Draft tier gating on non-mock non-sandbox
    manifest_draft = manifest.model_copy(update={
        "tier": PayloadTier.DRAFT,
        "allowed_node_types": [NodeType.AI_WORKER, NodeType.RESEARCH_SANDBOX]
    })
    with pytest.raises(PayloadValidationError, match="can only run on mock backend or research-sandbox"):
        PayloadValidator.validate(payload_file, manifest_draft, NodeType.AI_WORKER, NodeState.BOOTSTRAPPED, is_mock=False)

    # Draft tier allowed on mock or sandbox
    PayloadValidator.validate(payload_file, manifest_draft, NodeType.AI_WORKER, NodeState.BOOTSTRAPPED, is_mock=True)
    PayloadValidator.validate(payload_file, manifest_draft, NodeType.RESEARCH_SANDBOX, NodeState.BOOTSTRAPPED, is_mock=False)


def test_report_parser(temp_dir):
    # Test report parsing
    report_file = temp_dir / "report.json"
    report_data = {
        "node": "w-cliplib-01",
        "ts": "2026-07-11T12:00:00Z",
        "kind": "pre",
        "checks": [
            {"id": "C1", "name": "CPU Check", "status": "pass", "detail": "4 cores available"},
            {"id": "C2", "name": "Disk Check", "status": "warn", "detail": "Low disk space"}
        ],
        "needs": ["libpq-dev"]
    }
    with open(report_file, "w") as f:
        json.dump(report_data, f)

    report = ReportParser.parse_report_json(report_file)
    assert report.node == "w-cliplib-01"
    assert len(report.checks) == 2
    assert report.checks[0].status == CheckStatus.PASS
    assert report.needs == ["libpq-dev"]

    # Test NEEDS.md parsing
    needs_file = temp_dir / "NEEDS.md"
    needs_file.write_text("""
    # Node Needs
    - need: libssl-dev
      need: sqlite3 # nested comment
    * need: python3-dev
    """)
    needs = ReportParser.parse_needs_md(needs_file)
    assert "libssl-dev" in needs
    assert "sqlite3" in needs
    assert "python3-dev" in needs

    # Test PROGRESS.md parsing
    progress_file = temp_dir / "PROGRESS.md"
    progress_file.write_text("""
    ## Completed Work
    - W-001 - Init repo
    - D-001 - Choose KVM
    - KI-002 - Snapshots issue
    - B-005 - Cleanup backlog
    """)
    ids = ReportParser.parse_progress_identifiers(progress_file)
    assert "W-001" in ids["work_items"]
    assert "D-001" in ids["decisions"]
    assert "KI-002" in ids["known_issues"]
    assert "B-005" in ids["backlog_items"]


def test_node_lifecycle_engine(temp_dir):
    engine = NodeLifecycleEngine(temp_dir)

    # 1. Create project config file
    config_path = temp_dir / "project.yaml"
    config_data = {
        "repo": "https://github.com/Eowerd24/VM-Factory.git",
        "image": "gold-server-2404-v1",
        "node_type": "ai-worker",
        "resources": {
            "vcpu": 2,
            "ram_gb": 4,
            "disk_gb": 20
        },
        "branch_prefix": "ai/test",
        "credential_template": {
            "scopes": ["contents:rw", "pull_requests:rw"],
            "ttl_days": 7
        },
        "env_refs": ["env:TEST_SECRET"]
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)

    # Create credential in engine DB
    engine.credentials.create(
        cred_id="cred:test-pat",
        kind="github-pat-fine-grained",
        repo="Eowerd24/VM-Factory",
        node="node-01",
        last4="a9F2",
        expires="2026-07-26T12:00:00Z",
        scopes=["contents:rw", "pull_requests:rw"],
        vault_ref="mock:test-token"
    )

    # 2. Verb: Create
    node_name = "node-01"
    manifest = engine.create(node_name, config_path)
    assert manifest.name == node_name
    assert manifest.state == NodeState.READY
    assert manifest.image == "gold-server-2404-v1"
    assert "sx-fresh" in manifest.snapshots

    # Check manifest file exists in engine state dir
    manifest_file = temp_dir / "nodes" / node_name / "node.yaml"
    assert manifest_file.exists()

    # Verify hypervisor VM created and snapshot taken
    assert node_name in engine.hypervisor.list_nodes()
    assert "sx-fresh" in engine.hypervisor.list_snapshots(node_name)

    # Verify ledger entry
    records = list(engine.ledger.stream())
    assert len(records) == 1
    assert records[0].action == LedgerAction.NODE_CREATE

    # 3. Verb: Assign
    manifest = engine.assign(node_name, repo_url=config_data["repo"], credential_id="cred:test-pat")
    assert manifest.state == NodeState.ASSIGNED
    assert manifest.repo == config_data["repo"]
    assert manifest.credential_ref == "cred:test-pat"
    # An sx-ready snapshot was created
    assert any(s.startswith("sx-ready") for s in manifest.snapshots)

    # Hypervisor state is running
    assert engine.hypervisor.get_state(node_name) == VMState.RUNNING

    # Verify ledger records
    records = list(engine.ledger.stream())
    assert len(records) == 3
    assert records[1].action == LedgerAction.CRED_STRAP
    assert records[2].action == LedgerAction.PAYLOAD_FIRE

    # 4. Verb: Collect
    remote_outbox = Path("/home/agent/outbox")
    res = engine.collect(node_name, remote_outbox)
    assert res["success"] is True
    assert "PROGRESS.md" in res["verified_files"]

    manifest = ManifestManager.load(manifest_file)
    assert manifest.state == NodeState.REPORTING

    records = list(engine.ledger.stream())
    assert len(records) == 4
    assert records[3].action == LedgerAction.COLLECT_PULL

    # 5. Verb: Reset
    manifest = engine.reset(node_name)
    assert manifest.state == NodeState.READY
    assert manifest.credential_ref == "cred:test-pat"
    # Credential should be scrubbed
    cred = engine.credentials.get("cred:test-pat")
    assert cred.status == CredentialStatus.SCRUBBED

    records = list(engine.ledger.stream())
    assert len(records) == 6
    assert records[4].action == LedgerAction.CRED_SCRUB
    assert records[5].action == LedgerAction.NODE_RESET

    # 6. Verb: Destroy
    tombstone = engine.destroy(node_name)
    # M-c: destruction preserves a tombstone (the retired manifest), it does
    # not delete the manifest file — locked invariant, UCC-Standards §15.
    assert manifest_file.exists()
    assert tombstone.state == NodeState.RETIRED
    assert ManifestManager.load(manifest_file).state == NodeState.RETIRED
    assert node_name not in engine.hypervisor.list_nodes()

    cred = engine.credentials.get("cred:test-pat")
    assert cred.status == CredentialStatus.NUKED

    records = list(engine.ledger.stream())
    assert len(records) == 8
    assert records[6].action == LedgerAction.CRED_NUKE
    assert records[7].action == LedgerAction.EVENT


def test_cli_help():
    from typer.testing import CliRunner
    from nodectl import app
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CLI tool for the Node Lifecycle Pipeline" in result.output


def test_cli_lifecycle(temp_dir):
    from typer.testing import CliRunner
    from nodectl import app
    os.environ["NODEFACTORY_STATE"] = str(temp_dir)
    runner = CliRunner()

    # 1. Create project config file
    config_path = temp_dir / "project.yaml"
    config_data = {
        "repo": "https://github.com/Eowerd24/VM-Factory.git",
        "image": "gold-server-2404-v1",
        "node_type": "ai-worker",
        "resources": {
            "vcpu": 2,
            "ram_gb": 4,
            "disk_gb": 20
        },
        "branch_prefix": "ai/test",
        "credential_template": {
            "scopes": ["contents:rw", "pull_requests:rw"],
            "ttl_days": 7
        },
        "env_refs": []
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)

    # 2. Invoke create command with mock flag
    result = runner.invoke(app, ["create", "node-cli-01", str(config_path), "--mock"])
    assert result.exit_code == 0
    assert "Successfully created node 'node-cli-01'" in result.output

    # 3. Invoke list command
    result = runner.invoke(app, ["list", "--mock"])
    assert result.exit_code == 0
    assert "node-cli-01" in result.output

    # 4. Invoke assign command
    result = runner.invoke(app, ["assign", "node-cli-01", config_data["repo"], "--mock"])
    assert result.exit_code == 0
    assert "Successfully assigned workload" in result.output

    # 5. Invoke ledger command
    result = runner.invoke(app, ["ledger", "--mock"])
    assert result.exit_code == 0
    assert "node-cli-01" in result.output
    assert "node.create" in result.output

    # 6. Invoke collect command
    result = runner.invoke(app, ["collect", "node-cli-01", "/home/agent/outbox", "--mock"])
    assert result.exit_code == 0
    assert "Collection successful!" in result.output

    # 7. Invoke reset command
    result = runner.invoke(app, ["reset", "node-cli-01", "--mock"])
    assert result.exit_code == 0
    assert "Successfully reset node 'node-cli-01'" in result.output

    # 8. Invoke destroy command
    result = runner.invoke(app, ["destroy", "node-cli-01", "--mock"])
    assert result.exit_code == 0
    assert "Successfully destroyed node 'node-cli-01'" in result.output
