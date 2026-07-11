import pytest
import tempfile
from pathlib import Path
from library.models import NodeManifest, NodeType, NodeState, NodeResources, LedgerAction
from library.manifest import ManifestManager, StateTransitionError
from library.ledger import LedgerManager

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
