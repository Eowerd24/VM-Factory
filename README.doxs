# VM-Factory

`VM-Factory` is currently a planning and bootstrap repository for an AI Worker Factory / Node Lifecycle Pipeline. The repository describes a system for building credential-free Ubuntu golden images, cloning disposable worker VMs, assigning project work, collecting results, and resetting or retiring nodes. The current implementation in this repo is still early: two substantial planning documents and one Bash wrapper for a server VM golden-image layer.

Current status: planning/prototype. There is still no runnable application, package manifest, CI pipeline, or build system in the current snapshot, but the shell bootstrap layer now includes a shared core library and a dry-run smoke test. The repo is still early-stage rather than production-ready.

## Read First
- [AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md) / [AGENTS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.doxs)
- [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md) / [FIRE-AWAY.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.doxs)
- [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md) / [PROGRESS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.doxs)
- [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md) / [README.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.doxs)
- [ai-worker-factory-plan.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
- [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)

## What The Project Does
The current design documents define a VM-centric automation system with these major concerns:

- golden Ubuntu image creation
- node lifecycle management
- role-specific bootstrap layers
- isolated AI worker VMs
- credential injection and scrubbing
- workload assignment and report collection
- audit/ledger and state-manifest design
- future convergence with a panel/UI wrapper

The current scripts and engine library implement the core logic for the node lifecycle and the golden image VM preparation wrapper.

## Repository Structure
Current verified structure:

```text
.
├── AGENTS.docx
├── AGENTS.doxs
├── AGENTS.md
├── .gitignore
├── FIRE-AWAY.docx
├── FIRE-AWAY.doxs
├── FIRE-AWAY.md
├── PROGRESS.doxs
├── PROGRESS.md
├── PROGRESS.md.docx
├── README.doxs
├── README.md
├── README.md.docx
├── ai-worker-factory-plan.md
├── factory-panel-convergence.md
├── lib-l0-core.sh
├── l0-server-vm.sh
├── pyproject.toml
├── uv.lock
├── package.json
├── package-lock.json
├── library/
│   ├── credentials.py
│   ├── engine.py
│   ├── hypervisor.py
│   ├── ledger.py
│   ├── manifest.py
│   ├── models.py
│   ├── payloads.py
│   ├── reports.py
│   └── transport.py
├── scripts/
│   └── test.sh
└── tests/
    ├── test-l0-core-args.sh
    ├── test-l0-dry-run.sh
    └── test_library.py
```

File roles:

- [ai-worker-factory-plan.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md): primary product and architecture plan
- [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md): convergence plan between the factory and a panel-style wrapper
- [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh): shared L0 baseline library sourced by the VM wrapper
- [l0-server-vm.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh): current Bash VM golden image builder
- [library/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/): Python engine modules for managing nodes, state, credentials, ledger actions, hypervisors, and task reports
- [scripts/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/scripts/): unified repository-local validation script
- [tests/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/): shell and python tests verifying both dry-runs and library engine logic
- [.gitignore](file:///home/sarge/Desktop/AI-Factory/VM-Factory/.gitignore): repository-local ignore rules for disposable runtime, cache, coverage, editor, and secret-like files
- [pyproject.toml](file:///home/sarge/Desktop/AI-Factory/VM-Factory/pyproject.toml) & [uv.lock](file:///home/sarge/Desktop/AI-Factory/VM-Factory/uv.lock): Python dependencies configuration and lockfile managed by `uv`
- [package.json](file:///home/sarge/Desktop/AI-Factory/VM-Factory/package.json) & [package-lock.json](file:///home/sarge/Desktop/AI-Factory/VM-Factory/package-lock.json): Node.js packages for local command tooling (e.g. DeepSeek CLI)
- [AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md) / [AGENTS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.doxs): repository-specific instructions for coding agents
- [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md) / [FIRE-AWAY.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.doxs): autonomous execution contract inside the VM
- [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md) / [PROGRESS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.doxs): live operational state and handoff
- [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md) / [README.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.doxs): this documentation file
- `*.docx`: preserved legacy docs

## Requirements
Current verified requirements are minimal:

- Linux shell environment
- Bash
- Git
- `unzip` and `perl` (pre-installed, used for inspecting legacy docs)

Inferred runtime requirements for the shell bootstrap work, based on `l0-server-vm.sh`:

- Ubuntu-based target VM
- `sudo`
- `apt-get`
- `dpkg`
- `grep`
- `sed`
- `update-grub`
- `cloud-init` on the target image

These are implementation expectations, not a verified setup flow from this repo.

## Installation
The project dependencies are managed via `uv` (Python) and `npm` (Node.js). To initialize the environment:

```bash
# Set up Python virtual environment and install dependencies
uv sync

# Install Node.js dependencies
npm install
```

Useful verified entry commands:

```bash
cd /home/sarge/Desktop/AI-Factory/VM-Factory
pwd
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
find . -maxdepth 3 -type f | sort
```

## Configuration
No configuration templates or secret files exist in the current repository snapshot.

Security rule:

- do not add real credentials to this repository

If future work introduces configuration files, prefer example templates only.

Repository hygiene:

- `.gitignore` now excludes local virtualenvs, Python caches, pytest/coverage outputs, editor swap files, and `.env`-style local secret files.

## Running The Project
The project provides the `nodectl` CLI tool to orchestrate node lifecycle operations.

To run `nodectl` locally:

```bash
# Run with Python PYTHONPATH set to search local modules
PYTHONPATH=. uv run python -m nodectl --help
```

CLI commands available:
- `create`: Provision and bootstrap a new node from project config.
- `assign`: Assign a workload repo to a node and inject credentials.
- `collect`: Pull results from a node outbox directory and verify checksums.
- `reset`: Stop, revert a node to its `sx-ready` snapshot, scrub credentials, and restart.
- `destroy`: Permanently destroy a node, delete VM storage, and nuke credentials.
- `list`: Show all active node manifests.
- `ledger`: Query and stream the audit log ledger.

To test the CLI lifecycle locally with mock backends, pass the `--mock` flag or set the `MOCK_SSH=True` environment variable:

```bash
PYTHONPATH=. uv run python -m nodectl create node-01 ./tests/project.yaml --mock
PYTHONPATH=. uv run python -m nodectl list --mock
```

Current script status:
- dry-run validation command: `L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh --dry-run`
- intended privileged command on an Ubuntu target: `sudo bash ./l0-server-vm.sh --dry-run`
- current state: executable for dry-run validation; real system mutation still expects an Ubuntu-like target environment with `useradd`, `ufw`, `systemctl`, `dpkg`, and related base tools available.

## Testing
The validation suite runs both shell tests and Python unit tests:

```bash
# Run all tests and diff checks
bash scripts/test.sh

# Or run components separately:
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh
PYTHONPATH=. uv run pytest
```

The smoke test verifies full wrapper execution in non-root dry-run mode. It does not prove privileged runtime correctness on a target Ubuntu VM.

## Linting
No lint configuration or lint command was found.

Status: unimplemented. (Use `bash -n` for shell syntax check.)

## Type Checking
No type-check configuration was found.

Status: not applicable yet.

## Building
No build system or build command was found.

Status: unimplemented.

## Troubleshooting
- If `git` fails inside the sandbox due to `/etc/gitconfig` access, use:

```bash
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
```

- If `l0-server-vm.sh` cannot run, first verify whether `lib-l0-core.sh` exists in the repo. In the current snapshot it does.
- If a future agent claims the script works, require the exact command and validation result; syntax checking alone is insufficient.

## Security Notes
- This repo should remain credential-free.
- Do not commit tokens, PATs, private keys, `.env` files, or session material.
- Treat all VM/bootstrap automation as sensitive infrastructure code even when it is still early-stage.
- Do not expose services outside the VM without explicit human approval.

## Git Contribution Workflow
Current recommended flow:

```bash
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git switch -c agent/<task>-YYYYMMDD
git diff --check
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
git add <files>
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git commit -m "<focused message>"
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git push -u origin HEAD
```

Rules:

- use a dedicated branch
- preserve unknown work
- do not force-push
- do not merge automatically

## Current Maturity
Verified maturity assessment:

- product design: substantial
- implementation: minimal
- validation: minimal
- automation: not yet established in-repo

The next realistic work item is to broaden the L0 shell test coverage and then validate the bootstrap flow against a real disposable Ubuntu VM target.
