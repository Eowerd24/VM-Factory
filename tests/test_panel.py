import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from panel.main import app

@pytest.fixture(autouse=True)
def setup_mock_env(tmp_path):
    # Route all state data to a temporary directory during testing
    os.environ["NODEFACTORY_STATE"] = str(tmp_path)
    os.environ["MOCK_SSH"] = "true"
    yield
    # Cleanup
    if "NODEFACTORY_STATE" in os.environ:
        del os.environ["NODEFACTORY_STATE"]
    if "MOCK_SSH" in os.environ:
        del os.environ["MOCK_SSH"]

def test_index_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "NodePanel" in response.text
    assert "Active Fleet" in response.text
    assert "Audit Trail" in response.text

def test_refresh_routes():
    client = TestClient(app)

    # Refresh nodes
    resp_nodes = client.get("/nodes/refresh")
    assert resp_nodes.status_code == 200
    assert "No active nodes found" in resp_nodes.text

    # Refresh ledger
    resp_ledger = client.get("/ledger/refresh")
    assert resp_ledger.status_code == 200
    assert "No audit log records available" in resp_ledger.text

def test_node_lifecycle_routes():
    client = TestClient(app)

    # 1. Create a node
    create_data = {
        "name": "panel-test-node",
        "node_type": "ai-worker",
        "image": "gold-server-2404-v1",
        "vcpu": 2,
        "ram_gb": 4,
        "disk_gb": 20
    }
    resp_create = client.post("/nodes/create", data=create_data)
    assert resp_create.status_code in (200, 303)

    # Verify node exists in refresh
    resp_nodes = client.get("/nodes/refresh")
    assert "panel-test-node" in resp_nodes.text

    # 2. Assign workload
    assign_data = {
        "name": "panel-test-node",
        "repo_url": "https://github.com/Eowerd24/VM-Factory.git",
        "credential_id": "",
        "node_ip": "127.0.0.1"
    }
    resp_assign = client.post("/nodes/assign", data=assign_data)
    assert resp_assign.status_code in (200, 303)

    # Verify repo is visible in card
    resp_nodes2 = client.get("/nodes/refresh")
    assert "VM-Factory.git" in resp_nodes2.text

    # Verify ledger entries are recorded
    resp_ledger = client.get("/ledger/refresh")
    assert "node.create" in resp_ledger.text
    assert "payload.fire" in resp_ledger.text

    # 3. Collect node (transitions assigned -> reporting)
    collect_data = {
        "outbox_dir": "/home/agent/outbox",
        "node_ip": "127.0.0.1"
    }
    resp_collect = client.post("/nodes/collect/panel-test-node", data=collect_data)
    assert resp_collect.status_code in (200, 303)

    # 4. Reset node (transitions reporting -> ready)
    resp_reset = client.post("/nodes/reset/panel-test-node")
    assert resp_reset.status_code in (200, 303)

    # 5. Destroy node (transitions ready -> retired)
    resp_destroy = client.post("/nodes/destroy/panel-test-node")
    assert resp_destroy.status_code in (200, 303)

    # Verify node is gone
    resp_nodes3 = client.get("/nodes/refresh")
    assert "panel-test-node" not in resp_nodes3.text
