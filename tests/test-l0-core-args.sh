#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${REPO_ROOT}/lib-l0-core.sh"

DRY_RUN=0
ADMIN_USER=admin
SSH_PORT=22
NODE_RELEASE=/etc/node-release
IMAGE_VERSION=gold-unknown-v0
NODE_HOSTNAME=original-host

parse_l0_args \
    --dry-run \
    --admin-user builder \
    --ssh-port 2222 \
    --node-release /tmp/node-release.test \
    --image-version gold-test-v2 \
    --hostname test-node

[[ "${DRY_RUN}" -eq 1 ]]
[[ "${ADMIN_USER}" == "builder" ]]
[[ "${SSH_PORT}" == "2222" ]]
[[ "${NODE_RELEASE}" == "/tmp/node-release.test" ]]
[[ "${IMAGE_VERSION}" == "gold-test-v2" ]]
[[ "${NODE_HOSTNAME}" == "test-node" ]]

echo "argument parsing test passed"
