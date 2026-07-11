import os
import sys
from pathlib import Path
from typing import Optional
import typer
from library.engine import NodeLifecycleEngine, EngineError
from library.models import NodeType, NodeState
from library.hypervisor import LibvirtHypervisorBackend, MockHypervisorBackend
from library.transport import SSHTransportBackend, MockTransportBackend

app = typer.Typer(
    name="nodectl",
    help="CLI tool for the Node Lifecycle Pipeline ('bootstrap to retire')",
    no_args_is_help=True
)

def get_engine(mock: bool = False) -> NodeLifecycleEngine:
    state_dir_str = os.environ.get("NODEFACTORY_STATE", "~/.local/state/nodefactory")
    state_dir = Path(state_dir_str).expanduser().resolve()

    if mock or os.environ.get("MOCK_SSH", "").lower() in ("true", "1"):
        hypervisor = MockHypervisorBackend(state_file=state_dir / "mock_hypervisor.json")
        transport = MockTransportBackend()
        typer.secho("Using Mock backends (MOCK_SSH is active)", fg=typer.colors.YELLOW, dim=True)
    else:
        hypervisor = LibvirtHypervisorBackend()
        transport = SSHTransportBackend()

    return NodeLifecycleEngine(
        state_dir=state_dir,
        hypervisor=hypervisor,
        transport=transport,
        actor=os.environ.get("USER", "cli")
    )

@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the node to create"),
    project_config: Path = typer.Argument(..., help="Path to project config YAML file"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Clones a new node from the golden template, sets up the layout,
    and saves its initial manifest.
    """
    engine = get_engine(mock)
    try:
        typer.echo(f"Creating node '{name}' using project config {project_config}...")
        manifest = engine.create(name, project_config)
        typer.secho(f"Successfully created node '{name}' in state '{manifest.state.value}'.", fg=typer.colors.GREEN)
        typer.echo(f"Manifest saved to {engine._get_manifest_path(name)}")
    except EngineError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

@app.command()
def assign(
    name: str = typer.Argument(..., help="Name of the node"),
    repo_url: str = typer.Argument(..., help="Git repository URL to assign"),
    credential_id: Optional[str] = typer.Option(None, "--cred-id", "-c", help="Credential ID from vault"),
    node_ip: str = typer.Option("127.0.0.1", "--ip", help="IP address of the node"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Assigns a Git repository workload to the node and injects credentials.
    """
    engine = get_engine(mock)
    try:
        typer.echo(f"Assigning workload '{repo_url}' to node '{name}'...")
        manifest = engine.assign(name, repo_url, credential_id, node_ip)
        typer.secho(f"Successfully assigned workload to '{name}'. State: '{manifest.state.value}'.", fg=typer.colors.GREEN)
    except EngineError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

@app.command()
def collect(
    name: str = typer.Argument(..., help="Name of the node"),
    outbox_dir: Path = typer.Argument(Path("/home/agent/outbox"), help="Path to the remote outbox directory"),
    node_ip: str = typer.Option("127.0.0.1", "--ip", help="IP address of the node"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Pulls and verifies files from the guest VM's outbox folder.
    """
    engine = get_engine(mock)
    try:
        typer.echo(f"Collecting outbox files from node '{name}'...")
        res = engine.collect(name, outbox_dir, node_ip)
        if res["success"]:
            typer.secho("Collection successful!", fg=typer.colors.GREEN)
            typer.echo(f"Files verified: {res['verified_files']}")
            typer.echo(f"Collected at: {res['ts']}")
        else:
            typer.secho("Collection failed validation checks.", fg=typer.colors.RED)
            for err in res["errors"]:
                typer.echo(f"- {err}", err=True)
            sys.exit(1)
    except EngineError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

@app.command()
def reset(
    name: str = typer.Argument(..., help="Name of the node"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Stops the VM, reverts it to the latest sx-ready snapshot, rotates credentials, and starts it.
    """
    engine = get_engine(mock)
    try:
        typer.echo(f"Resetting node '{name}'...")
        manifest = engine.reset(name)
        typer.secho(f"Successfully reset node '{name}'. State: '{manifest.state.value}'.", fg=typer.colors.GREEN)
    except EngineError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

@app.command()
def destroy(
    name: str = typer.Argument(..., help="Name of the node to destroy"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Permanently destroys the VM, deletes its storage, and retires the credential.
    """
    engine = get_engine(mock)
    try:
        typer.echo(f"Destroying node '{name}'...")
        engine.destroy(name)
        typer.secho(f"Successfully destroyed node '{name}'.", fg=typer.colors.GREEN)
    except EngineError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

@app.command("list")
def list_nodes(
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    List all node manifests in the state directory.
    """
    engine = get_engine(mock)
    if not engine.nodes_dir.exists():
        typer.echo("No nodes found.")
        return

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

    if not nodes:
        typer.echo("No active node manifests found.")
        return

    typer.echo(f"{'NAME':<20} {'TYPE':<20} {'STATE':<15} {'EXPIRES':<25}")
    typer.echo("-" * 80)
    for m in nodes:
        typer.echo(f"{m.name:<20} {m.type.value:<20} {m.state.value:<15} {m.expires:<25}")

@app.command()
def ledger(
    node: Optional[str] = typer.Option(None, "--node", "-n", help="Filter by node name"),
    action: Optional[str] = typer.Option(None, "--action", "-a", help="Filter by action name"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Filter by actor name"),
    mock: bool = typer.Option(False, "--mock", help="Use mock hypervisor/transport")
):
    """
    Query and stream ledger audit logs.
    """
    from library.models import LedgerAction
    engine = get_engine(mock)
    ledger_action = None
    if action:
        try:
            ledger_action = LedgerAction(action)
        except ValueError:
            typer.secho(f"Invalid ledger action '{action}'. Options: {[a.value for a in LedgerAction]}", fg=typer.colors.RED, err=True)
            sys.exit(1)

    try:
        records = engine.ledger.query(node=node, action=ledger_action, actor=actor)
        if not records:
            typer.echo("No matching ledger records found.")
            return

        typer.echo(f"{'TIMESTAMP':<25} {'ACTOR':<10} {'ACTION':<15} {'NODE':<15} {'RESULT':<10}")
        typer.echo("-" * 80)
        for r in records:
            typer.echo(f"{r.ts:<25} {r.actor:<10} {r.action.value:<15} {r.node:<15} {r.result:<10}")
    except Exception as e:
        typer.secho(f"Error reading ledger: {e}", fg=typer.colors.RED, err=True)
        sys.exit(1)

if __name__ == "__main__":
    app()
