import os
import yaml
from typing import Optional
from pathlib import Path
from library.models import NodeManifest, NodeState

class ManifestError(Exception):
    """Custom exception for manifest errors."""
    pass

class StateTransitionError(ManifestError):
    """Raised when a state transition is invalid."""
    pass

class ManifestManager:
    """Manages reading, writing, and state transitions for node manifests."""

    @staticmethod
    def load(file_path: Path) -> NodeManifest:
        """Loads and validates a node manifest from a YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {file_path}")
        
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            return NodeManifest.model_validate(data)
        except Exception as e:
            raise ManifestError(f"Failed to load manifest from {file_path}: {e}")

    @staticmethod
    def save(manifest: NodeManifest, file_path: Path) -> None:
        """Saves a node manifest to a YAML file, ensuring directories exist."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Dump with custom YAML styling
            data = manifest.model_dump(exclude_none=False)
            # Ensure enum values are serialized as strings
            data["type"] = manifest.type.value
            data["state"] = manifest.state.value
            data["resources"] = manifest.resources.model_dump()
            
            with open(file_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ManifestError(f"Failed to save manifest to {file_path}: {e}")

    @classmethod
    def transition(cls, manifest: NodeManifest, target_state: NodeState) -> NodeManifest:
        """Enforces legal state transitions according to the state machine.
        
        Valid transitions:
          - None -> provisioned (implicitly at creation)
          - provisioned -> bootstrapped
          - bootstrapped -> validated
          - validated -> ready
          - ready -> assigned
          - assigned -> reporting
          - reporting -> ready (reverted/reset)
          - reporting -> retired
          - * -> retired (any state can be retired)
        """
        current_state = manifest.state
        
        if current_state == target_state:
            return manifest  # No transition needed

        is_valid = False

        if target_state == NodeState.RETIRED:
            is_valid = True  # Any node can be retired
        elif current_state == NodeState.PROVISIONED:
            is_valid = target_state == NodeState.BOOTSTRAPPED
        elif current_state == NodeState.BOOTSTRAPPED:
            is_valid = target_state == NodeState.VALIDATED
        elif current_state == NodeState.VALIDATED:
            is_valid = target_state == NodeState.READY
        elif current_state == NodeState.READY:
            is_valid = target_state == NodeState.ASSIGNED
        elif current_state == NodeState.ASSIGNED:
            is_valid = target_state == NodeState.REPORTING
        elif current_state == NodeState.REPORTING:
            is_valid = target_state in (NodeState.READY, NodeState.RETIRED)

        if not is_valid:
            raise StateTransitionError(
                f"Invalid transition from '{current_state.value}' to '{target_state.value}'"
            )

        # Create a new manifest copy with updated state
        updated_manifest = manifest.model_copy(update={"state": target_state})
        return updated_manifest
