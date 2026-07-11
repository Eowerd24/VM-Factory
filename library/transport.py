import subprocess
import os
import json
import hashlib
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

class TransportError(Exception):
    """Raised for any connection or transfer errors."""
    pass

class TransportBackend:
    """Interface for guest VM interaction (SSH/SCP)."""

    def run_cmd(self, ip: str, cmd: str, user: str = "admin", key_path: Optional[Path] = None) -> Tuple[int, str, str]:
        raise NotImplementedError()

    def push(self, ip: str, local_path: Path, remote_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        raise NotImplementedError()

    def pull(self, ip: str, remote_path: Path, local_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        raise NotImplementedError()

    def collect_outbox(self, ip: str, remote_dir: Path, local_dir: Path, user: str = "admin", key_path: Optional[Path] = None) -> Dict[str, Any]:
        raise NotImplementedError()


class SSHTransportBackend(TransportBackend):
    """Real transport using system ssh/scp subprocesses."""

    def _get_ssh_opts(self, key_path: Optional[Path] = None) -> List[str]:
        opts = [
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "UserKnownHostsFile=/dev/null",  # avoid known_hosts pollution
            "-o", "ConnectTimeout=5"
        ]
        if key_path:
            opts += ["-i", str(key_path)]
        return opts

    def run_cmd(self, ip: str, cmd: str, user: str = "admin", key_path: Optional[Path] = None) -> Tuple[int, str, str]:
        ssh_cmd = ["ssh"] + self._get_ssh_opts(key_path) + [f"{user}@{ip}", cmd]
        try:
            res = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            raise TransportError(f"Failed to execute SSH command on {ip}: {e}")

    def push(self, ip: str, local_path: Path, remote_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        scp_cmd = ["scp"] + self._get_ssh_opts(key_path) + [str(local_path), f"{user}@{ip}:{remote_path}"]
        try:
            subprocess.run(scp_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise TransportError(f"Failed to push file to {ip}: {e.stderr.decode() if e.stderr else str(e)}")

    def pull(self, ip: str, remote_path: Path, local_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        scp_cmd = ["scp"] + self._get_ssh_opts(key_path) + [f"{user}@{ip}:{remote_path}", str(local_path)]
        try:
            subprocess.run(scp_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise TransportError(f"Failed to pull file from {ip}: {e.stderr.decode() if e.stderr else str(e)}")

    def collect_outbox(self, ip: str, remote_dir: Path, local_dir: Path, user: str = "admin", key_path: Optional[Path] = None) -> Dict[str, Any]:
        """Pulls files from the remote node outbox, verifying them via the handback manifest."""
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Pull the handback manifest first
        remote_manifest = remote_dir / "handback.json"
        local_manifest = local_dir / "handback.json"
        
        try:
            self.pull(ip, remote_manifest, local_manifest, user, key_path)
        except Exception as e:
            raise TransportError(f"Failed to collect handback manifest: {e}")

        # 2. Read manifest
        with open(local_manifest, "r") as f:
            manifest_data = json.load(f)
            
        files_to_collect = manifest_data.get("files", [])
        verified_files = []
        errors = []

        # 3. Pull each file and verify sha256
        for f_info in files_to_collect:
            rel_path = f_info["path"]
            expected_sha = f_info["sha256"]
            
            remote_file = remote_dir / rel_path
            local_file = local_dir / rel_path
            
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                self.pull(ip, remote_file, local_file, user, key_path)
                
                # Check sha256
                sha = hashlib.sha256()
                with open(local_file, "rb") as lf:
                    while chunk := lf.read(8192):
                        sha.update(chunk)
                actual_sha = sha.hexdigest()
                
                if actual_sha == expected_sha:
                    verified_files.append(rel_path)
                else:
                    errors.append(f"Checksum mismatch for '{rel_path}': expected {expected_sha}, got {actual_sha}")
            except Exception as e:
                errors.append(f"Failed to collect '{rel_path}': {e}")

        return {
            "node": manifest_data.get("node"),
            "ts": manifest_data.get("ts"),
            "verified_files": verified_files,
            "errors": errors,
            "success": len(errors) == 0
        }


class MockTransportBackend(TransportBackend):
    """Mock transport simulator for development & sandbox validation."""

    def __init__(self):
        self.commands: Dict[str, List[str]] = {}
        self.files: Dict[str, Dict[str, str]] = {}  # ip -> {path: content}

    def run_cmd(self, ip: str, cmd: str, user: str = "admin", key_path: Optional[Path] = None) -> Tuple[int, str, str]:
        self.commands.setdefault(ip, []).append(cmd)
        
        # Simple simulated behavior
        if "preflight" in cmd:
            report = {
                "node": "mock-node",
                "ts": "2026-07-11T12:00:00Z",
                "kind": "pre",
                "checks": [{"id": "C1", "name": "CPU", "status": "pass"}]
            }
            return 0, json.dumps(report), ""
        return 0, "mock stdout", ""

    def push(self, ip: str, local_path: Path, remote_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        content = local_path.read_text() if local_path.exists() else "mock content"
        self.files.setdefault(ip, {})[str(remote_path)] = content

    def pull(self, ip: str, remote_path: Path, local_path: Path, user: str = "admin", key_path: Optional[Path] = None) -> None:
        content = self.files.get(ip, {}).get(str(remote_path), "mock content")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content)

    def collect_outbox(self, ip: str, remote_dir: Path, local_dir: Path, user: str = "admin", key_path: Optional[Path] = None) -> Dict[str, Any]:
        # Prepopulate a mock handback list
        local_dir.mkdir(parents=True, exist_ok=True)
        handback_path = local_dir / "handback.json"
        
        manifest_data = {
            "node": "mock-node",
            "ts": "2026-07-11T12:00:00Z",
            "files": [
                {"path": "PROGRESS.md", "sha256": hashlib.sha256(b"mock progress").hexdigest()}
            ]
        }
        
        with open(handback_path, "w") as f:
            json.dump(manifest_data, f)
            
        progress_path = local_dir / "PROGRESS.md"
        progress_path.write_text("mock progress")
        
        return {
            "node": "mock-node",
            "ts": "2026-07-11T12:00:00Z",
            "verified_files": ["PROGRESS.md"],
            "errors": [],
            "success": True
        }
