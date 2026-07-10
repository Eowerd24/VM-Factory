# Factory ⇄ NodePanel — Convergence Roadmap
*Comparing the AI Worker Factory plan against the real nodepanel repo, and the path to one system. The factory is the product; the panel is one wrapper on it.*

---

## 1. Comparison: what exists vs what the factory adds

| Capability | Panel (repo, today) | Factory plan | Verdict |
|---|---|---|---|
| Audit trail | ✅ Ledger: immutable JSONL, actor IDs, structured params | Planned as `events.md` + reports | **Panel wins — adopt its ledger as THE audit spec**, factory events become ledger entries |
| Credential handling | ✅ SQLite-backed manager; strap/scrub/nuke; token injection via SSH stdin (never on disk in transit) | Planned as `vault.py` at Step H | **Panel is 70% of L3 credential injection already.** Missing: vault backend for the tokens themselves, per-node scoping, rotation-on-reset |
| Result collection | ✅ Collect/Handback: `~/outbox/` atomic inbox, JIT checksum manifest, `./inbox` on host | Planned as `collect-report` | **Panel wins on transport.** Factory adds *what* to collect (report.json, PROGRESS, NEEDS, diffs) |
| Payload execution | ✅ 3-tier picker (Approved/Draft/Unavailable), sha256 manifest gating | Planned as "gate by node type" | **Merge:** keep checksum gating, add node-type gating, kill the bypass |
| Guest provisioning | ❌ Triggers `create-worker` over SSH (script assumed to exist) | ✅ L0–L2 scripts written, L3 spec'd | **Factory wins — this is the missing half** |
| Node identity/state | Two-way: node.yaml vs virsh | Three-way + formal state machine | Factory adds `/etc/node-release` + state transitions |
| Snapshot lifecycle | ❌ | ✅ sx-fresh/sx-ready, reset-with-rotation | Factory only |
| SSH identity | ❌ mounts `~/.ssh` read-only | ✅ dedicated factory keypair + pinned known_hosts | Factory wins — highest-priority swap |
| Dev without hypervisor | ✅ MOCK_SSH=True dummy mode | ❌ not considered | **Panel wins — MOCK_SSH becomes the autonomous-dev harness** |
| Repo hygiene | ❌ nodepanel.db + uploads/ committed; patch/refactor litter at root | State-dir separation designed | Factory rules apply to the panel repo itself |

**Conclusion:** the panel independently grew the *work-plane* organs (ledger, credentials, collection, gating) while the factory grew the *machine-plane* organs (images, layers, snapshots, state machine). They interlock rather than overlap. The convergence job is: extract the panel's organs into a shared library, put the factory engine under them, and make the panel UI a thin wrapper — exactly your "factory pointed at a single wrapper on the panel."

---

## 2. The Shared Stack

```
┌─────────────────────────────────────────────────────────────┐
│  WRAPPERS (thin, replaceable, zero business logic)          │
│  ├─ panel/     FastAPI + HTMX UI  (+ /app Vue experiment)   │
│  └─ nodectl    typer CLI                                    │
├─────────────────────────────────────────────────────────────┤
│  ENGINE LIBRARY  (library/ → the one implementation)        │
│  ├─ manifest.py     node.yaml + state machine (sole writer) │
│  ├─ hypervisor.py   virsh via local subprocess OR SSH       │
│  ├─ transport.py    fabric SSH, payload push, inbox/outbox  │
│  │                  checksum collect  ← extract from panel  │
│  ├─ credentials.py  strap/scrub/nuke + vault adapter        │
│  │                  ← extract from panel; SQLite = METADATA │
│  ├─ payloads.py     manifest.json sha256 + tier + node-type │
│  │                  gating           ← extract from panel   │
│  ├─ ledger.py       append-only JSONL writer + query        │
│  │                  ← extract from panel                    │
│  ├─ engine.py       verbs: create/assign/reset/snapshot/    │
│  │                  destroy/collect (compose the above)     │
│  └─ reports.py      report.json, NEEDS.md, PROGRESS parse   │
├─────────────────────────────────────────────────────────────┤
│  CONTRACTS   contracts/*.{yaml,json,md} — human-owned       │
├─────────────────────────────────────────────────────────────┤
│  GUEST       guest/ bash L0–L3 — zero deps, runs in VMs     │
├─────────────────────────────────────────────────────────────┤
│  STATE       ~/.local/state/nodefactory/ — NEVER in git     │
│              images/ disks/ nodes/ reports/ inbox/          │
│              ssh/(factory key + known_hosts) credentials.db │
│              ledger/*.jsonl                                 │
└─────────────────────────────────────────────────────────────┘
```

Stack rules:

1. **Wrappers contain routes, templates, and argument parsing. Nothing else.** If a panel handler has logic worth testing, that logic belongs in the library.
2. **The engine is the only writer** to hypervisor, manifests, credentials, and ledger. The panel's existing direct implementations migrate down; the routes keep their URLs and call library functions.
3. **`FACTORY_DIR=~/nodefactory` splits**: repo (code) vs `~/.local/state/nodefactory` (state). The panel's pydantic-settings gains `NODEFACTORY_STATE`; `nodepanel.db`, `uploads/`, `inbox/` move there.
4. **MOCK_SSH graduates** from dummy-render flag to a first-class *mock backend* implementing the same hypervisor/transport interfaces with fixture nodes — the harness all autonomous development runs against.

---

## 3. The Schemas

All live in `contracts/`, versioned (`schema_version` field in every record). Humans own this directory (see §4). Each schema names its **sole writer**.

### 3.1 `node.yaml` — node manifest (writer: manifest.py)
```yaml
schema_version: 1
name: w-cliplib-01
type: ai-worker            # enum: ai-worker|dev-desktop|dev-server|homelab-service|
                           #       monitoring-node|research-sandbox|temporary-build-node|github-maintainer
image: gold-server-2404-v1
state: ready               # provisioned→bootstrapped→validated→ready→assigned→reporting→retired
snapshots: [sx-fresh, sx-ready-20260712]
repo: github.com/you/cliplib          # assignment fields present only when state ≥ assigned
credential_ref: cred:cliplib-w01      # reference into credentials.db — never a value
created: ...   expires: ...   resources: {vcpu, ram_gb, disk_gb}
network: nat-workers
```
State transitions are legal only via `manifest.transition()`, which enforces preconditions (e.g., `ready` requires an `sx-ready` snapshot to exist AND last preflight green).

### 3.2 `/etc/node-release` — in-guest truth (writer: guest L-scripts, append-only)
Already emitted by your L0–L2 scripts. Freeze the field list: `IMAGE_VERSION, ADMIN_USER, TARGET, L0_WRAPPER, NODE_HOSTNAME, L1_DATE, NODE_TYPE, L2_SCRIPT, AGENT_UID, AGENT_SUDO=denied, …`. The panel parses by this spec for the three-way reconciliation.

### 3.3 Ledger record — audit trail (writer: ledger.py, append-only JSONL)
Adopt the panel's existing shape and extend:
```json
{"schema_version":1,"ts":"2026-07-10T15:04:11Z","actor":"sarge|panel|nodectl|agent:w-x-01",
 "action":"payload.fire|collect.pull|cred.strap|cred.scrub|cred.nuke|node.create|node.reset|...",
 "node":"w-cliplib-01","params":{...},"result":"ok|error","sha256":{...}}
```
Rules: no record ever contains a secret value; engine progress *events* use the same envelope with `action:"event"` but stream separately (telemetry ≠ audit — ledger is only completed facts).

### 3.4 Credential record — metadata only (writer: credentials.py)
```json
{"id":"cred:cliplib-w01","kind":"github-pat-fine-grained","repo":"you/cliplib",
 "node":"w-cliplib-01","last4":"a9F2","expires":"2026-07-26","scopes":["contents:rw","pull_requests:rw"],
 "status":"strapped|scrubbed|nuked","strapped_at":...,"vault_ref":"pass:github/cliplib-w01"}
```
**By construction there is no token field.** Values live in the vault (backend still to choose: pass/age/Bitwarden CLI); injection stays the panel's stdin-stream mechanism; `reset` implies scrub+re-strap with a *new* token.

### 3.5 Payload manifest (writer: human via review flow)
```json
{"schema_version":1,"name":"l2-ai-worker.sh","sha256":"...","tier":"approved|draft",
 "allowed_node_types":["ai-worker"],"allowed_states":["bootstrapped","validated"],
 "approved_by":"sarge","approved_at":"..."}
```
Extends the panel's existing sha256 gate with node-type and state gating. **The bypass flag is deleted**, replaced by: draft-tier payloads may run only against mock or `research-sandbox` nodes.

### 3.6 Handback manifest — outbox collection (writer: guest JIT tool, verified by transport.py)
Panel's existing checksum manifest, frozen as a schema: file list + sha256 + node + ts. Collection commits to `state/inbox/<node>/<ts>/` only if every checksum verifies; verification result → ledger.

### 3.7 `report.json` — pre/postflight (writer: guest scripts)
`{node, ts, kind: pre|post, checks:[{id,name,status,detail}], commit_range, pr_url, needs:[...]}` — rendered by the panel as pass/fail tables; `needs` aggregates into the NEEDS badge.

### 3.8 `projects/<name>.yaml` — assignment config (writer: human)
`repo, image, node_type, resources, branch_prefix, credential template (scopes+ttl), env_refs`. Vault references only.

---

## 4. The Hard Boundaries (guardrails for autonomous development)

The panel repo already carries AGENTS.md / MISSION.md / RULES.md — it is itself AI-developed. These boundaries assume agents will write most future code, and are ordered by enforcement strength: **structural (can't) > procedural (checked) > instructional (told)**.

### B1 — Two planes, never bridged
An agent *developing* nodefactory must never touch the infrastructure nodefactory *controls*.
- Dev agents run in ai-worker VMs with `MOCK_SSH=True`, fixture state, **no factory key, no state dir, no real credentials.db, no real ledger**. Structural: those files simply don't exist on a dev worker.
- Only sarge runs the panel/engine against the real hypervisor. Deploy = human pulls a merged main onto the panel host. Agents never deploy.

### B2 — Secrets have one home
- Repo: never (CI secret-scan + gitleaks pre-merge check — required status check).
- SQLite: metadata only, schema §3.4 has no value column to fill.
- Transit: stdin stream (existing mechanism), never argv, never temp files.
- State dir holds `credentials.db` and vault material; it is outside the repo, mode 700, and **immediate action:** `nodepanel.db` + `uploads/` leave git, history audited, anything that ever touched them rotated.

### B3 — Writes go through the engine
Raw `virsh`, raw `ssh`, raw sqlite3 against state files — forbidden in wrapper code. Enforced procedurally: a CI grep/lint rule (`no direct virsh/paramiko outside library/`) as a required check, plus RULES.md. The engine verbs are the API; if a verb is missing, the mission is to add the verb, not to bypass.

### B4 — Protected modules (the panel's own forbidden paths)
`contracts/`, `library/ledger.py`, `library/credentials.py`, `library/payloads.py` (the gate), `guest/lib-l0-core.sh`, `.github/workflows/`, `RULES.md`. Agents may propose changes via DECISIONS.md entries; a human commit flips them. Enforced: CODEOWNERS + branch protection + fine-grained PAT without workflow scope (server-side, injection-proof).

### B5 — The gate has no bypass
Delete the dynamic bypass. Testing uses draft tier against mock/sandbox (B1 + §3.5). A checksum gate that can be switched off in prod is decorative — and "disable the gate" is exactly what a prompt-injected agent would attempt.

### B6 — Ledger is append-only and complete
Every mutating verb writes a ledger record or fails. No verb may complete without its record (write-ahead: intent record → action → result record). Agents cannot edit `ledger.py` (B4) and dev agents have no real ledger to pollute (B1).

### B7 — Repo hygiene rules for agents (add to RULES.md)
- No one-shot transformation scripts committed (`patch_*.py`, `refactor_*.py` class). Transform, verify, delete before PR; the diff is the record.
- No runtime artifacts in git (db, uploads, inbox, compiled assets beyond build.sh outputs policy).
- Every schema-affecting change bumps `schema_version` and includes a migration note in DECISIONS.md.

### B8 — Reset is the response to doubt
Any tripwire hit, secret-scan hit, or out-of-workspace write on a dev worker → collect-report, revoke that worker's PAT, revert to sx-ready. Fix-forward is for code, never for environment trust.

---

## 5. Roadmap (revised for what actually exists)

| Step | Deliverable | Notes / acceptance |
|---|---|---|
| **A. Hygiene (do first, ½ day)** | nodepanel.db + uploads/ out of git & gitignored; history audited; litter files removed; B7 added to RULES.md; state dir created | Public repo is clean; `git log -p -- nodepanel.db` reviewed |
| **B. Contracts** | §3 schemas written into `contracts/`, codifying what the panel already does (ledger, credential, payload, handback) + new (node.yaml, node-release, report) | Every existing panel behavior conforms or has a tracked gap |
| **C. Library consolidation** | Panel's ledger/credential/collect/payload logic moves into `library/` modules with the panel importing them; MOCK_SSH becomes a mock backend behind the same interfaces | Panel behavior unchanged; library importable standalone; pytest green under mock |
| **D. Factory identity** | Dedicated keypair + pinned known_hosts in state dir; compose mounts only that; `~/.ssh` mount deleted | Panel operates with zero access to personal keys |
| **E. Engine verbs** | `engine.py` create/snapshot/reset/destroy/collect composing guest L-scripts over transport; nodectl CLI | Full toy-node lifecycle from CLI; every verb ledgered |
| **F. Three-way reconciliation** | node-release parsing + drift table in panel (manifest vs virsh vs guest) | A deliberately-induced drift is visible |
| **G. Autonomous-dev harness** | Fixture node set for mock backend; CI: pytest + secret scan + B3 lint as required checks; dev-worker project.yaml for nodefactory itself | An ai-worker can develop the panel end-to-end against mock and open a green PR |
| **H. L3 assignment** | `guest/l3/assign-repo.sh` + `engine.assign()` wiring the existing credential strap flow + vault adapter (**vault decision blocks here and nowhere earlier**) | First real worker assigned, mission run, PR opened, collected, reset |
| **I. Dogfood** | The first real mission for the factory: an ai-worker developing nodefactory, under B1–B8 | The system builds itself with you as merge gate |

---

## 6. One-line summary
The panel already built the factory's work-plane organs; the factory built the machine-plane ones. Extract the organs into `library/`, put the engine under them, keep the panel as one thin wrapper — and enforce the boundaries structurally, because the next developer of this codebase is an AI worker inside it.
