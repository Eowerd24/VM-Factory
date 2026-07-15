# AGENTS.md

Guidance for any coding agent (Codex, Claude Code, etc.) working in this repository.
This is one of three UCC Stage-1 repos: **`nodectl`**, **`Artifact-compiler`**, **`VM-Factory`**.

> **M-c note (2026-07-15):** this file previously had no mention of the UCC Stage-1 conformance
> work at all (fences, ports, envelopes, idempotency) — it was purely a generic operating-procedure
> doc (branch naming, commit hygiene, destructive-action prohibitions). §0–§2 and §4 below are new,
> copied from the shared `/UCC/AGENTS.md` template; §3 is this repo's per-repo block, also from that
> template. Everything from "Repository operating procedure" onward is the *original* content,
> corrected in place rather than deleted — see the inline notes for what changed and why:
> - Every absolute path pointed at `/home/sarge/Desktop/AI-Factory/VM-Factory/...`, which is not
>   where this repo lives (this clone is under `.../UCC/clones/VM-Factory`, and the real path will
>   differ again after the repo is forked). Replaced with repo-root-relative language.
> - "no runnable application wrapper exists yet" was false — `panel/main.py` is a real FastAPI +
>   Jinja app (the "factory panel"), already running and tested.
> - **Naming collision worth flagging explicitly:** this repo's own `nodectl.py` (a Typer CLI for
>   direct node lifecycle management — `create`/`reset`/`destroy` against the hypervisor) is a
>   **different tool** from the separate `nodectl` repo (the FastAPI dashboard this workspace also
>   contains, currently mid-D5-rename from `nodepanel`). The name collision is coincidental and
>   predates the UCC work; nothing here renames `nodectl.py` — that's this repo's own tool name, not
>   in scope for the `nodectl`-the-repo rename (D5).

---

## 0. What this repo is

A **UCC Stage-1 conformant standalone tool.** It runs and is tested on its own, and it
conforms to a shared contract layer so three repos can later integrate. The fork onto the
UCC line has **not** been cut yet. Pinned shared-contract version: **`ucc-contracts v0.2.0`**
(vendored under `third_party/ucc-contracts/`).

Two documents outrank this file and each other in this order — read them before non-trivial work:

1. `docs/roadmap/UCC-Shared-Roadmap-To-Fork.md` — the plan, gates, and the path to fork (§8).
2. `docs/reference/UCC-Standards-and-Layout-Reference.md` — the conventions everything conforms to.

**If this file disagrees with those, they win.** If the vendored `ucc-contracts` disagrees with
any prose, the code wins. Do not re-litigate decisions already locked in the roadmap's decisions
table (D1–D6) or its conflict-resolution table.

**This repo also carries its own, larger, pre-UCC planning corpus** (`ai-worker-factory-plan.md`,
`factory-panel-convergence.md`, `FIRE-AWAY.md`) describing a broader "AI Worker Factory" product
vision — converging this repo and `nodectl` into one system. That vision is **not** the same as,
and is broader in scope than, the UCC narrow-fork work: repo convergence/merging is explicitly
Stage-2-or-later under the locked roadmap (§1.1 below). Treat those three docs as background
context and a separate, longer-term roadmap, not as authorization to do convergence work now — if
a task seems to call for it, stop and check it against the UCC roadmap first, per §4.

---

## 1. Shared core — non-negotiable rules (identical in all three repos)

1. **Fork scope is NARROW.** Do **not**: build the UCC product, merge repos, add a broker /
   network service / canonical database, or wire real cross-module adapters. Those are Stage 2
   (post-fork). Port adapters here may stay honest stubs.
2. **Fail closed over fabricate.** If you lack a real ID, hash, token, publication state, or
   record, refuse with a typed `ucc.problem` — never invent one. This is the same principle
   behind the vault and dry-run fixes; apply it everywhere, especially in port methods.
3. **No trusted-path arbitrary shell. No cross-module canonical writes.** Legacy raw-command and
   direct-infra paths survive only as **fenced, standalone-only diagnostics** and must never be
   reachable from a port. See §3 below for the exact fenced symbols.
4. **Fences are enforced by AST call-site tests, not substrings.** Mentioning a fenced symbol in a
   docstring is fine; adding a real call to it will (correctly) fail the guard. **Never "fix" a
   failing fence test by weakening it to text matching** — that regression already happened once
   (this repo's own `test_string_exec_fence.py` was rewritten from regex to AST for exactly this
   reason, M-a session) and was reverted. If a fence test fails, you added a real forbidden call;
   remove it.
5. **`ucc-contracts` is vendored and pinned.** Never hand-edit schemas, ID rules, lifecycle
   tables, or refusal codes locally. If the contract needs to change, it changes upstream, gets a
   new tag, and is re-vendored — then this repo bumps its pinned version.
6. **Standalone stays usable.** Every change is additive or a fenced relocation. Never remove this
   repo's independent CLI/run path or its existing tests.
7. **Six-field format for every change**, in the PR/patch description:
   current evidence / target contract / smallest conforming change / compatibility impact /
   tests / migration or fallback.
8. **Delivery is via patches.** Clones are read-only (no push creds). Produce `.patch`/diffs and
   files; do not assume you can push. Patches are cumulative and order-sensitive per repo.
9. **Keep the docs in lockstep.** If you change the schema set or a gate's state, update the
   roadmap (§2/§8) and standards reference (§17) in the same change.

### Event / envelope conventions

- Each repo **dual-writes**: the legacy ledger/audit line **and** a schema-conformant `ucc.event`,
  never one instead of the other. The legacy writer stays byte-for-byte as-is.
- `ucc.event.causation_id` is **omitted when absent, never `null`** (unlike `ucc.request`, the event
  schema's `causation_id` is not nullable).
- `producer_sequence` is per-producer, not globally ordered; it is not race-safe under concurrent
  writers (matches the legacy ledgers — do not claim otherwise).
- Real canonical IDs (`art_`, `node_`, …) do not exist yet. Current `subject.id`s are **documented
  placeholders** (deterministic sha256-derived). Do not build logic that assumes they are the final
  canonical IDs; they are replaced in Stage 2.

---

## 2. Making a change here

- Start from the current HEAD; run the full suite **before** touching anything and report the count.
- Make the smallest conforming change. Prefer additive files (new test, new module) over edits to
  load-bearing or vendored code — and verify a "this is vendored, don't touch it" comment is
  actually still true before trusting it.
- Re-run the full suite in an **independent fresh clone** before delivering — not just the working
  copy you edited.
- Write the six-field description. State compatibility impact honestly (operational changes count,
  e.g. "connecting to an un-pinned host now hard-fails").

---

## 3. This repo — VM-Factory

- **Shape:** multi-top-level layout (`library/`, `panel/`, `scripts/`). **No editable self-install**
  (setuptools can't auto-discover the layout; `pyproject.toml` has no `[build-system]` table);
  install deps directly and run `pytest`
  (`fastapi jinja2 pydantic python-multipart pyyaml typer uvicorn httpx pytest jsonschema`).
  Vendored `third_party/ucc-contracts/`. `panel/main.py` is a real, running FastAPI + Jinja app (the
  "factory panel"). `nodectl.py` (repo root) is this repo's own Typer CLI for direct node lifecycle
  management — see the naming-collision note above, it is unrelated to the separate `nodectl` repo.
- **Fail-closed vault:** `library/credentials.py` `VaultAdapter` — unknown refs raise
  `CredentialError`; only explicit `mock:` / `env:` prefixes resolve. **Never** restore a fabricated
  `ghp_test_token_*` fallback or a bare-env fallback.
- **SSH host-key:** `library/transport.py` — `StrictHostKeyChecking=yes` + a real pinned known-hosts
  file (env `VM_FACTORY_KNOWN_HOSTS`, else `<state>/ssh/known_hosts`). **Never** `accept-new` or
  `UserKnownHostsFile=/dev/null`. `MockTransportBackend` is unaffected.
- **Fenced — standalone-only** (guarded by `tests/test_string_exec_fence.py`, AST-based):
  `library/engine.py` `NodeLifecycleEngine.assign()` (interpolated `git clone`) and
  `TransportBackend.run_cmd(cmd: str)`. Never call either from a `FactoryPort` adapter.
- **Ports:** `library/factory_port.py` — 10 `FactoryPort` methods. **Real:** `list_eligible_nodes`,
  `get_node_health` (uses `v0.2.0`'s `RefusalCode.NODE_NOT_FOUND`, not `refusal_code=None`, done in
  M-a), `reset_node`. The other 7 refuse `DEPENDENCY_UNAVAILABLE`.
- **Events:** dual-write via `library/ucc_events.py`. The events-file path is an **explicit
  constructor param** — do not derive it via `.parent.parent` (that leaked files above the test's
  tmp dir once and was fixed). `deterministic_id()` (was `_deterministic_id`, made public in M-b
  since `idempotency_store`/`factory_port` now import it too) derives placeholder subject/actor ids.
- **Idempotency (M-b, D2, done):** `FactoryPort.reset_node` — pass `request["idempotency_key"]` to
  opt in. Builds+validates `ucc.request`/`ucc.result`; replay returns the stored `PortResult.value`
  verbatim (no re-reset); same key + different node refuses with `RefusalCode.IDEMPOTENCY_CONFLICT`.
  Store: `<state_dir>/idempotency.db` (`library/idempotency_store.py`). It commits `unknown` before
  dispatch; success replaces it, definite failure removes it, and ambiguity retains it so retry
  refuses `OUTCOME_UNKNOWN` until reconciliation. No auto-expiry. Omitting the field preserves the
  pre-M-b behavior.
- **Tombstone-on-destroy (M-c, done):** `engine.py::destroy()` now saves the manifest back
  (state=`retired`) instead of `unlink()`-ing it — locked invariant, destruction preserves tombstones.
  **Behavior change:** destroyed nodes stay visible in `nodectl list --mock` / the panel's node listing
  (showing `retired`) instead of vanishing; `destroy()` now returns `NodeManifest`, not `None`.
- **Tests:** `pytest`.
- **M-c hygiene done:** the 5 previously-committed `library/__pycache__/*.pyc` /
  `tests/__pycache__/*.pyc` files are untracked (`git rm --cached`, content stays on disk;
  `.gitignore` already excluded `__pycache__/` — they'd been force-added before that rule existed).
- **Pending:** none for this repo's UCC M-c scope. `factory-panel-convergence.md`'s hygiene item
  ("`nodepanel.db` + `uploads/` out of git") is a `nodectl`-repo concern, not this repo's — and is
  substantially done there already (M-c, this session): `uploads/` untracked, dev-root isolated
  under `.ucc-dev/`. See that repo's `AGENTS.md`/`COMPONENT-MAP.md`.

---

## 4. Out of scope (do not do here)

Real cross-module adapters; canonical record stores; the ~26 domain schemas; projection builder;
UCC application services; broker / network API / server DB; repo merges; multi-operator auth; any
general remote terminal in a trusted path; frontend or deployment-topology decisions. All of these
are Stage 2 or a later roadmap. If a task seems to require one, stop and flag it against the
roadmap. This includes the `ai-worker-factory-plan.md` / `factory-panel-convergence.md` convergence
vision — it is real, longer-term intent for this repo, but repo convergence specifically is exactly
the kind of thing this section rules out for the UCC narrow fork.

---

## Repository operating procedure (pre-UCC, retained — generic hygiene, not UCC-specific)

The sections below predate the UCC work and describe general agent-operating discipline for this
repo (branch naming, commit hygiene, destructive-action policy). None of it contradicts §0–§4
above; it's a stricter, repo-specific layer on top. Corrected in place where stale (see the M-c
note at the top of this file for what changed).

### Repository boundaries

Work only inside this repository and repository-local artifacts. Do not modify: the physical host,
the hypervisor, other VMs, unrelated repositories, host networking/firewall/SSH/storage/DNS, or
production systems / live infrastructure.

### Mandatory preflight checks

Run these from the repository root at the start of each substantial session:

```bash
pwd
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git status --short --branch
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git remote -v
env HOME=$PWD GIT_CONFIG_NOSYSTEM=1 git log --oneline --decorate -n 20
find . -maxdepth 3 -type f | sort
bash -n l0-server-vm.sh
```

Preflight requirements: confirm you're at the repository root (not any specific absolute path —
that will differ by clone/environment); preserve unknown working-tree changes; verify referenced
files actually exist before assuming a script or doc is complete; treat missing files as repo-state
facts, not user mistakes.

### Setup and test commands

```bash
# Python setup (uv-managed) — or install the pinned deps directly per §3 above if uv isn't available
uv sync
# Node.js setup (for tooling, not the Python app)
npm install
# Full validation suite (shell + python)
bash scripts/test.sh
```

`l0-server-vm.sh` is a Bash script intended to run on Ubuntu with `sudo`, depends on
`lib-l0-core.sh`. Dry-run smoke test:

```bash
L0_ALLOW_NON_ROOT=1 bash ./l0-server-vm.sh --dry-run
```

Privileged runtime behavior on a real Ubuntu target remains only partially verified.

### Dependency management

Python deps via `uv` (`pyproject.toml`/`uv.lock`); Node deps via `npm` (`package.json`/
`package-lock.json`, tooling only). Keep dependencies minimal and pinned; use `uv add <package>` /
commit the npm lockfile; don't install global packages when a repo-local alternative exists; don't
add heavyweight infrastructure tooling speculatively.

### Git workflow

Inspect the working tree first → create or continue a dedicated branch → smallest coherent change →
validate the relevant commands → update `README.md`/`PROGRESS.md` when state changes → focused
commits → push only if authentication already works → never merge automatically.

Branch naming: `agent/<short-task>-YYYYMMDD` (or `agent/project-bootstrap-YYYYMMDD` for bootstrap
work). Commits: focused, reviewable, reflect real verified work, no secrets/generated junk/
host-specific artifacts.

### Secret handling

Never commit or expose: tokens, PATs, SSH private keys, `.env` files with real values, cookies,
host credentials, VM credentials. Check staged changes before every commit.

### Prohibited destructive actions

Never run unless the human explicitly instructs it: `git reset --hard`, `git clean -fd`/`-fdx`,
`git push --force`/`--force-with-lease`, destructive migrations, credential rotation, host/
hypervisor modification. Also prohibited: deleting unknown files because they seem unused;
overwriting legacy docs without reading them first; claiming a script works when only syntax was
checked.

### When to stop for human input

Use the `WAITING_FOR_HUMAN` format in `FIRE-AWAY.md` when blocked by: a missing secret or account
authorization; an unavoidable host/hypervisor change; a destructive/irreversible migration; an
architecture/product decision with major consequences and no governing doc; a persistent blocker
after multiple grounded attempts; or a conflict between authority documents that specificity/
recency can't resolve. Do not stop for routine implementation work, missing tests, or ordinary
cleanup.

### Autonomous authority

Agents may proceed autonomously with normal repository-local development: reading/editing files,
running tests, fixing failures, adding tests, updating docs, branching, focused commits, installing
repo-local dependencies. Must stop before: production deployment, destructive migrations,
credential rotation, force-pushing, rewriting shared history, modifying the host/hypervisor,
exposing services outside the VM, or making unresolved large-consequence product/architecture
decisions.
