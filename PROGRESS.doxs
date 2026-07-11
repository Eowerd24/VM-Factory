# PROGRESS.md

## Current Phase
Phase: Repository bootstrap and baseline verification

## Current Milestone
Milestone: Restore executable shell bootstrap baseline and keep repository operating docs accurate

## Current Objective
Objective: Maintain the bootstrap baseline, keep operating docs accurate, and add basic repository hygiene where local runtime artifacts appear.

## Baton Holder
Baton holder: Agent

## Last Updated
Last updated: 2026-07-11

## Completed Work
- W-001 — Repository root confirmed at [VM-Factory](file:///home/sarge/Desktop/AI-Factory/VM-Factory).
- W-002 — Current git state inspected: branch, remote, short history, and working tree.
- W-003 — Repository tree inspected.
- W-004 — Existing documentation inspected:
  - [ai-worker-factory-plan.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/ai-worker-factory-plan.md)
  - [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md)
  - legacy `AGENTS.docx`
  - legacy `FIRE-AWAY.docx`
  - legacy `PROGRESS.md.docx`
  - legacy `README.md.docx`
- W-005 — Existing implementation inspected: [l0-server-vm.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/l0-server-vm.sh).
- W-006 — Dedicated branch created: `agent/project-bootstrap-20260710`.
- W-007 — Canonical markdown operating docs created to replace placeholder/legacy guidance while preserving the legacy `.docx` files.
- W-008 — Implemented [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh) to supply the wrapper's shared CLI/runtime helpers and conservative L0 baseline actions.
- W-009 — Added [tests/test-l0-dry-run.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test-l0-dry-run.sh) to validate full wrapper execution in non-root dry-run mode.
- W-010 — Added [tests/test-l0-core-args.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test-l0-core-args.sh) to verify the shared shell argument parser independently.
- W-011 — Added [scripts/test.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/scripts/test.sh) as the canonical repository-local validation entry point for the shell layer.
- W-012 — Committed the canonical test entry point and refreshed the handoff.
- W-015 — Completed project inspection, verified all tests pass, and checked out new branch `agent/project-bootstrap-20260711`.
- W-016 — Aligned `.doxs` and `.md` documentation files to contain the complete, project-specific operating rules and operational progress.
- W-017 — Added a conservative repository [.gitignore](file:///home/sarge/Desktop/AI-Factory/VM-Factory/.gitignore) for local Python/runtime/cache/editor/secret-like artifacts and updated docs to reflect it.
- W-018 — Updated operating documents ([AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md)/[AGENTS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.doxs), [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md)/[FIRE-AWAY.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.doxs), [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md)/[README.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.doxs), [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md)/[PROGRESS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.doxs)) to reflect Python/Node packages and pytest unit tests correctly.
- W-019 — Expanded the unit test suite in [tests/test_library.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test_library.py) to achieve full coverage of the Python engine library including `CredentialManager`, `PayloadValidator`, `ReportParser`, `NodeLifecycleEngine`, and the CLI layer.
- W-020 — Added mock state persistence to `MockHypervisorBackend` in [library/hypervisor.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/hypervisor.py) so mock VM topologies are saved to disk and persist across CLI invocations.
- W-021 — Implemented the Typer-based command-line interface tool [nodectl.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/nodectl.py) at the repository root to expose all lifecycle verbs (`create`, `assign`, `collect`, `reset`, `destroy`, `list`, and `ledger`).
- W-022 — Registered the `nodectl` command in [pyproject.toml](file:///home/sarge/Desktop/AI-Factory/VM-Factory/pyproject.toml) and verified CLI invocations under mock settings.
- W-023 — Bootstrapped the FastAPI + HTMX NodePanel frontend dashboard inside the [panel/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/panel/) directory, featuring a responsive, premium dark-mode layout with real-time HTMX-driven auto-polling nodes list and ledger audit trails.
- W-024 — Implemented comprehensive route integration tests in [tests/test_panel.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test_panel.py) verifying index rendering, form actions (`create`, `assign`, `collect`, `reset`, and `destroy`), and HTMX refresh fragments.
- W-025 — Updated project dependencies in [pyproject.toml](file:///home/sarge/Desktop/AI-Factory/VM-Factory/pyproject.toml) to include FastAPI, Jinja2, Uvicorn, python-multipart, and HTTPX for test execution.

## Work In Progress
None.

## Next Authorized Actions
- W-019 — Validate the bootstrap flow on a real disposable Ubuntu VM target.
- W-020 — Expand the python-based library engine integration and convergence with nodepanel.

## Backlog
- B-001 — Decide and add the first real repository manifest/configuration strategy once code beyond Bash is introduced.
- B-002 — Add broader shell validation/test workflow for bootstrap scripts.
- B-004 — Convert or retire legacy `.docx` docs after the markdown workflow is accepted.
- B-005 — Revisit `.gitignore` if additional generated state directories or tool caches become part of the repo workflow.

## Locked Decisions
- D-001 — Work remains inside the dedicated VM and repository boundary.
- D-002 — Preserve unknown user work; no destructive git cleanup.
- D-003 — Canonical operating docs are Markdown files at repo root: [AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md), [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md), [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md), [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md).
- D-004 — Legacy `.docx` root docs are preserved for now and not overwritten.
- D-005 — Branch workflow uses a dedicated agent branch; no automatic merge to `main`.
- D-006 — Maintain both `.doxs` and `.md` files as identical full-content markdown files to ensure compatibility with automated verification systems.

## Open Questions
None currently. No human decision is blocking the next repository-local implementation step.

## Active Blockers
No active human-only blockers are currently recorded.

## Known Issues
- KI-001 — Privileged runtime is only partially verified
  - Observed behavior: the wrapper now executes in non-root dry-run mode, but no real Ubuntu VM mutation run has been performed from this repo session
  - Expected behavior: the bootstrap flow should be exercised on an actual disposable Ubuntu target
  - Reproduction: compare available local validation to the intended `sudo bash ./l0-server-vm.sh --dry-run` or real run path
  - Impact: Medium
  - Status: Open
- KI-002 — Repository is documentation/planning only
  - Observed behavior: early version of the library engine with python unit tests, dependency manifests, and lockfiles are now implemented. Additional features and full convergence with nodepanel are planned.
  - Expected behavior: future implementation work will expand these as the codebase becomes real
  - Reproduction: [library/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/) and [tests/test_library.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test_library.py)
  - Impact: Medium
  - Status: Partially Resolved
- KI-003 — Legacy root docs are stored as `.docx`
  - Observed behavior: the previous operating docs were Word documents rather than editable markdown
  - Expected behavior: repository-operating docs should be plain text under version control
  - Reproduction: inspect root filenames and unzip the `.docx` files
  - Impact: Medium
  - Status: Open
- KI-004 — Push remains unavailable from the current VM git install
  - Observed behavior: `git push` fails because `git remote-https` is unavailable
  - Expected behavior: standard HTTPS remotes should be usable when push is needed
  - Reproduction: `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git push -u origin agent/project-bootstrap-20260711`
  - Impact: Medium
  - Status: Open

## Validation Status
- `bash -n lib-l0-core.sh` — passed
- `bash -n l0-server-vm.sh` — passed
- `bash tests/test-l0-dry-run.sh` — passed
- `bash tests/test-l0-core-args.sh` — passed
- `PYTHONPATH=. uv run pytest` — passed
- `bash scripts/test.sh` — passed
- `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git diff --check` — passed
- `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch` — passed

## Recent Work Log
- 2026-07-11 — Bootstrapped NodePanel Web Frontend
  - Worker: Agent
  - Summary: Developed a FastAPI + HTMX based NodePanel web dashboard under `panel/` featuring real-time node auto-polling, dynamic ledger audits, and HTML form workflows for creation, assignment, collection, reset, and destruction. Created a complete test suite `tests/test_panel.py` covering all web routes and form integrations.
  - Validation: `bash scripts/test.sh` passed.
  - Git state: branch `agent/project-bootstrap-20260711`, local modifications uncommitted.
- 2026-07-11 — Implemented nodectl CLI and expanded engine unit tests
  - Worker: Agent
  - Summary: Built the Typer-based `nodectl` CLI tool supporting all lifecycle engine verbs. Added json state persistence for MockHypervisorBackend so CLI invocations retain mock state. Expanded the pytest test suite in `tests/test_library.py` to cover all library components and CLI verbs.
  - Validation: `bash scripts/test.sh` passed.
  - Git state: branch `agent/project-bootstrap-20260711`, local modifications uncommitted.
- 2026-07-11 — Aligned operating docs, synchronized doxs/md files, and verified tests
  - Worker: Agent
  - Summary: Updated AGENTS, FIRE-AWAY, README, and PROGRESS files to include Python/Node setups, pytest unit tests, and standardized links (file:/// scheme, no backticks). Overwrote all `.doxs` counterparts to ensure exact equality.
  - Validation: `bash scripts/test.sh` passed.
  - Git state: branch `agent/project-bootstrap-20260711`, documentation and `.gitignore` updates staged/stashed.
- 2026-07-11 — Repository ignore policy added
  - Worker: Agent
  - Summary: Added a conservative root `.gitignore` for local Python/runtime/cache/editor/secret-like artifacts and updated README/PROGRESS to reflect the new hygiene baseline.
  - Validation:
    - `bash -n l0-server-vm.sh` passed
    - `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git diff --check` passed
    - `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch` passed
  - Git state: branch `agent/project-bootstrap-20260711`, `.gitignore` and doc changes uncommitted.
- 2026-07-10 — Canonical shell test entry point validated
  - Worker: Agent
  - Summary: Verified `bash scripts/test.sh` as the single repository-local validation command for the current shell layer.
  - Validation:
    - `bash scripts/test.sh` passed
    - `env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch` passed
  - Git state: branch `agent/project-bootstrap-20260710`, test-runner changes committed.

## Git Branch and Commit State
- Current branch: `agent/project-bootstrap-20260711`
- Base branch at start: `agent/project-bootstrap-20260710`
- HEAD commit at start: `a05af43` (`test: add canonical shell validation entrypoint`)
- Working tree state at start: clean
- Current HEAD commit: `41d64c3`
- Commit state for current work: uncommitted NodePanel implementation, tests, and dependency updates present

## Exact Resume Point
Resume from:
1. run `bash scripts/test.sh`
2. review status and run `git diff --check`
3. commit the web panel, tests, and pyproject.toml changes
4. proceed with validating the bootstrap flow on a real disposable VM target (W-019)
