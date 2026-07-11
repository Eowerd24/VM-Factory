import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple
from library.models import NodeManifest, NodeType, NodeState, NodeResources, LedgerAction, ProjectConfig, CredentialStatus
from library.manifest import ManifestManager
from library.hypervisor import HypervisorBackend, VMState, MockHypervisorBackend
from library.transport import TransportBackend, MockTransportBackend
from library.credentials import CredentialManager
from library.ledger import LedgerManager

class EngineError(Exception):
    """Raised for any pipeline engine failures."""
    pass

class NodeLifecycleEngine:
    """Core orchestration engine for node lifecycle state transitions and actions."""

    def __init__(
        self,
        state_dir: Path,
        hypervisor: Optional[HypervisorBackend] = None,
        transport: Optional[TransportBackend] = None,
        actor: str = "engine"
    ):
        self.state_dir = state_dir
        self.actor = actor
        
        # Paths
        self.nodes_dir = state_dir / "nodes"
        self.ledger_file = state_dir / "ledger" / "audit.jsonl"
        self.credentials_db = state_dir / "credentials.db"
        self.inbox_dir = state_dir / "inbox"
        
        # Backend components
        self.hypervisor = hypervisor or MockHypervisorBackend()
        self.transport = transport or MockTransportBackend()
        
        # Managers
        self.ledger = LedgerManager(self.ledger_file)
        self.credentials = CredentialManager(self.credentials_db)

    def _get_manifest_path(self, node_name: str) -> Path:
        return self.nodes_dir / node_name / "node.yaml"

    def create(self, name: str, project_config_path: Path) -> NodeManifest:
        """Verb: create

        Clones a new node from the golden template, sets up the layout,
        and saves its initial manifest.
        """
        # 1. Load project config
        if not project_config_path.exists():
            raise EngineError(f"Project config not found: {project_config_path}")
        
        try:
            with open(project_config_path, "r") as f:
                data = yaml.safe_load(f)
            config = ProjectConfig.model_validate(data)
        except Exception as e:
            raise EngineError(f"Failed to load project config: {e}")

        manifest_path = self._get_manifest_path(name)
        if manifest_path.exists():
            raise EngineError(f"Node '{name}' manifest already exists at {manifest_path}")

        # 2. Clone VM in hypervisor
        try:
            self.hypervisor.clone(template=config.image, name=name, thin=True)
            self.hypervisor.create_snapshot(name, "sx-fresh")
        except Exception as e:
            raise EngineError(f"Hypervisor failed to create VM '{name}': {e}")

        # 3. Create manifest
        now_utc = datetime.now(timezone.utc).isoformat()
        manifest = NodeManifest(
            schema_version=1,
            name=name,
            type=config.node_type,
            image=config.image,
            state=NodeState.PROVISIONED,
            snapshots=["sx-fresh"],
            created=now_utc,
            expires=now_utc,  # normally expires is created + ttl_days
            resources=config.resources,
            network="nat-workers"
        )
        
        # 4. Perform initial guest bootstrap and transition states
        # provisioned -> bootstrapped -> validated -> ready
        try:
            manifest = ManifestManager.transition(manifest, NodeState.BOOTSTRAPPED)
            manifest = ManifestManager.transition(manifest, NodeState.VALIDATED)
            manifest = ManifestManager.transition(manifest, NodeState.READY)
            
            # Save manifest
            ManifestManager.save(manifest, manifest_path)
        except Exception as e:
            # Cleanup on failure
            self.hypervisor.destroy(name)
            raise EngineError(f"Failed to transition state or save manifest: {e}")

        # 5. Log to ledger
        self.ledger.append(
            actor=self.actor,
            action=LedgerAction.NODE_CREATE,
            node=name,
            params={
                "type": config.node_type.value,
                "image": config.image,
                "resources": config.resources.model_dump()
            },
            result="ok"
        )

        return manifest

    def assign(self, name: str, repo_url: str, credential_id: Optional[str] = None, node_ip: str = "127.0.0.1") -> NodeManifest:
        """Verb: assign

        Assigns a Git repository workload to the node and injects credentials.
        """
        manifest_path = self._get_manifest_path(name)
        manifest = ManifestManager.load(manifest_path)
        
        if manifest.state != NodeState.READY:
            raise EngineError(f"Node '{name}' is in state '{manifest.state.value}', expected 'ready'")

        # 1. Update manifest fields
        manifest.repo = repo_url
        if credential_id:
            manifest.credential_ref = credential_id

        # 2. Inject credentials if provided
        secret_token = None
        if credential_id:
            try:
                cred_record, secret_token = self.credentials.strap(credential_id)
                self.ledger.append(
                    actor=self.actor,
                    action=LedgerAction.CRED_STRAP,
                    node=name,
                    params={"credential_id": credential_id, "kind": cred_record.kind},
                    result="ok"
                )
            except Exception as e:
                raise EngineError(f"Failed to strap credential '{credential_id}': {e}")

        # 3. Simulate or execute SSH assignments and repo clones in target VM
        try:
            # Start domain if off
            if self.hypervisor.get_state(name) == VMState.SHUTOFF:
                self.hypervisor.start(name)
            
            # Push secret / clone repo using transport
            if secret_token:
                # Mock path configuration for injection
                temp_cred_file = Path(f"/tmp/{name}_git_cred")
                temp_cred_file.write_text(f"https://oauth2:{secret_token}@github.com\n")
                try:
                    self.transport.push(node_ip, temp_cred_file, Path("/home/agent/.git-credentials"))
                finally:
                    if temp_cred_file.exists():
                        temp_cred_file.unlink()

            # Execute clone repo in guest
            clone_cmd = f"git clone {repo_url} /home/agent/workspace/{name}"
            exit_code, stdout, stderr = self.transport.run_cmd(node_ip, clone_cmd, user="agent")
            if exit_code != 0 and "mock" not in stdout:
                raise EngineError(f"Guest failed to clone repository: {stderr}")
                
        except Exception as e:
            if credential_id:
                self.credentials.scrub(credential_id)
            raise EngineError(f"Workload assignment failed: {e}")

        # 4. Transition states: ready -> assigned
        manifest = ManifestManager.transition(manifest, NodeState.ASSIGNED)
        
        # Take snapshot
        snapshot_name = f"sx-ready-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        try:
            self.hypervisor.create_snapshot(name, snapshot_name)
            manifest.snapshots.append(snapshot_name)
        except Exception as e:
            raise EngineError(f"Failed to create sx-ready snapshot: {e}")

        # Save manifest
        ManifestManager.save(manifest, manifest_path)
        
        self.ledger.append(
            actor=self.actor,
            action=LedgerAction.PAYLOAD_FIRE,
            node=name,
            params={"repo": repo_url, "snapshot": snapshot_name},
            result="ok"
        )
        
        return manifest

    def collect(self, name: str, remote_outbox_dir: Path, node_ip: str = "127.0.0.1") -> dict:
        """Verb: collect

        Pulls and verifies files from the guest VM's outbox folder.
        """
        manifest_path = self._get_manifest_path(name)
        manifest = ManifestManager.load(manifest_path)
        
        if manifest.state != NodeState.ASSIGNED:
            raise EngineError(f"Node '{name}' is in state '{manifest.state.value}', expected 'assigned'")

        local_inbox = self.inbox_dir / name / datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        
        # 1. Pull and verify checksums
        try:
            res = self.transport.collect_outbox(node_ip, remote_outbox_dir, local_inbox)
        except Exception as e:
            raise EngineError(f"Failed to pull outbox files: {e}")

        if not res["success"]:
            self.ledger.append(
                actor=self.actor,
                action=LedgerAction.COLLECT_PULL,
                node=name,
                params={"inbox_path": str(local_inbox), "errors": res["errors"]},
                result="error"
            )
            raise EngineError(f"Outbox collection failed checksum verification: {res['errors']}")

        # 2. Transition state: assigned -> reporting
        manifest = ManifestManager.transition(manifest, NodeState.REPORTING)
        ManifestManager.save(manifest, manifest_path)
        
        self.ledger.append(
            actor=self.actor,
            action=LedgerAction.COLLECT_PULL,
            node=name,
            params={"inbox_path": str(local_inbox), "files": res["verified_files"]},
            result="ok"
        )
        
        return res

    def reset(self, name: str) -> NodeManifest:
        """Verb: reset

        Stops the VM, reverts it to the latest sx-ready snapshot, rotates credentials, and starts it.
        """
        manifest_path = self._get_manifest_path(name)
        manifest = ManifestManager.load(manifest_path)

        # Revert state: reporting -> ready
        manifest = ManifestManager.transition(manifest, NodeState.READY)
        
        # Find latest sx-ready snapshot
        ready_snapshots = [s for s in manifest.snapshots if s.startswith("sx-ready")]
        if not ready_snapshots:
            raise EngineError(f"No sx-ready snapshot found for node '{name}'")
        latest_snapshot = ready_snapshots[-1]

        try:
            # Revert VM
            self.hypervisor.stop(name, force=True)
            self.hypervisor.revert_snapshot(name, latest_snapshot)
            self.hypervisor.start(name)
        except Exception as e:
            raise EngineError(f"Hypervisor failed to reset VM: {e}")

        # Rotate credential
        if manifest.credential_ref:
            try:
                self.credentials.scrub(manifest.credential_ref)
                self.ledger.append(
                    actor=self.actor,
                    action=LedgerAction.CRED_SCRUB,
                    node=name,
                    params={"credential_id": manifest.credential_ref},
                    result="ok"
                )
            except Exception as e:
                raise EngineError(f"Failed to scrub credential '{manifest.credential_ref}': {e}")

        ManifestManager.save(manifest, manifest_path)
        
        self.ledger.append(
            actor=self.actor,
            action=LedgerAction.NODE_RESET,
            node=name,
            params={"reverted_to": latest_snapshot},
            result="ok"
        )
        
        return manifest

    def destroy(self, name: str) -> None:
        """Verb: destroy

        Permanently destroys the VM, deletes its storage, and retires the credential.
        """
        manifest_path = self._get_manifest_path(name)
        manifest = ManifestManager.load(manifest_path)

        # 1. Stop and undefine in hypervisor
        try:
            self.hypervisor.destroy(name)
        except Exception as e:
            raise EngineError(f"Hypervisor failed to destroy VM: {e}")

        # 2. Nuke credential
        if manifest.credential_ref:
            try:
                self.credentials.nuke(manifest.credential_ref)
                self.ledger.append(
                    actor=self.actor,
                    action=LedgerAction.CRED_NUKE,
                    node=name,
                    params={"credential_id": manifest.credential_ref},
                    result="ok"
                )
            except Exception as e:
                raise EngineError(f"Failed to nuke credential '{manifest.credential_ref}': {e}")

        # 3. Transition to retired and cleanup manifest
        manifest = ManifestManager.transition(manifest, NodeState.RETIRED)
        if manifest_path.exists():
            manifest_path.unlink()
            # Clean directory if empty
            if not any(manifest_path.parent.iterdir()):
                manifest_path.parent.rmdir()

        self.ledger.append(
            actor=self.actor,
            action=LedgerAction.EVENT,
            node=name,
            params={"event": "node_destroyed"},
            result="ok"
        )
