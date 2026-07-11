import subprocess
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path

class VMState(str, Enum):
    RUNNING = "running"
    SHUTOFF = "shutoff"
    PAUSED = "paused"
    UNKNOWN = "unknown"

class HypervisorError(Exception):
    """Raised for any hypervisor command errors."""
    pass

class HypervisorBackend:
    """Base interface for KVM/libvirt hypervisor interactions."""

    def list_nodes(self) -> List[str]:
        raise NotImplementedError()

    def get_state(self, name: str) -> VMState:
        raise NotImplementedError()

    def clone(self, template: str, name: str, thin: bool = True) -> None:
        raise NotImplementedError()

    def start(self, name: str) -> None:
        raise NotImplementedError()

    def stop(self, name: str, force: bool = False) -> None:
        raise NotImplementedError()

    def destroy(self, name: str) -> None:
        raise NotImplementedError()

    def create_snapshot(self, name: str, snapshot_name: str) -> None:
        raise NotImplementedError()

    def revert_snapshot(self, name: str, snapshot_name: str) -> None:
        raise NotImplementedError()

    def delete_snapshot(self, name: str, snapshot_name: str) -> None:
        raise NotImplementedError()

    def list_snapshots(self, name: str) -> List[str]:
        raise NotImplementedError()


class LibvirtHypervisorBackend(HypervisorBackend):
    """Real hypervisor backend interacting with local libvirt via virsh/virt-clone."""

    def list_nodes(self) -> List[str]:
        try:
            out = subprocess.check_output(["virsh", "list", "--all", "--name"], text=True)
            return [line.strip() for line in out.splitlines() if line.strip()]
        except Exception as e:
            raise HypervisorError(f"Failed to list nodes: {e}")

    def get_state(self, name: str) -> VMState:
        try:
            out = subprocess.check_output(["virsh", "domstate", name], text=True).strip().lower()
            if "running" in out:
                return VMState.RUNNING
            elif "shut off" in out or "shutoff" in out:
                return VMState.SHUTOFF
            elif "paused" in out:
                return VMState.PAUSED
            return VMState.UNKNOWN
        except Exception as e:
            raise HypervisorError(f"Failed to get state for '{name}': {e}")

    def clone(self, template: str, name: str, thin: bool = True) -> None:
        cmd = ["virt-clone", "--original", template, "--name", name, "--auto-clone"]
        # In libvirt, thin (linked) clones are typically handled via qcow2 backing files,
        # virt-clone handles storage allocation, but to do true linked clones we often
        # create the qcow2 overlay file manually or let libvirt backing store handle it.
        # Here we map to virt-clone auto-clone as a baseline.
        try:
            subprocess.check_call(cmd)
        except Exception as e:
            raise HypervisorError(f"Failed to clone '{template}' to '{name}': {e}")

    def start(self, name: str) -> None:
        try:
            subprocess.check_call(["virsh", "start", name])
        except Exception as e:
            raise HypervisorError(f"Failed to start node '{name}': {e}")

    def stop(self, name: str, force: bool = False) -> None:
        cmd = ["virsh", "destroy" if force else "shutdown", name]
        try:
            subprocess.check_call(cmd)
        except Exception as e:
            raise HypervisorError(f"Failed to stop node '{name}': {e}")

    def destroy(self, name: str) -> None:
        # Destroys the VM and undefines it, wiping storage
        try:
            # First stop if running
            state = self.get_state(name)
            if state == VMState.RUNNING:
                subprocess.call(["virsh", "destroy", name])
            subprocess.check_call(["virsh", "undefine", name, "--remove-all-storage"])
        except Exception as e:
            raise HypervisorError(f"Failed to destroy node '{name}': {e}")

    def create_snapshot(self, name: str, snapshot_name: str) -> None:
        try:
            subprocess.check_call(["virsh", "snapshot-create-as", name, snapshot_name])
        except Exception as e:
            raise HypervisorError(f"Failed to create snapshot '{snapshot_name}' for '{name}': {e}")

    def revert_snapshot(self, name: str, snapshot_name: str) -> None:
        try:
            subprocess.check_call(["virsh", "snapshot-revert", name, snapshot_name])
        except Exception as e:
            raise HypervisorError(f"Failed to revert to snapshot '{snapshot_name}' for '{name}': {e}")

    def delete_snapshot(self, name: str, snapshot_name: str) -> None:
        try:
            subprocess.check_call(["virsh", "snapshot-delete", name, snapshot_name])
        except Exception as e:
            raise HypervisorError(f"Failed to delete snapshot '{snapshot_name}' for '{name}': {e}")

    def list_snapshots(self, name: str) -> List[str]:
        try:
            out = subprocess.check_output(["virsh", "snapshot-list", name, "--name"], text=True)
            return [line.strip() for line in out.splitlines() if line.strip()]
        except Exception as e:
            raise HypervisorError(f"Failed to list snapshots for '{name}': {e}")


class MockHypervisorBackend(HypervisorBackend):
    """Simulated in-memory hypervisor for offline development and testing."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file and self.state_file.exists():
            try:
                import json
                with open(self.state_file, "r") as f:
                    self.nodes = json.load(f)
            except Exception:
                self.nodes = {}

    def _save(self) -> None:
        if self.state_file:
            try:
                import json
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.state_file, "w") as f:
                    json.dump(self.nodes, f)
            except Exception:
                pass

    def list_nodes(self) -> List[str]:
        return list(self.nodes.keys())

    def get_state(self, name: str) -> VMState:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        return self.nodes[name]["state"]

    def clone(self, template: str, name: str, thin: bool = True) -> None:
        if name in self.nodes:
            raise HypervisorError(f"Node '{name}' already exists")
        self.nodes[name] = {
            "template": template,
            "state": VMState.SHUTOFF,
            "snapshots": {},
            "thin": thin
        }
        self._save()

    def start(self, name: str) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        self.nodes[name]["state"] = VMState.RUNNING
        self._save()

    def stop(self, name: str, force: bool = False) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        self.nodes[name]["state"] = VMState.SHUTOFF
        self._save()

    def destroy(self, name: str) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        del self.nodes[name]
        self._save()

    def create_snapshot(self, name: str, snapshot_name: str) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        # Record a snapshot of the current state
        self.nodes[name]["snapshots"][snapshot_name] = {
            "state": self.nodes[name]["state"]
        }
        self._save()

    def revert_snapshot(self, name: str, snapshot_name: str) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        if snapshot_name not in self.nodes[name]["snapshots"]:
            raise HypervisorError(f"Snapshot '{snapshot_name}' not found for '{name}'")
        self.nodes[name]["state"] = self.nodes[name]["snapshots"][snapshot_name]["state"]
        self._save()

    def delete_snapshot(self, name: str, snapshot_name: str) -> None:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        if snapshot_name not in self.nodes[name]["snapshots"]:
            raise HypervisorError(f"Snapshot '{snapshot_name}' not found for '{name}'")
        del self.nodes[name]["snapshots"][snapshot_name]
        self._save()

    def list_snapshots(self, name: str) -> List[str]:
        if name not in self.nodes:
            raise HypervisorError(f"Node '{name}' does not exist")
        return list(self.nodes[name]["snapshots"].keys())
