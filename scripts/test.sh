#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "==> Shell syntax"
bash -n lib-l0-core.sh
bash -n l0-server-vm.sh

echo "==> Shell tests"
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh

echo "==> Python tests"
PYTHONPATH=. uv run pytest

echo "==> Diff hygiene"
env HOME="${REPO_ROOT}" GIT_CONFIG_NOSYSTEM=1 git diff --check

echo "test suite passed"
