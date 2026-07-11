from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class NodeType(str, Enum):
    AI_WORKER = "ai-worker"
    DEV_DESKTOP = "dev-desktop"
    DEV_SERVER = "dev-server"
    HOMELAB_SERVICE = "homelab-service"
    MONITORING_NODE = "monitoring-node"
    RESEARCH_SANDBOX = "research-sandbox"
    TEMPORARY_BUILD_NODE = "temporary-build-node"
    GITHUB_MAINTAINER = "github-maintainer"

class NodeState(str, Enum):
    PROVISIONED = "provisioned"
    BOOTSTRAPPED = "bootstrapped"
    VALIDATED = "validated"
    READY = "ready"
    ASSIGNED = "assigned"
    REPORTING = "reporting"
    RETIRED = "retired"

class NodeResources(BaseModel):
    vcpu: int = Field(..., gt=0)
    ram_gb: int = Field(..., gt=0)
    disk_gb: int = Field(..., gt=0)

class NodeManifest(BaseModel):
    schema_version: int = Field(1, ge=1)
    name: str
    type: NodeType
    image: str
    state: NodeState
    snapshots: List[str] = Field(default_factory=list)
    repo: Optional[str] = None
    credential_ref: Optional[str] = None
    created: str
    expires: str
    resources: NodeResources
    network: str

class NodeRelease(BaseModel):
    IMAGE_VERSION: str
    ADMIN_USER: str
    TARGET: str
    L0_WRAPPER: str
    NODE_HOSTNAME: str
    L0_DATE: str
    NODE_TYPE: Optional[NodeType] = None
    L2_SCRIPT: Optional[str] = None
    AGENT_UID: Optional[int] = None
    AGENT_SUDO: Optional[str] = None

class LedgerAction(str, Enum):
    PAYLOAD_FIRE = "payload.fire"
    COLLECT_PULL = "collect.pull"
    CRED_STRAP = "cred.strap"
    CRED_SCRUB = "cred.scrub"
    CRED_NUKE = "cred.nuke"
    NODE_CREATE = "node.create"
    NODE_RESET = "node.reset"
    EVENT = "event"

class LedgerRecord(BaseModel):
    schema_version: int = Field(1, ge=1)
    ts: str
    actor: str
    action: LedgerAction
    node: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result: str
    sha256: Optional[Dict[str, str]] = None

class CredentialStatus(str, Enum):
    STRAPPED = "strapped"
    SCRUBBED = "scrubbed"
    NUKED = "nuked"

class CredentialRecord(BaseModel):
    id: str = Field(..., pattern=r"^cred:.+$")
    kind: str
    repo: str
    node: str
    last4: str
    expires: str
    scopes: List[str]
    status: CredentialStatus
    strapped_at: Optional[str] = None
    vault_ref: str

class PayloadTier(str, Enum):
    APPROVED = "approved"
    DRAFT = "draft"

class PayloadManifest(BaseModel):
    schema_version: int = Field(1, ge=1)
    name: str
    sha256: str
    tier: PayloadTier
    allowed_node_types: List[NodeType]
    allowed_states: List[NodeState]
    approved_by: str
    approved_at: str

class HandbackFile(BaseModel):
    path: str
    sha256: str

class HandbackManifest(BaseModel):
    schema_version: int = Field(1, ge=1)
    node: str
    ts: str
    files: List[HandbackFile]

class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"

class CheckResult(BaseModel):
    id: str
    name: str
    status: CheckStatus
    detail: Optional[str] = None

class Report(BaseModel):
    node: str
    ts: str
    kind: str  # pre|post
    checks: List[CheckResult]
    commit_range: Optional[str] = None
    pr_url: Optional[str] = None
    needs: List[str] = Field(default_factory=list)

class CredentialTemplate(BaseModel):
    scopes: List[str]
    ttl_days: int = Field(..., gt=0)

class ProjectConfig(BaseModel):
    repo: str
    image: str
    node_type: NodeType
    resources: NodeResources
    branch_prefix: str
    credential_template: CredentialTemplate
    env_refs: List[str] = Field(default_factory=list)
