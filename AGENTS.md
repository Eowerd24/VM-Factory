# AGENTS.md

## Purpose
This repository currently captures the design and bootstrap baseline for the AI Worker Factory / Node Lifecycle Pipeline. It is not yet a runnable application. The current implementation footprint is:

- planning documents in Markdown
- legacy placeholder documents stored as `.docx`
- one shell wrapper, [`l0-server-vm.sh`](/home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh), for building a server VM golden-image layer

The immediate engineering goal is to turn the planning repo into a usable bootstrap/codebase for autonomous VM-oriented development without losing any existing user work.

## Repository Boundaries
Work only inside this repository and repository-local artifacts.

Do not modify:

- the physical host
- the hypervisor
- other VMs
- unrelated repositories
- host networking, firewall, SSH, storage, or DNS
- production systems or live infrastructure

The current repo root contains only:

- [`ai-worker-factory-plan.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
- [`factory-panel-convergence.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)
- [`l0-server-vm.sh`](/home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh)
- legacy `.docx` docs

## Required Reading Order
Read these in order before making changes:

1. [`AGENTS.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md)
2. [`FIRE-AWAY.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md)
3. [`PROGRESS.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md)
4. [`README.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/README.md)
5. [`ai-worker-factory-plan.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
6. [`factory-panel-convergence.md`](/home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)
7. [`l0-server-vm.sh`](/home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh)

Also inspect the current git state before editing.

## Mandatory Preflight Checks
Run these from the repository root at the start of each substantial session:

```bash
pwd
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git remote -v
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git log --oneline --decorate -n 20
find . -maxdepth 3 -type f | sort
```

Then verify the current implementation surface:

```bash
bash -n l0-server-vm.sh
```

Preflight requirements:

- confirm you are in `/home/sarge/Desktop/AI-Factory/VM-Factory`
- preserve unknown working-tree changes
- verify whether referenced files actually exist before assuming the script or docs are complete
- treat missing files as repo-state facts, not as user mistakes

## Actual Setup Commands
There is no installable application or package manager environment in the current repository snapshot.

Verified commands:

```bash
bash -n lib-l0-core.sh
bash -n l0-server-vm.sh
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh
```

Current execution reality:

- `l0-server-vm.sh` is a Bash script intended to run on Ubuntu with `sudo`
- it depends on `lib-l0-core.sh`, which is now present in this repository
- a non-root dry-run smoke test exists
- privileged runtime behavior on a real Ubuntu target remains only partially verified

Use dry-run invocation for repository-local validation:

```bash
L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh --dry-run
```

Use privileged dry-run on a real target VM when available:

```bash
sudo bash ./l0-server-vm.sh --dry-run
```

Status: dry-run path is verified locally; privileged runtime remains partially verified.

## Actual Test, Lint, Type-Check, Build, and Run Commands
Current verified command set:

```bash
bash -n lib-l0-core.sh
bash -n l0-server-vm.sh
bash tests/test-l0-dry-run.sh
bash tests/test-l0-core-args.sh
git diff --check
```

Current state by category:

- Test: no test suite exists yet
- Lint: no linter config or lint command exists yet
- Type-check: not applicable yet; no type-check configuration exists
- Build: no build system or build manifest exists yet
- Run: no runnable application exists yet

If you add any of the above, document the exact command in the same change.

## Dependency Management Rules
Current repo state:

- no dependency manifest
- no lockfile
- no CI config
- no build config
- no package manager config

Rules:

- do not invent a package manager without a strong repo-backed reason
- if you add Python code, add a real manifest and keep installs repository-local
- if you add Node code, choose one package manager and commit its lockfile
- if you add shell tooling dependencies, document them in `README.md` and `PROGRESS.md`
- do not install global language packages when a repository-local alternative exists
- do not add heavyweight infrastructure tooling speculatively

## Git Workflow
Default workflow for this repo:

1. inspect the working tree first
2. create or continue a dedicated branch
3. make the smallest coherent change
4. validate the relevant commands
5. update `README.md` and `PROGRESS.md` when behavior or project state changes
6. create focused commits
7. push only if authentication already works
8. do not merge automatically

## Branch Naming
Use:

```text
agent/<short-task>-YYYYMMDD
```

For repository bootstrap work, prefer:

```text
agent/project-bootstrap-YYYYMMDD
```

## Commit Expectations
Each commit must:

- be focused and reviewable
- reflect real verified work
- avoid mixing unrelated cleanup with functional changes
- not include secrets, generated junk, or host-specific artifacts
- update docs when the repo state changes

Good commit style:

```text
docs: bootstrap repository operating docs
```

## Secret Handling Rules
Never commit or expose:

- tokens
- PATs
- SSH private keys
- `.env` files with real values
- cookies
- host credentials
- VM credentials

This repository is currently documentation-heavy and should remain secret-free. Check staged changes before every commit.

## Documentation Rules
Documentation must reflect the real repository, not the intended future system.

Rules:

- keep `README.md` human-facing
- keep `AGENTS.md` for agent operating rules
- keep `FIRE-AWAY.md` for autonomous execution policy
- keep `PROGRESS.md` as the live handoff
- preserve legacy `.docx` files unless explicitly asked to remove or convert them
- clearly label anything unverified rather than guessing

## Validation Requirements
Before finishing a work unit, run all relevant available checks. For the current repo, that minimally means:

```bash
bash -n l0-server-vm.sh
git diff --check
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
```

If you add new executable code, add and run the strongest local validation supported by that change.

## Prohibited Destructive Actions
Never run unless the human explicitly instructs it:

- `git reset --hard`
- `git clean -fd`
- `git clean -fdx`
- `git push --force`
- `git push --force-with-lease`
- destructive migrations
- credential rotation
- host or hypervisor modification

Also prohibited:

- deleting unknown files because they seem unused
- overwriting legacy docs without first reading them
- claiming a script works when only syntax was checked

## Conditions Requiring Human Input
Stop and use the `WAITING_FOR_HUMAN` format in `FIRE-AWAY.md` only when blocked by:

- a missing secret or account authorization
- an unavoidable host or hypervisor change
- a destructive or irreversible migration
- an architecture/product decision with major consequences and no governing doc
- a persistent blocker after multiple grounded attempts
- a conflict between repository authority documents that cannot be resolved by specificity or recency

Do not stop for routine implementation work, missing tests, or ordinary repo cleanup.

## Expected Final Report Format
End each substantial run with:

1. `Outcome`: complete, partially complete, or waiting for human
2. `What changed`: concise summary
3. `Validation`: each command run and result
4. `Git state`: branch, commit hash, pushed state, remaining changes
5. `Uncertainties`: only real unresolved items
6. `Next recommended task`: one concrete next step

## Autonomous Authority
Future agents are authorized to proceed autonomously with normal repository-local development work, including:

- reading files
- editing project files
- running tests
- fixing failures
- adding tests
- updating documentation
- creating a branch
- creating focused commits
- installing repository-local dependencies

They must stop before:

- production deployment
- destructive migrations
- credential rotation
- force-pushing
- rewriting shared history
- modifying the host or hypervisor
- exposing services outside the VM
- making unresolved large-consequence product or architecture decisions
