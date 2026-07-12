# VM-Factory

`VM-Factory` is an early implementation of an AI Worker Factory / Node Lifecycle Pipeline. The repository now contains executable bootstrap scripts, a Python node lifecycle engine, a Typer CLI, and a FastAPI + HTMX web panel for managing mock or libvirt-backed nodes.

Current status: bootstrap/prototype. The repository is runnable for local development and mock-backed validation, but privileged Ubuntu bootstrap behavior and real hypervisor-backed lifecycle flows are still only partially verified.

## Read First
- [AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md) / [AGENTS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.doxs)
- [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md) / [FIRE-AWAY.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.doxs)
- [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md) / [PROGRESS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.doxs)
- [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md) / [README.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.doxs)
- [ai-worker-factory-plan.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
- [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)

## What The Project Does
The repository currently implements these layers:

- L0 shell bootstrap for Ubuntu server golden-image preparation via [l0-server-vm.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh) and [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh)
- A Python engine under [library/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/) for manifests, ledgering, credentials, transport, hypervisor control, payload validation, reporting, and lifecycle verbs
- A Typer CLI in [nodectl.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/nodectl.py)
- A FastAPI + HTMX dashboard in [panel/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/panel/) for node creation, assignment, collection, reset, destruction, and ledger views
- Shell and Python validation under [tests/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/) with a canonical runner at [scripts/test.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/scripts/test.sh)

Planning documents still define the broader target architecture, especially around real hypervisor workflows, snapshot policy, credential boundaries, and convergence between the factory engine and the panel wrapper.

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
├── nodectl.py
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
├── panel/
│   ├── main.py
│   ├── static/
│   │   └── style.css
│   └── templates/
│       ├── index.html
│       └── partials/
│           ├── ledger_list.html
│           └── node_list.html
├── scripts/
│   └── test.sh
└── tests/
    ├── test-l0-core-args.sh
    ├── test-l0-dry-run.sh
    ├── test_library.py
    └── test_panel.py
```

File roles:

- [ai-worker-factory-plan.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md): primary product and architecture plan
- [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md): convergence plan between the factory and a panel-style wrapper
- [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh): shared L0 baseline library sourced by the VM wrapper
- [l0-server-vm.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh): current Bash VM golden image builder
- [nodectl.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/nodectl.py): Typer-based command-line interface tool
- [library/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/): Python engine modules for manifests, hypervisor operations, credentials, ledgering, payload validation, reporting, and transport
- [panel/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/panel/): FastAPI + HTMX dashboard web app code, templates, and styles
- [scripts/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/scripts/): unified repository-local validation script
- [tests/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/): shell and Python tests covering dry-run shell flows, library behavior, and panel routes
- [.gitignore](file:///home/sarge/Desktop/AI-Factory/VM-Factory/.gitignore): repository-local ignore rules for disposable runtime, cache, coverage, editor, and secret-like files
- [pyproject.toml](file:///home/sarge/Desktop/AI-Factory/VM-Factory/pyproject.toml) and [uv.lock](file:///home/sarge/Desktop/AI-Factory/VM-Factory/uv.lock): Python package configuration and lockfile managed by `uv`
- [package.json](file:///home/sarge/Desktop/AI-Factory/VM-Factory/package.json) and [package-lock.json](file:///home/sarge/Desktop/AI-Factory/VM-Factory/package-lock.json): Node.js dependency manifests for repository-local CLI tooling

## Requirements
Current verified requirements:

- Linux shell environment
- Bash
- Git
- Python 3.12+
- `uv`
- Node.js and `npm`

Additional expectations inferred from the bootstrap layer:

- Ubuntu-based target VM for real `l0-server-vm.sh` execution
- `sudo`, `apt-get`, `dpkg`, `grep`, `sed`, and `update-grub` on the target image
- `cloud-init` present for the intended VM image path
- libvirt for non-mock hypervisor execution

These target-runtime requirements are partially inferred from the implementation and are not all verified end-to-end from this repository session.

## Installation
Initialize repository-local dependencies with:

```bash
uv sync
npm install
```

Useful repo inspection commands:

```bash
cd /home/sarge/Desktop/AI-Factory/VM-Factory
pwd
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
find . -maxdepth 3 -type f | sort
```

## Configuration
No committed real secret material or `.env` templates exist in the current snapshot.

Relevant environment variables:

- `NODEFACTORY_STATE`: overrides the engine and panel state directory; defaults to `~/.local/state/nodefactory`
- `MOCK_SSH=true`: forces mock transport/hypervisor mode for the panel and related local flows
- `L0_ALLOW_NON_ROOT=1`: allows repository-local non-root dry-run testing for `l0-server-vm.sh`

Security rule:

- do not add real credentials to this repository

## Running The Project
The repository currently exposes three practical entry points.

### Shell bootstrap dry-run

```bash
L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh --dry-run
```

Intended privileged dry-run on a real Ubuntu target:

```bash
sudo bash ./l0-server-vm.sh --dry-run
```

### Command-line interface

```bash
PYTHONPATH=. uv run python -m nodectl --help
```

Example mock-backed lifecycle calls:

```bash
cat > /tmp/node-01.yaml <<'EOF'
repo: https://github.com/Eowerd24/VM-Factory.git
image: gold-server-2404-v1
node_type: ai-worker
resources:
  vcpu: 2
  ram_gb: 4
  disk_gb: 20
branch_prefix: ai/node-01
credential_template:
  scopes:
    - contents:rw
    - pull_requests:rw
  ttl_days: 14
EOF
PYTHONPATH=. uv run python -m nodectl create node-01 /tmp/node-01.yaml --mock
PYTHONPATH=. uv run python -m nodectl list --mock
PYTHONPATH=. uv run python -m nodectl ledger --mock
```

### Web dashboard

```bash
MOCK_SSH=true PYTHONPATH=. uv run uvicorn panel.main:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

The panel automatically falls back to mock backends when `MOCK_SSH=true` or when `/var/run/libvirt/libvirt-sock` is unavailable.

## Testing
The canonical validation suite is:

```bash
bash scripts/test.sh
```

Component-level commands:

```bash
bash -n lib-l0-core.sh
bash -n l0-server-vm.sh
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh
PYTHONPATH=. uv run pytest
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git diff --check
```

Coverage today:

- shell syntax validation for the L0 scripts
- non-root dry-run shell validation
- shell argument parser coverage
- Python unit/integration tests for the engine library and the FastAPI panel

## Linting
No dedicated lint configuration exists yet.

Current substitute:

- `bash -n` for shell syntax
- `git diff --check` for whitespace/diff hygiene

## Type Checking
No type-check configuration exists yet.

Status: unimplemented.

## Building
No separate build pipeline or packaging build step is defined yet.

Status: unimplemented.

## Troubleshooting
- If `git` tries to read system config unexpectedly, use `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git ...`
- If the panel cannot reach libvirt locally, set `MOCK_SSH=true` to force the mock backend
- If `l0-server-vm.sh` fails, verify that [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh) exists and rerun the documented dry-run path first
- If a workflow claims real bootstrap success, require the exact command and target environment; local dry-run validation is not equivalent to a privileged Ubuntu mutation run

## Security Notes
- This repo should remain credential-free
- Do not commit tokens, PATs, private keys, `.env` files, cookies, or session material
- Treat VM/bootstrap automation as sensitive infrastructure code even in prototype form
- Do not expose services outside the VM without explicit human approval

## Git Contribution Workflow
Current recommended flow:

```bash
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git switch -c agent/<task>-YYYYMMDD
bash scripts/test.sh
git diff --check
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
git add <files>
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git commit -m "<focused message>"
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git push -u origin HEAD
```
