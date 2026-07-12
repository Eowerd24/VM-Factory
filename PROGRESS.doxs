# PROGRESS.md

## Current Phase
Phase: Bootstrap implementation and documentation alignment

## Current Milestone
Milestone: Keep the executable bootstrap/codebase and operating docs synchronized

## Current Objective
Objective: Maintain accurate repository docs for the shell bootstrap layer, Python engine, CLI, web panel, and current validation workflow while preserving unrelated local artifacts.

## Baton Holder
Baton holder: Agent

## Last Updated
Last updated: 2026-07-12

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
- W-007 — Canonical markdown operating docs created while preserving the legacy `.docx` files.
- W-008 — Implemented [lib-l0-core.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/lib-l0-core.sh) to supply the wrapper's shared CLI/runtime helpers and conservative L0 baseline actions.
- W-009 — Added [tests/test-l0-dry-run.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test-l0-dry-run.sh) to validate full wrapper execution in non-root dry-run mode.
- W-010 — Added [tests/test-l0-core-args.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test-l0-core-args.sh) to verify the shared shell argument parser independently.
- W-011 — Added [scripts/test.sh](file:///home/sarge/Desktop/AI-Factory/VM-Factory/scripts/test.sh) as the canonical repository-local validation entry point for the shell layer.
- W-012 — Added a conservative repository [.gitignore](file:///home/sarge/Desktop/AI-Factory/VM-Factory/.gitignore) for local Python/runtime/cache/editor/secret-like artifacts.
- W-013 — Implemented the Python engine modules in [library/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/) covering manifests, credentials, hypervisor backends, ledgering, payload validation, reporting, transport, and lifecycle orchestration.
- W-014 — Added and expanded [tests/test_library.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test_library.py) to cover the Python engine library and CLI behavior.
- W-015 — Implemented the Typer-based CLI [nodectl.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/nodectl.py) and registered it in [pyproject.toml](file:///home/sarge/Desktop/AI-Factory/VM-Factory/pyproject.toml).
- W-016 — Added mock state persistence to [library/hypervisor.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/library/hypervisor.py) so mock VM state survives multiple CLI/panel interactions.
- W-017 — Bootstrapped the FastAPI + HTMX NodePanel web dashboard inside [panel/](file:///home/sarge/Desktop/AI-Factory/VM-Factory/panel/).
- W-018 — Added [tests/test_panel.py](file:///home/sarge/Desktop/AI-Factory/VM-Factory/tests/test_panel.py) covering index rendering, HTMX refresh fragments, and lifecycle form actions.
- W-019 — Updated dependency manifests and lockfiles for the Python/web stack and repo-local Node tooling.
- W-020 — Refreshed [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md), [README.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.doxs), [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md), and [PROGRESS.doxs](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.doxs) to match the actual repository state on 2026-07-12.

## Work In Progress
None.

## Next Authorized Actions
- W-021 — Validate a real libvirt-backed lifecycle flow beyond mock mode.
- W-022 — Exercise the L0 bootstrap wrapper on a disposable Ubuntu target with privileged dry-run or real mutation validation.

## Backlog
- B-001 — Converge the panel wrapper and factory engine further around the roadmap in [factory-panel-convergence.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/factory-panel-convergence.md).
- B-002 — Add stronger repo hygiene around tracked runtime artifacts if additional generated files continue appearing in the working tree.
- B-003 — Convert or retire legacy `.docx` docs after the markdown workflow is fully accepted.
- B-004 — Add linting and type-checking only when there is enough implemented code to justify the maintenance overhead.

## Locked Decisions
- D-001 — Work remains inside the dedicated VM and repository boundary.
- D-002 — Preserve unknown user work; no destructive git cleanup.
- D-003 — Canonical operating docs are Markdown files at repo root: [AGENTS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/AGENTS.md), [FIRE-AWAY.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/FIRE-AWAY.md), [PROGRESS.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/PROGRESS.md), [README.md](file:///home/sarge/Desktop/AI-Factory/VM-Factory/README.md).
- D-004 — Legacy `.docx` root docs are preserved for now and not overwritten.
- D-005 — Branch workflow uses a dedicated agent branch; no automatic merge to `main`.
- D-006 — Maintain both `.doxs` and `.md` files as identical full-content markdown files to ensure compatibility with automated verification systems.

## Open Questions
None currently.

## Active Blockers
No active human-only blockers are currently recorded.

## Known Issues
- KI-001 — Privileged bootstrap runtime remains only partially verified
  - Observed behavior: `l0-server-vm.sh` passes syntax checks and non-root dry-run validation locally, but no privileged Ubuntu run was executed in this session
  - Expected behavior: the bootstrap flow should be exercised with `sudo` on a disposable Ubuntu target
  - Impact: Medium
  - Status: Open
- KI-002 — Real hypervisor-backed lifecycle flow remains less verified than mock mode
  - Observed behavior: CLI and panel flows are covered under mock backends; libvirt-backed execution paths are present but not equally exercised
  - Expected behavior: create/assign/collect/reset/destroy should be validated against a disposable real target
  - Impact: Medium
  - Status: Open
- KI-003 — Runtime artifact hygiene is incomplete
  - Observed behavior: tracked `__pycache__` content can still appear in the working tree, including unrelated `.pyc` changes
  - Expected behavior: local runtime artifacts should stay out of normal source-control churn
  - Impact: Low
  - Status: Open

## Validation Status
- `bash -n l0-server-vm.sh` — passed

## Recent Work Log
- 2026-07-12 — Refreshed README and progress/changelog docs
  - Worker: Agent
  - Summary: Updated the human-facing README and live progress handoff to reflect the current shell bootstrap scripts, Python engine, `nodectl` CLI, FastAPI panel, validation commands, current branch policy, and the known tracked `.pyc` working-tree artifact.
  - Validation: `bash -n l0-server-vm.sh` passed.
  - Git state: branch `agent/docs-refresh-20260712`, documentation changes pending commit.
- 2026-07-11 — Documented the web panel stack in README
  - Worker: Agent
  - Summary: README updated to mention the FastAPI + HTMX NodePanel stack and current repository components.
  - Validation: committed as `815238c`.
  - Git state: branch `main`, pushed.
- 2026-07-11 — Bootstrapped NodePanel web frontend
  - Worker: Agent
  - Summary: Developed a FastAPI + HTMX based NodePanel dashboard under `panel/` with auto-refreshing node and ledger views plus form workflows for create, assign, collect, reset, and destroy actions.
  - Validation: `bash scripts/test.sh` passed.
  - Git state: feature work committed before README refresh.
- 2026-07-11 — Implemented `nodectl` CLI and expanded engine tests
  - Worker: Agent
  - Summary: Built the Typer-based `nodectl` CLI, added mock hypervisor state persistence, and expanded the Python test suite to cover lifecycle engine behaviors.
  - Validation: `bash scripts/test.sh` passed.
  - Git state: feature work committed before README refresh.

## Git Branch and Commit State
- Current branch: `agent/docs-refresh-20260712`
- Base branch at start of this session: `main`
- HEAD commit at start of this session: `815238c` (`docs: document web panel stack in README`)
- Working tree state at start: unrelated tracked `.pyc` modification under `tests/__pycache__/`
- Commit state for current work: documentation refresh pending commit

## Exact Resume Point
Resume from:
1. run `bash scripts/test.sh` if a broader validation pass is needed for non-doc changes
2. review `git status --short --branch` to confirm only intended docs are staged
3. commit the README/PROGRESS refresh
4. validate real libvirt-backed or privileged Ubuntu flows next
