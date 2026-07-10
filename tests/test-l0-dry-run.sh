#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

OUTPUT_FILE="${TMP_DIR}/dry-run.log"
NODE_RELEASE_PATH="${TMP_DIR}/node-release"

(
    cd "${REPO_ROOT}"
    L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh \
        --dry-run \
        --node-release "${NODE_RELEASE_PATH}" \
        --image-version "test-image-v1"
) >"${OUTPUT_FILE}" 2>&1

grep -q "L0 CORE" "${OUTPUT_FILE}"
grep -q "L0 SERVER-VM COMPLETE" "${OUTPUT_FILE}"
grep -q "Server VM golden baseline ready." "${OUTPUT_FILE}"
grep -q "Running non-root in dry-run mode for validation" "${OUTPUT_FILE}"

if [[ -e "${NODE_RELEASE_PATH}" ]]; then
    echo "node-release should not be written during dry-run" >&2
    exit 1
fi

echo "dry-run smoke test passed"
