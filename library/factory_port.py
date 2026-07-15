"""FactoryPort adapter (G3, roadmap §4C "FactoryPort adapter").

Thin, in-process adapter over `NodeLifecycleEngine` — no new transport, mock
parity kept (UCC-Standards §13). This is the ONLY seam a future nodectl
consumer may use to reach VM-Factory. It must never call the fenced
string-exec `NodeLifecycleEngine.assign()` path directly (see
tests/test_string_exec_fence.py) — that fence exists specifically to keep a
future port from bypassing typed execution.

Three methods have real behavior today because they map cleanly onto
existing engine capability without touching a fenced path or fabricating
data: `list_eligible_nodes` (manifest query), `get_node_health` (manifest +
hypervisor state), `reset_node` (engine.reset()). The other seven refuse
`DEPENDENCY_UNAVAILABLE`: VM-Factory has no NodeAllocation/Execution/
Handback/Quarantine record store yet (roadmap §4C "Typed execution +
allocation", "Atomic manifests + handbacks", "Credential lease + cleanup
evidence" — separate, larger work items). Fabricating a fake allocation or
execution id would violate the same fail-closed principle as the vault fix.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from library.engine import EngineError, NodeLifecycleEngine
from library.idempotency_store import (
    IdempotencyOutcome,
    IdempotencyStore,
    evaluate_idempotency,
    request_fingerprint,
)
from library.manifest import ManifestManager
from library.models import NodeState
from library.ucc_events import deterministic_id, ucc_now_iso
from ucc_contracts import new_id, validate_document
from ucc_contracts.idempotency import idempotency_conflict_problem
from ucc_contracts.ports import (
    CollectHandbackRequest, EligibilityRequest,  # re-exported for callers; unused directly here
    ExecutionRequestEnvelope, FactoryPort, PortResult, RefusalCode, ReserveNodeRequest,
)

_NOT_YET_BUILT = (
    "VM-Factory has no NodeAllocation/Execution/Handback/Quarantine record "
    "store yet; this FactoryPort method cannot be served."
)


def _dependency_unavailable() -> PortResult:
    return PortResult(ok=False, disposition="refused",
                      refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
                      message=_NOT_YET_BUILT, retryable=True)


def _validation_refusal(message: str) -> PortResult:
    return PortResult(ok=False, disposition="refused",
                      refusal_code=RefusalCode.VALIDATION_ERROR,
                      message=message, retryable=False)


def _require_keys(request: dict, *keys: str) -> PortResult | None:
    missing = [key for key in keys if key not in request]
    if missing:
        return _validation_refusal(f"missing required field(s): {', '.join(missing)}")
    return None


class VMFactoryFactoryPort:
    """Concrete FactoryPort. `isinstance(VMFactoryFactoryPort(engine), FactoryPort)`
    holds via the Protocol's structural check (see tests/test_factory_port.py)."""

    def __init__(self, engine: NodeLifecycleEngine):
        self.engine = engine

    def list_eligible_nodes(self, request: dict) -> PortResult:
        nodes = []
        if self.engine.nodes_dir.exists():
            for node_dir in sorted(self.engine.nodes_dir.iterdir()):
                manifest_path = node_dir / "node.yaml"
                if not manifest_path.exists():
                    continue
                try:
                    manifest = ManifestManager.load(manifest_path)
                except Exception:
                    continue
                if manifest.state == NodeState.READY:
                    nodes.append({"name": manifest.name, "type": manifest.type.value})
        return PortResult(ok=True, disposition="completed", value={"nodes": nodes})

    def reserve_node(self, request: ReserveNodeRequest) -> PortResult:
        return _dependency_unavailable()

    def release_node(self, request: dict) -> PortResult:
        refusal = _require_keys(request, "allocation_id")
        return refusal or _dependency_unavailable()

    def request_execution(self, request: ExecutionRequestEnvelope) -> PortResult:
        return _dependency_unavailable()

    def get_execution(self, request: dict) -> PortResult:
        refusal = _require_keys(request, "execution_id")
        return refusal or _dependency_unavailable()

    def collect_handback(self, request: CollectHandbackRequest) -> PortResult:
        return _dependency_unavailable()

    def cancel_execution(self, request: dict) -> PortResult:
        # Standards §13: cancellation never claims termination before
        # observation. There is no Execution record to observe, so the only
        # honest disposition is refused, never "cancelled".
        refusal = _require_keys(request, "execution_id")
        return refusal or _dependency_unavailable()

    def reset_node(self, request: dict) -> PortResult:
        name = request.get("name")
        if not name:
            return _validation_refusal("missing required field: name")
        idempotency_key = request.get("idempotency_key")
        if idempotency_key:
            return self._reset_node_idempotent(name, idempotency_key)
        try:
            manifest = self.engine.reset(name)
        except EngineError as exc:
            return PortResult(ok=False, disposition="failed", message=str(exc), retryable=False)
        return PortResult(ok=True, disposition="completed",
                          value={"name": manifest.name, "state": manifest.state.value})

    def _reset_node_idempotent(self, name: str, idempotency_key: str) -> PortResult:
        """M-b (D2): opt-in idempotent replay for reset_node, gated on
        `request["idempotency_key"]` being present — the non-idempotent path
        above is unchanged for callers that don't pass one. Dispatch is
        preceded by a durable in-flight record. Definite failure removes it;
        ambiguity leaves it for operator reconciliation."""
        store = IdempotencyStore(self.engine.state_dir / "idempotency.db")
        payload = {"name": name}
        fingerprint = request_fingerprint(payload)
        stored = store.get(idempotency_key)
        outcome = evaluate_idempotency(idempotency_key, fingerprint, stored)

        request_id = new_id("req")
        operation_id = new_id("op")
        correlation_id = new_id("corr")

        if outcome == IdempotencyOutcome.REPLAY:
            return PortResult(ok=True, disposition="completed", value=stored.result)

        if outcome == IdempotencyOutcome.IN_FLIGHT:
            return PortResult(
                ok=False,
                disposition="refused",
                refusal_code=RefusalCode.OUTCOME_UNKNOWN,
                message="operation outcome is unknown; operator reconciliation is required",
                retryable=False,
            )

        if outcome == IdempotencyOutcome.CONFLICT:
            problem = idempotency_conflict_problem(
                request_id=request_id, operation_id=operation_id, correlation_id=correlation_id)
            return PortResult(ok=False, disposition="refused",
                              refusal_code=RefusalCode.IDEMPOTENCY_CONFLICT,
                              message=problem["message"], retryable=False)

        # NEW: build + validate the request envelope, run the real op, build
        # + validate the result envelope, store the exact value we return
        # (so replay is verbatim), return it.
        request_doc = {
            "schema": "ucc.request", "schema_version": 1,
            "request_id": request_id, "operation_id": operation_id, "correlation_id": correlation_id,
            "causation_id": None, "idempotency_key": idempotency_key,
            "request_fingerprint": fingerprint, "requested_at": ucc_now_iso(),
            "requested_by": new_id("act"), "operation_type": "node.reset", "payload": payload,
        }
        validate_document("request", request_doc)

        store.begin(
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            operation_type="node.reset",
            result={
                "disposition": "unknown",
                "request_id": request_id,
                "operation_id": operation_id,
                "correlation_id": correlation_id,
            },
            created_at=request_doc["requested_at"],
        )

        try:
            manifest = self.engine.reset(name)
        except EngineError as exc:
            store.abandon(idempotency_key=idempotency_key, fingerprint=fingerprint)
            return PortResult(ok=False, disposition="failed", message=str(exc), retryable=False)

        result_doc = {
            "schema": "ucc.result", "schema_version": 1,
            "result_id": new_id("res"), "request_id": request_id, "operation_id": operation_id,
            "correlation_id": correlation_id, "completed_at": ucc_now_iso(),
            "disposition": "completed",
            "resource": {"kind": "node", "id": deterministic_id("node", f"node:{name}")},
            "warnings": [],
        }
        validate_document("result", result_doc)
        value = {"name": manifest.name, "state": manifest.state.value, "result": result_doc}
        store.complete(idempotency_key=idempotency_key, fingerprint=fingerprint,
                       disposition="completed", result=value)
        return PortResult(ok=True, disposition="completed", value=value)

    def quarantine_node(self, request: dict) -> PortResult:
        refusal = _require_keys(request, "node_id")
        return refusal or _dependency_unavailable()

    def get_node_health(self, request: dict) -> PortResult:
        name = request.get("name")
        if not name:
            return _validation_refusal("missing required field: name")
        manifest_path = self.engine._get_manifest_path(name)
        try:
            manifest = ManifestManager.load(manifest_path)
        except FileNotFoundError:
            # ucc-contracts v0.2.0 added NODE_NOT_FOUND to FACTORY_PORT_CODES
            # (D6) specifically for this case — a raw node-by-name query with
            # no manifest, distinct from ALLOCATION_NOT_FOUND/EXECUTION_NOT_FOUND.
            return PortResult(ok=False, disposition="refused", refusal_code=RefusalCode.NODE_NOT_FOUND,
                              message=f"no manifest for node '{name}'", retryable=False)
        try:
            vm_state = self.engine.hypervisor.get_state(name)
        except Exception as exc:
            return PortResult(ok=False, disposition="failed", message=str(exc), retryable=True)
        return PortResult(ok=True, disposition="completed", value={
            "name": manifest.name,
            "lifecycle_state": manifest.state.value,
            "runtime_state": vm_state.value,
        })


def build_factory_port(engine: NodeLifecycleEngine) -> FactoryPort:
    return VMFactoryFactoryPort(engine)
