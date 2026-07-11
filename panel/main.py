import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from library.engine import NodeLifecycleEngine, EngineError
from library.models import NodeType, NodeState
from library.hypervisor import LibvirtHypervisorBackend, MockHypervisorBackend
from library.transport import SSHTransportBackend, MockTransportBackend

app = FastAPI(title="NodePanel", description="Node Lifecycle Dashboard")

# Paths
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Static files mount
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def get_engine() -> NodeLifecycleEngine:
    state_dir_str = os.environ.get("NODEFACTORY_STATE", "~/.local/state/nodefactory")
    state_dir = Path(state_dir_str).expanduser().resolve()

    # Check if mock mode is active
    if os.environ.get("MOCK_SSH", "").lower() in ("true", "1") or not Path("/var/run/libvirt/libvirt-sock").exists():
        # Fallback to mock backend if libvirt is missing or MOCK_SSH is set
        hypervisor = MockHypervisorBackend(state_file=state_dir / "mock_hypervisor.json")
        transport = MockTransportBackend()
    else:
        hypervisor = LibvirtHypervisorBackend()
        transport = SSHTransportBackend()

    return NodeLifecycleEngine(
        state_dir=state_dir,
        hypervisor=hypervisor,
        transport=transport,
        actor="panel"
    )

def list_nodes_manifests(engine: NodeLifecycleEngine):
    if not engine.nodes_dir.exists():
        return []
    nodes = []
    for p in engine.nodes_dir.iterdir():
        manifest_file = p / "node.yaml"
        if manifest_file.exists():
            try:
                from library.manifest import ManifestManager
                m = ManifestManager.load(manifest_file)
                nodes.append(m)
            except Exception:
                pass
    return sorted(nodes, key=lambda n: n.name)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    engine = get_engine()
    nodes = list_nodes_manifests(engine)
    records = list(engine.ledger.stream())[-15:]  # last 15 ledger entries
    records.reverse()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "nodes": nodes,
            "ledger": records,
            "node_types": [t.value for t in NodeType],
            "node_states": [s.value for s in NodeState]
        }
    )

@app.get("/nodes/refresh", response_class=HTMLResponse)
async def refresh_nodes(request: Request):
    engine = get_engine()
    nodes = list_nodes_manifests(engine)
    return templates.TemplateResponse(
        request=request,
        name="partials/node_list.html",
        context={"nodes": nodes}
    )

@app.get("/ledger/refresh", response_class=HTMLResponse)
async def refresh_ledger(request: Request):
    engine = get_engine()
    records = list(engine.ledger.stream())[-15:]
    records.reverse()
    return templates.TemplateResponse(
        request=request,
        name="partials/ledger_list.html",
        context={"ledger": records}
    )

@app.post("/nodes/create")
async def create_node(
    name: str = Form(...),
    node_type: str = Form(...),
    image: str = Form(...),
    vcpu: int = Form(...),
    ram_gb: int = Form(...),
    disk_gb: int = Form(...)
):
    engine = get_engine()
    # Create a temporary project yaml config based on form
    temp_yaml = engine.state_dir / f"temp_proj_{name}.yaml"
    temp_yaml.parent.mkdir(parents=True, exist_ok=True)

    config_data = {
        "repo": "",
        "image": image,
        "node_type": node_type,
        "resources": {
            "vcpu": vcpu,
            "ram_gb": ram_gb,
            "disk_gb": disk_gb
        },
        "branch_prefix": "ai/task",
        "credential_template": {
            "scopes": ["contents:rw", "pull_requests:rw"],
            "ttl_days": 14
        }
    }

    import yaml
    with open(temp_yaml, "w") as f:
        yaml.safe_dump(config_data, f)

    try:
        engine.create(name, temp_yaml)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_yaml.exists():
            temp_yaml.unlink()

    return RedirectResponse("/", status_code=303)

@app.post("/nodes/assign")
async def assign_node(
    name: str = Form(...),
    repo_url: str = Form(...),
    credential_id: Optional[str] = Form(None),
    node_ip: str = Form("127.0.0.1")
):
    engine = get_engine()
    try:
        engine.assign(name, repo_url, credential_id, node_ip)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=303)

@app.post("/nodes/collect/{name}")
async def collect_node(
    name: str,
    outbox_dir: str = Form("/home/agent/outbox"),
    node_ip: str = Form("127.0.0.1")
):
    engine = get_engine()
    try:
        engine.collect(name, Path(outbox_dir), node_ip)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=303)

@app.post("/nodes/reset/{name}")
async def reset_node(name: str):
    engine = get_engine()
    try:
        engine.reset(name)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=303)

@app.post("/nodes/destroy/{name}")
async def destroy_node(name: str):
    engine = get_engine()
    try:
        engine.destroy(name)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=303)
