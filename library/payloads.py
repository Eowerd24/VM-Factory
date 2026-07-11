import hashlib
from pathlib import Path
from library.models import PayloadManifest, NodeType, NodeState, PayloadTier

class PayloadValidationError(Exception):
    """Raised when payload validation or gating checks fail."""
    pass

class PayloadValidator:
    """Validates payloads against metadata manifests and enforces security gates."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Calculates the SHA-256 hash of a file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Payload file not found: {file_path}")
        
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception as e:
            raise PayloadValidationError(f"Failed to hash payload file {file_path}: {e}")

    @classmethod
    def validate(cls, payload_path: Path, manifest: PayloadManifest, node_type: NodeType, node_state: NodeState, is_mock: bool = False) -> None:
        """Validates the payload file against its manifest and executes safety gating checks."""
        # 1. Verify sha256 checksum
        actual_sha = cls.calculate_sha256(payload_path)
        if actual_sha != manifest.sha256:
            raise PayloadValidationError(
                f"Checksum mismatch for '{payload_path.name}': "
                f"expected {manifest.sha256}, got {actual_sha}"
            )

        # 2. Gating: node type check
        if node_type not in manifest.allowed_node_types:
            raise PayloadValidationError(
                f"Payload '{manifest.name}' is not allowed on node type '{node_type.value}'"
            )

        # 3. Gating: node state check
        if node_state not in manifest.allowed_states:
            raise PayloadValidationError(
                f"Payload '{manifest.name}' is not allowed in node state '{node_state.value}'"
            )

        # 4. Gating: draft tier restrictions (B5 guardrail)
        if manifest.tier == PayloadTier.DRAFT:
            # Draft payloads are only allowed in Mock or research-sandbox environments
            is_sandbox = (node_type == NodeType.RESEARCH_SANDBOX)
            if not (is_mock or is_sandbox):
                raise PayloadValidationError(
                    f"Draft payload '{manifest.name}' can only run on mock backend or research-sandbox nodes"
                )
