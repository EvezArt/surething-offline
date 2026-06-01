# External Persistence Rollout

Purpose: move the operator spine from local durability experiments to an honestly persistent backend without breaking the current API contract.

This rollout assumes the current state:
- `api/index_durable.py` exists
- `api/durable_spine.py` exists
- the route surface is already shaped for ledger-style persistence
- local SQLite may be useful, but Vercel-local filesystem durability is not assumed to be redeploy-safe

---

## Objective

Upgrade the operator spine to use a true persistent backend while preserving:
- current route names
- current event object shape
- current hashing semantics
- current client integrations

The storage backend changes.
The operator contract stays stable.

---

## Recommended rollout sequence

## Phase 1 — abstract the store boundary

Status: started.

Artifacts already present:
- `api/spine_store_protocol.py`
- `api/durable_spine.py`

Goal:
- ensure route layer depends on the store protocol, not directly on a single backend implementation

### Completion condition
`api/index_durable.py` uses a store selected behind a backend boundary rather than being hardwired forever to SQLite.

---

## Phase 2 — choose persistent backend class

Pick one path:

### Path A — verified persistent volume + SQLite
Fastest honest upgrade.

Use when:
- you want minimal code changes
- you can run on infrastructure with actual persistent volume semantics

### Path B — external relational ledger backend
Best long-term architecture.

Use when:
- you want strong audit/query semantics
- you want the operator ledger to outgrow local-file assumptions

### Path C — hybrid
- relational backend for durable ledger
- KV for hot state/counters
- blob/archive for snapshots

Best for larger operational maturity.

---

## Phase 3 — backend implementation

### If Path A
- keep `DurableSpineStore`
- deploy on runtime with verified persistent storage
- verify restart/redeploy retention

### If Path B
Implement a new store that satisfies `SpineStoreProtocol`, for example:
- `PostgresSpineStore`

It must preserve:
- append-only event semantics
- stable `height`
- unique `event_hash`
- parent-hash continuity checks
- ordered replay

### If Path C
Keep one canonical source of truth.
Do not let cache/archive layers become competing ledgers.

---

## Phase 4 — route-layer wiring

The route layer should expose the same contract regardless of backend.

Safe implementation pattern:
- pick backend via environment/config
- instantiate one store behind `SpineStoreProtocol`
- route handlers call only protocol methods

This keeps the mobile console and other clients stable while the backend matures.

---

## Suggested config model

Examples:

```bash
SPINE_BACKEND=sqlite
SPINE_DB_PATH=data/operator_spine.db
```

```bash
SPINE_BACKEND=postgres
SPINE_DATABASE_URL=...
```

```bash
SPINE_BACKEND=hybrid
SPINE_DATABASE_URL=...
SPINE_CACHE_URL=...
SPINE_ARCHIVE_BUCKET=...
```

---

## Truth labels during rollout

### Before external backend is live
- `durable local store`
- `platform durability unverified`

### After verified persistent volume or external DB is live
- `persistent backend`

### After auth is enabled
- `authenticated writes`

### For archive/snapshot layers
- `archived`

These labels should flow through the console UI.

---

## Validation requirements

### Ledger integrity
- create event
- verify chain
- restart service
- verify event remains
- redeploy/replace runtime
- verify event remains if persistence claims require that

### Auth
- missing token fails when enabled
- bad token fails when enabled
- valid token succeeds

### Contract stability
- route paths unchanged
- response keys preserved or expanded additively
- clients continue to function

---

## Recommended next implementation step

Introduce store selection in the durable entrypoint so the operator spine can choose between SQLite and future persistent backends without another route rewrite.

That is the clean bridge from current durable scaffolding to true persistent backend operation.
