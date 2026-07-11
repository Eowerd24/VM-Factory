# FIRE-AWAY.md

## Autonomous Execution Contract
This repository is authorized for routine autonomous development inside the dedicated VM. Future agents should proceed without repeated approval requests for normal repository-local work.

## Operating Rules
Proceed autonomously for:

- inspection
- implementation
- debugging
- testing
- documentation
- focused commits
- branch creation
- repository-local dependency installation

Do not pause for routine confirmation when the work stays inside this repository and VM.

## Required Behavior
Always:

- inspect before modifying
- preserve unknown user work
- use conservative assumptions
- prefer implementation over planning-only responses
- test and debug independently
- continue into the next clearly authorized task after finishing the current one
- leave the repository in a readable, resumable state

## Hard Boundaries
Never modify:

- the physical host
- the hypervisor
- unrelated repositories
- other VMs
- production systems
- host networking, firewall, DNS, or SSH configuration

Never expose services outside the VM.

## Repository-Specific Reality
Current repo state:

- planning-first repository
- one shell script wrapper: `l0-server-vm.sh`
- shared core helper library: `lib-l0-core.sh`
- dry-run smoke test suite: `tests/test-l0-dry-run.sh`, `tests/test-l0-core-args.sh`, and `scripts/test.sh`
- no CI configuration
- no package dependency manifest
- no runnable application product yet (planning/prototype phase)

That means autonomous work should focus on repository bootstrap, missing implementation pieces, tests, and documentation grounded in the existing plan docs.

## Default Execution Loop
1. Read `AGENTS.md`, `PROGRESS.md`, `README.md`, and the planning docs.
2. Inspect git status and current repo contents.
3. Validate what already exists.
4. Implement the highest-priority unblocked work item.
5. Add tests or validation where practical.
6. Update `PROGRESS.md`.
7. Run final checks.
8. Commit coherent work.
9. Continue into the next authorized item unless a real blocker stops progress.

## Stop Only For Genuine Human-Only Blockers
Stop only when progress cannot realistically continue without:

- credentials or account access
- a major unresolved product or architecture decision
- host or hypervisor modification
- a destructive irreversible action
- missing external material that defines required behavior

Difficulty alone is not a blocker.

## WAITING_FOR_HUMAN
Use exactly this format when blocked:

```text
WAITING_FOR_HUMAN
Blocker: <exact blocker>
Why work cannot realistically continue: <evidence-based explanation>
Attempts already made: <commands or approaches tried, with outcomes>
Work completed: <what is already done safely>
Exact human action required: <one specific action or answer>
Exact resume step: <next concrete command or implementation step>
Validation: <checks run and their status>
```

## Current Priority Guidance
Unless a human gives a narrower task, prefer this sequence:

1. make the repository executable from its current plans
2. restore or implement missing script dependencies
3. add minimal validation
4. add missing manifests/config only when justified by real code being introduced
5. keep docs current as the codebase takes shape
