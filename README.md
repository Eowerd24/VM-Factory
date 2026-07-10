# VM-Factory

`VM-Factory` is currently a planning and bootstrap repository for an AI Worker Factory / Node Lifecycle Pipeline. The repository describes a system for building credential-free Ubuntu golden images, cloning disposable worker VMs, assigning project work, collecting results, and resetting or retiring nodes. The current implementation in this repo is still early: two substantial planning documents and one Bash wrapper for a server VM golden-image layer.

Current status: planning/prototype. There is still no runnable application, package manifest, CI pipeline, or build system in the current snapshot, but the shell bootstrap layer now includes a shared core library and a dry-run smoke test. The repo is still early-stage rather than production-ready.

## Read First
- [`AGENTS.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md)
- [`FIRE-AWAY.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md)
- [`PROGRESS.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md)
- [`ai-worker-factory-plan.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
- [`factory-panel-convergence.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)

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

The current script implements only a narrow slice of that plan: an L0 wrapper intended to harden and prepare a server VM golden baseline.

## Repository Structure
Current verified structure:

```text
.
├── AGENTS.docx
├── AGENTS.doxs
├── AGENTS.md
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
└── tests/
```

File roles:

- `ai-worker-factory-plan.md`: primary product and architecture plan
- `factory-panel-convergence.md`: convergence plan between the factory and a panel-style wrapper
- `lib-l0-core.sh`: shared L0 baseline library sourced by the VM wrapper
- `l0-server-vm.sh`: current Bash implementation artifact
- `tests/`: shell smoke validation for the bootstrap layer
- `AGENTS.md`: repository-specific instructions for coding agents
- `FIRE-AWAY.md`: autonomous execution contract inside the VM
- `PROGRESS.md`: live operational state and handoff
- `*.docx`: preserved legacy docs
- `*.doxs`: compatibility pointers to the markdown docs

## Requirements
Current verified requirements are minimal:

- Linux shell environment
- Bash
- Git
- `unzip` and `perl` were available in the current VM and were used to inspect legacy docs

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
There is no repository-local install process yet because there is no package manifest or runnable app.

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

## Running The Project
No runnable application exists yet.

Current script status:

- dry-run validation command: `L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh --dry-run`
- intended privileged command on an Ubuntu target: `sudo bash ./l0-server-vm.sh --dry-run`
- current state: executable for dry-run validation; real system mutation still expects an Ubuntu-like target environment with `useradd`, `ufw`, `systemctl`, `dpkg`, and related base tools available

## Testing
The repo now has a minimal shell smoke test:

```bash
bash scripts/test.sh
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh
```

Other available validation:

```bash
bash scripts/test.sh
bash -n lib-l0-core.sh
bash -n l0-server-vm.sh
```

The smoke test verifies full wrapper execution in non-root dry-run mode. It does not prove privileged runtime correctness on a target Ubuntu VM.

## Linting
No lint configuration or lint command was found.

Status: unimplemented.

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

- If `l0-server-vm.sh` cannot run, first verify whether `lib-l0-core.sh` exists in the repo. In the current snapshot it does not.
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
