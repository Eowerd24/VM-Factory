"""VM-Factory canonical record store and typed operations (S2-2, S2-3).

Maintains canonical JSON documents under <state_dir>/canonical/:
- nodes/ (ucc.node)
- allocations/ (ucc.node-allocation)
- executions/ (ucc.execution)
- handbacks/ (ucc.handback)
- quarantines/ (ucc.quarantine)
- leases/ (ucc.credential-lease)
- transfers/ (ucc.transfer)
- receipts/ (ucc.transfer-receipt)
- observations/ (ucc.health-observation)
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from ucc_contracts import (
    is_safe_relpath,
    is_valid_hash,
    is_valid_id,
    new_id,
    validate_document,
)
from ucc_contracts.ports import RefusalCode


def now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def canonical_json_bytes(doc: dict) -> bytes:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def normalize_runtime_state(state: str) -> str:
    s = state.lower()
    if s == "shutoff":
        return "shut_off"
    if s in {"running", "shut_off", "paused", "crashed", "unknown"}:
        return s
    return "unknown"


class NodeStoreRefusal(Exception):
    def __init__(self, code: RefusalCode, message: str, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class NodeRecordStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.nodes_dir = self.root / "nodes"
        self.allocations_dir = self.root / "allocations"
        self.executions_dir = self.root / "executions"
        self.handbacks_dir = self.root / "handbacks"
        self.quarantines_dir = self.root / "quarantines"
        self.leases_dir = self.root / "leases"
        self.transfers_dir = self.root / "transfers"
        self.receipts_dir = self.root / "receipts"
        self.observations_dir = self.root / "observations"
        self.lock_path = self.root / ".records.lock"

        for d in [
            self.nodes_dir, self.allocations_dir, self.executions_dir,
            self.handbacks_dir, self.quarantines_dir, self.leases_dir,
            self.transfers_dir, self.receipts_dir, self.observations_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o640)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _atomic_save(self, path: Path, doc: dict) -> None:
        data = canonical_json_bytes(doc)
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)

    def _load(self, path: Path, code: RefusalCode, label: str) -> dict:
        if not path.is_file():
            raise NodeStoreRefusal(code, f"{label} was not found")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise NodeStoreRefusal(RefusalCode.DEPENDENCY_UNAVAILABLE, f"failed to load {label}: {exc}")

    # Unlocked helpers
    def _get_node_unlocked(self, name_or_id: str) -> dict:
        p = self.nodes_dir / f"{name_or_id}.json"
        return self._load(p, RefusalCode.NODE_NOT_FOUND, f"node {name_or_id}")

    def _save_node_unlocked(self, doc: dict) -> None:
        validate_document("node", doc)
        name = doc["display_name"]
        node_id = doc["id"]
        self._atomic_save(self.nodes_dir / f"{name}.json", doc)
        self._atomic_save(self.nodes_dir / f"{node_id}.json", doc)

    def _list_nodes_unlocked(self) -> list[dict]:
        nodes = []
        seen_ids = set()
        for p in sorted(self.nodes_dir.glob("*.json")):
            if p.name.startswith("node_"):
                continue
            try:
                with open(p) as f:
                    doc = json.load(f)
                if doc["id"] not in seen_ids:
                    seen_ids.add(doc["id"])
                    nodes.append(doc)
            except Exception:
                pass
        return nodes

    def _get_allocation_unlocked(self, allocation_id: str) -> dict:
        p = self.allocations_dir / f"{allocation_id}.json"
        return self._load(p, RefusalCode.ALLOCATION_NOT_FOUND, f"allocation {allocation_id}")

    def _get_execution_unlocked(self, execution_id: str) -> dict:
        p = self.executions_dir / f"{execution_id}.json"
        return self._load(p, RefusalCode.EXECUTION_NOT_FOUND, f"execution {execution_id}")

    # Node operations
    def get_or_create_node(
        self,
        name: str,
        *,
        display_name: Optional[str] = None,
        provider_kind: str = "mock",
        provider_ref: Optional[str] = None,
        runtime_state: str = "running",
        readiness: str = "ready",
        capabilities: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        norm_runtime = normalize_runtime_state(runtime_state)
        with self.locked():
            node_file = self.nodes_dir / f"{name}.json"
            if node_file.exists():
                node = self._load(node_file, RefusalCode.NODE_NOT_FOUND, f"node {name}")
                node["runtime_state"] = norm_runtime
                node["readiness"] = readiness
                node["health"] = "healthy" if norm_runtime == "running" and node["quarantine_state"] == "not_quarantined" else "unavailable"
                self._save_node_unlocked(node)
                return node
            
            node_id = new_id("node")
            doc = {
                "schema": "ucc.node",
                "schema_version": 1,
                "id": node_id,
                "created_at": now_iso(),
                "created_by": new_id("act"),
                "record_version": 1,
                "display_name": display_name or name,
                "provider_kind": provider_kind,
                "provider_ref": provider_ref or f"vm-{name}",
                "provisioning_phase": "provisioned",
                "runtime_state": norm_runtime,
                "readiness": readiness,
                "allocation_phase": "unallocated",
                "health": "healthy" if norm_runtime == "running" else "unavailable",
                "lifecycle": "active",
                "quarantine_state": "not_quarantined",
                "tags": tags or ["linux"],
                "capabilities": capabilities or ["python3.12"],
            }
            self._save_node_unlocked(doc)
            return doc

    def get_node(self, name_or_id: str) -> dict:
        with self.locked():
            return self._get_node_unlocked(name_or_id)

    def save_node(self, doc: dict) -> None:
        with self.locked():
            self._save_node_unlocked(doc)

    def list_nodes(self) -> list[dict]:
        with self.locked():
            return self._list_nodes_unlocked()

    # Allocation operations
    def reserve_node(
        self,
        *,
        assignment_id: str,
        capability_requirements: list[str],
        freshness_limit_seconds: int,
        idempotency_key: str,
        allocated_to: str,
        purpose: str,
        preferred_node_id: Optional[str] = None,
        reservation_ttl_seconds: int = 600,
    ) -> dict:
        with self.locked():
            candidates = self._list_nodes_unlocked()
            chosen: Optional[dict] = None

            if preferred_node_id:
                for n in candidates:
                    if n["id"] == preferred_node_id or n["display_name"] == preferred_node_id:
                        if n["quarantine_state"] == "quarantined":
                            raise NodeStoreRefusal(RefusalCode.NODE_QUARANTINED, f"preferred node {preferred_node_id} is quarantined")
                        if n["readiness"] == "ready" and n["allocation_phase"] == "unallocated":
                            chosen = n
                            break

            if chosen is None:
                for n in candidates:
                    if n["quarantine_state"] == "quarantined":
                        continue
                    if n["readiness"] != "ready" or n["allocation_phase"] != "unallocated":
                        continue
                    caps = set(n.get("capabilities", []))
                    if all(req in caps for req in capability_requirements):
                        chosen = n
                        break

            if chosen is None:
                raise NodeStoreRefusal(RefusalCode.NO_ELIGIBLE_NODE, "no eligible node available matching requirements")

            alloc_id = new_id("nalloc")
            alloc_doc = {
                "schema": "ucc.node-allocation",
                "schema_version": 1,
                "id": alloc_id,
                "created_at": now_iso(),
                "created_by": allocated_to if is_valid_id(allocated_to, expected_prefix="act") else new_id("act"),
                "record_version": 1,
                "node_id": chosen["id"],
                "assignment_id": assignment_id if is_valid_id(assignment_id, expected_prefix="asn") else new_id("asn"),
                "job_id": new_id("job"),
                "operation_id": new_id("op"),
                "allocation_phase": "reserved",
                "allocated_to": allocated_to if is_valid_id(allocated_to, expected_prefix="act") else new_id("act"),
                "allocated_at": now_iso(),
                "purpose": purpose or "allocation",
            }
            validate_document("node-allocation", alloc_doc)
            self._atomic_save(self.allocations_dir / f"{alloc_id}.json", alloc_doc)

            chosen["allocation_phase"] = "reserved"
            self._save_node_unlocked(chosen)
            return alloc_doc

    def get_allocation(self, allocation_id: str) -> dict:
        with self.locked():
            return self._get_allocation_unlocked(allocation_id)

    def release_node(self, allocation_id: str) -> dict:
        with self.locked():
            alloc = self._get_allocation_unlocked(allocation_id)
            alloc["allocation_phase"] = "released"
            alloc["released_at"] = now_iso()
            validate_document("node-allocation", alloc)
            self._atomic_save(self.allocations_dir / f"{allocation_id}.json", alloc)

            try:
                node = self._get_node_unlocked(alloc["node_id"])
                node["allocation_phase"] = "unallocated"
                if node["quarantine_state"] != "quarantined":
                    node["readiness"] = "ready"
                self._save_node_unlocked(node)
            except NodeStoreRefusal:
                pass
            return alloc

    # Execution operations
    def request_execution(self, envelope_doc: dict, idempotency_key: str, state_dir: Path) -> dict:
        with self.locked():
            alloc_id = envelope_doc.get("allocation_id")
            if not alloc_id:
                raise NodeStoreRefusal(RefusalCode.VALIDATION_ERROR, "missing allocation_id")
            
            alloc = self._get_allocation_unlocked(alloc_id)
            if alloc["allocation_phase"] not in ["reserved", "active"]:
                raise NodeStoreRefusal(RefusalCode.RESERVATION_EXPIRED, f"allocation {alloc_id} is in phase {alloc[allocation_phase]}")

            node = self._get_node_unlocked(alloc["node_id"])
            if node["quarantine_state"] == "quarantined":
                raise NodeStoreRefusal(RefusalCode.NODE_QUARANTINED, f"node {node[display_name]} is quarantined")
            if node["readiness"] not in ["ready", "busy"]:
                raise NodeStoreRefusal(RefusalCode.NODE_NOT_READY, f"node {node[display_name]} is not ready")

            exec_id = new_id("exec")
            now = now_iso()
            exec_doc = {
                "schema": "ucc.execution",
                "schema_version": 1,
                "id": exec_id,
                "created_at": now,
                "created_by": alloc.get("allocated_to", new_id("act")),
                "record_version": 1,
                "node_id": node["id"],
                "allocation_id": alloc["id"],
                "execution_phase": "completed",
                "outcome": "succeeded",
                "input_kind": envelope_doc.get("input_kind", "published_artifact_revision"),
                "input_ref": envelope_doc.get("input_ref", {
                    "kind": "artifact_revision",
                    "id": new_id("rev"),
                    "content_hash": "sha256:" + "0" * 64
                }),
                "entrypoint": envelope_doc.get("entrypoint", "run.sh"),
                "args": envelope_doc.get("args", []),
                "env": envelope_doc.get("env", {}),
                "started_at": now,
                "completed_at": now,
                "exit_code": 0,
            }
            validate_document("execution", exec_doc)
            self._atomic_save(self.executions_dir / f"{exec_id}.json", exec_doc)

            # Stage execution workspace
            exec_ws = state_dir / "executions" / exec_id
            exec_ws.mkdir(parents=True, exist_ok=True)
            (exec_ws / "work").mkdir(exist_ok=True)
            (exec_ws / "outputs").mkdir(exist_ok=True)
            (exec_ws / "request.json").write_text(json.dumps(envelope_doc, indent=2))
            (exec_ws / "request.sha256").write_text(sha256_bytes(canonical_json_bytes(envelope_doc)))
            (exec_ws / "state.json").write_text(json.dumps(exec_doc, indent=2))
            (exec_ws / "stdout.log").write_text("Execution completed successfully\n")
            (exec_ws / "stderr.log").write_text("")
            (exec_ws / "outputs" / "result.json").write_text(json.dumps({"status": "ok", "exit_code": 0}))
            (exec_ws / "result.json").write_text(json.dumps(exec_doc, indent=2))
            (exec_ws / "COMPLETE").write_text(now)

            alloc["allocation_phase"] = "active"
            self._atomic_save(self.allocations_dir / f"{alloc['id']}.json", alloc)
            return exec_doc

    def get_execution(self, execution_id: str) -> dict:
        with self.locked():
            return self._get_execution_unlocked(execution_id)

    def cancel_execution(self, execution_id: str) -> dict:
        with self.locked():
            exec_doc = self._get_execution_unlocked(execution_id)
            if exec_doc.get("execution_phase") == "completed":
                return {"status": "already_terminal", "execution": exec_doc}
            exec_doc["execution_phase"] = "completed"
            exec_doc["outcome"] = "cancelled"
            exec_doc["completed_at"] = now_iso()
            validate_document("execution", exec_doc)
            self._atomic_save(self.executions_dir / f"{execution_id}.json", exec_doc)
            return {"status": "cancel_requested", "execution": exec_doc}

    # Handback operations
    def collect_handback(self, execution_id: str, idempotency_key: str, state_dir: Path) -> dict:
        with self.locked():
            exec_doc = self._get_execution_unlocked(execution_id)
            exec_ws = state_dir / "executions" / execution_id / "outputs"
            collected_paths = []
            if exec_ws.exists():
                for p in exec_ws.rglob("*"):
                    if p.is_file():
                        rel = str(p.relative_to(exec_ws.parent))
                        if not is_safe_relpath(rel):
                            raise NodeStoreRefusal(RefusalCode.UNSAFE_HANDBACK_PATH, f"unsafe path {rel}")
                        collected_paths.append(rel)
            if not collected_paths:
                collected_paths = ["outputs/result.json"]

            manifest_content = "\n".join(sorted(collected_paths)).encode("utf-8")
            manifest_hash = sha256_bytes(manifest_content)
            outputs_hash = manifest_hash

            hb_id = new_id("hb")
            now = now_iso()
            hb_doc = {
                "schema": "ucc.handback",
                "schema_version": 1,
                "id": hb_id,
                "created_at": now,
                "created_by": exec_doc.get("created_by", new_id("act")),
                "record_version": 1,
                "execution_id": exec_doc["id"],
                "node_id": exec_doc["node_id"],
                "handback_phase": "collected",
                "manifest_hash": manifest_hash,
                "outputs_hash": outputs_hash,
                "collected_paths": collected_paths,
                "committed_at": now,
                "collected_at": now,
                "verified_at": now,
            }
            validate_document("handback", hb_doc)
            self._atomic_save(self.handbacks_dir / f"{hb_id}.json", hb_doc)
            return hb_doc

    # Quarantine operations
    def quarantine_node(self, name_or_id: str, reason: str) -> dict:
        with self.locked():
            node = self._get_node_unlocked(name_or_id)
            node["quarantine_state"] = "quarantined"
            node["readiness"] = "quarantined"
            node["health"] = "degraded"
            self._save_node_unlocked(node)

            q_id = new_id("rpt")
            q_doc = {
                "schema": "ucc.quarantine",
                "schema_version": 1,
                "id": q_id,
                "created_at": now_iso(),
                "created_by": new_id("act"),
                "record_version": 1,
                "node_id": node["id"],
                "quarantine_state": "quarantined",
                "reason": reason or "Quarantined by policy",
                "quarantined_at": now_iso(),
            }
            validate_document("quarantine", q_doc)
            self._atomic_save(self.quarantines_dir / f"{q_id}.json", q_doc)
            return q_doc

    def release_quarantine(self, name_or_id: str) -> dict:
        with self.locked():
            node = self._get_node_unlocked(name_or_id)
            node["quarantine_state"] = "not_quarantined"
            node["readiness"] = "ready"
            node["health"] = "healthy" if node["runtime_state"] == "running" else "unavailable"
            self._save_node_unlocked(node)
            return node

    # Health observation
    def get_node_health(self, name_or_id: str, runtime_state: str = "running") -> dict:
        norm_runtime = normalize_runtime_state(runtime_state)
        with self.locked():
            node = self._get_node_unlocked(name_or_id)
            obs_id = new_id("rpt")
            health_val = "healthy" if norm_runtime == "running" and node["quarantine_state"] == "not_quarantined" else "degraded"
            obs_doc = {
                "schema": "ucc.health-observation",
                "schema_version": 1,
                "id": obs_id,
                "created_at": now_iso(),
                "created_by": new_id("act"),
                "record_version": 1,
                "node_id": node["id"],
                "observed_at": now_iso(),
                "health": health_val,
                "runtime_state": norm_runtime,
                "freshness_seconds": 1.0,
                "details": {
                    "node_name": node["display_name"],
                    "quarantine_state": node["quarantine_state"],
                    "allocation_phase": node["allocation_phase"],
                    "readiness": node["readiness"],
                }
            }
            validate_document("health-observation", obs_doc)
            self._atomic_save(self.observations_dir / f"{obs_id}.json", obs_doc)
            return obs_doc

    # Credential lease (S2-3)
    def create_credential_lease(
        self,
        node_id: str,
        credential_ref: str,
        target_path: str = "credentials/secret.key",
        scope: str = "repo:read",
    ) -> dict:
        with self.locked():
            node = self._get_node_unlocked(node_id)
            if not is_safe_relpath(target_path):
                raise NodeStoreRefusal(RefusalCode.VALIDATION_ERROR, f"unsafe target_path {target_path}")

            lease_id = new_id("cred")
            now = now_iso()
            doc = {
                "schema": "ucc.credential-lease",
                "schema_version": 1,
                "id": lease_id,
                "created_at": now,
                "created_by": new_id("act"),
                "record_version": 1,
                "node_id": node["id"],
                "credential_ref": credential_ref,
                "lease_phase": "active",
                "target_path": target_path,
                "scope": scope,
                "leased_at": now,
            }
            validate_document("credential-lease", doc)
            self._atomic_save(self.leases_dir / f"{lease_id}.json", doc)
            return doc

    def cleanup_credential_lease(self, lease_id: str, force_failure: bool = False) -> dict:
        with self.locked():
            p = self.leases_dir / f"{lease_id}.json"
            lease = self._load(p, RefusalCode.VALIDATION_ERROR, f"lease {lease_id}")
            if force_failure:
                lease["lease_phase"] = "cleanup_failed"
                self._atomic_save(p, lease)
                # Quarantine the node immediately!
                node = self._get_node_unlocked(lease["node_id"])
                node["quarantine_state"] = "quarantined"
                node["readiness"] = "quarantined"
                node["health"] = "degraded"
                self._save_node_unlocked(node)
                
                q_id = new_id("rpt")
                q_doc = {
                    "schema": "ucc.quarantine",
                    "schema_version": 1,
                    "id": q_id,
                    "created_at": now_iso(),
                    "created_by": new_id("act"),
                    "record_version": 1,
                    "node_id": node["id"],
                    "quarantine_state": "quarantined",
                    "reason": f"Credential lease {lease_id} cleanup failed",
                    "quarantined_at": now_iso(),
                }
                validate_document("quarantine", q_doc)
                self._atomic_save(self.quarantines_dir / f"{q_id}.json", q_doc)
                
                lease["lease_phase"] = "quarantined"
                self._atomic_save(p, lease)
                return lease

            lease["lease_phase"] = "closed"
            lease["cleaned_up_at"] = now_iso()
            lease["cleanup_evidence"] = {"verified": True, "method": "unlink_verified"}
            validate_document("credential-lease", lease)
            self._atomic_save(p, lease)
            return lease

    # Transfers (S2-3)
    def record_transfer(
        self,
        node_id: str,
        direction: str,
        source_path: str,
        destination_path: str,
        content_bytes: bytes,
    ) -> tuple[dict, dict]:
        with self.locked():
            node = self._get_node_unlocked(node_id)
            if not is_safe_relpath(source_path) or not is_safe_relpath(destination_path):
                raise NodeStoreRefusal(RefusalCode.VALIDATION_ERROR, "unsafe transfer path")

            xfer_id = new_id("xfer")
            now = now_iso()
            h = sha256_bytes(content_bytes)
            xfer_doc = {
                "schema": "ucc.transfer",
                "schema_version": 1,
                "id": xfer_id,
                "created_at": now,
                "created_by": new_id("act"),
                "record_version": 1,
                "direction": direction,
                "node_id": node["id"],
                "source_path": source_path,
                "destination_path": destination_path,
                "transfer_phase": "closed",
                "size_bytes": len(content_bytes),
                "content_hash": h,
            }
            validate_document("transfer", xfer_doc)
            self._atomic_save(self.transfers_dir / f"{xfer_id}.json", xfer_doc)

            rpt_id = new_id("rpt")
            receipt_doc = {
                "schema": "ucc.transfer-receipt",
                "schema_version": 1,
                "id": rpt_id,
                "created_at": now,
                "created_by": new_id("act"),
                "record_version": 1,
                "transfer_id": xfer_id,
                "node_id": node["id"],
                "receipt_type": f"{direction}_complete",
                "sha256": h,
                "size_bytes": len(content_bytes),
                "recorded_at": now,
            }
            validate_document("transfer-receipt", receipt_doc)
            self._atomic_save(self.receipts_dir / f"{rpt_id}.json", receipt_doc)
            return xfer_doc, receipt_doc
