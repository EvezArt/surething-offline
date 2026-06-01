# Persistence and Auth Rollout

Status: staged upgrade plan for moving the operator spine from ephemeral process state to durable, optionally authenticated operation.

This document is paired with:
- `docs/OPERATOR_API_CONTRACT.md`
- `api/durable_spine.py`
- `api/auth_guard.py`

It is written to preserve the current client contract while upgrading the backend guarantees underneath it.

---

## Current state

The live operator spine currently has these constraints:

- event storage is in-memory only
- events disappear on restart/redeploy
- write endpoints are unauthenticated
- contradiction and deploy-status rows are diagnostic/static
- console clients must currently label some state as `ephemeral` or `diagnostic`

That is honest, but it is not yet operationally strong enough for durable operator history.

---

## Upgrade goals

### Goal 1 — durable event history
Preserve spine events across process restarts using local durable storage.

### Goal 2 — protected writes
Require operator authentication for write-capable routes when a token is configured.

### Goal 3 — preserve client contract
Keep route names and core response shapes stable so the mobile console and other clients do not need a full rewrite.

### Goal 4 — honest migration
Do not silently pretend old ephemeral history is durable. Durable history begins when durable storage is enabled.

---

## New implementation components

### `api/durable_spine.py`
Provides a SQLite-backed spine store.

Key behavior:
- stores events in `data/operator_spine.db` by default
- enforces sequential heights
- verifies parent-hash continuity at append time
- lists events with pagination
- verifies stored chain integrity

### `api/auth_guard.py`
Provides optional bearer-token protection.

Key behavior:
- controlled by `OPERATOR_API_TOKEN`
- when unset: current open behavior is preserved
- when set: protected routes require `Authorization: Bearer <token>`

---

## Environment variables

### `SPINE_DB_PATH`
Optional path override for durable spine DB.

Default:
```bash
SPINE_DB_PATH=data/operator_spine.db
```

### `OPERATOR_API_TOKEN`
Optional bearer token for write protection.

When unset:
- API remains open as it is today

When set:
- protected routes should require matching bearer token

Example:
```bash
OPERATOR_API_TOKEN=replace-with-long-random-secret
```

---

## Recommended route protection policy

### Protect immediately when auth is enabled
These routes should require the bearer token:
- `POST /spine/event`
- `POST /canonicalize` (optional; depends on whether you want public utility behavior)
- `POST /fire/anchor` (recommended if operationally sensitive)

### May remain open
These routes may remain open initially:
- `GET /`
- `GET /tools`
- `GET /spine/verify`
- `GET /spine/events` (optional; depends on how private event history should be)
- `GET /contradictions`
- `GET /deploy/status`

### Conservative privacy policy
If event history is sensitive, also protect:
- `GET /spine/events`
- `GET /spine/verify`

---

## Migration phases

## Phase A — code landed, not yet wired
Status now.

What exists:
- durable storage module
- optional auth guard module
- contract docs

What does not yet exist:
- `api/index.py` integration
- deployment env wiring
- data migration from any previous persistent source

Client meaning:
- current API contract still stands
- mobile console should continue to label history as `ephemeral` until durable integration is active

---

## Phase B — durable spine integration

### Change
Refactor `api/index.py` so spine routes use `DurableSpineStore` instead of `_spine` list state.

### Intended behavior
- `GET /` returns durable height
- `POST /spine/event` appends to SQLite
- `GET /spine/events` reads SQLite-backed history
- `GET /spine/verify` verifies SQLite-backed chain

### Client impact
At this point, the console may switch from `ephemeral` to `durable` for spine history **only after deployment confirmation**.

### Required honesty rule
Do not retroactively imply that pre-upgrade session history was durable.

---

## Phase C — auth activation

### Change
Add `require_operator_token` to protected routes.

### Intended behavior
- when `OPERATOR_API_TOKEN` unset: existing open behavior preserved
- when `OPERATOR_API_TOKEN` set: protected writes require bearer token

### Client impact
- Settings screen in the mobile console should support operator token input
- token should be stored locally only unless a safer secret mechanism exists
- failed auth should surface as `401` or `403`, not as generic disconnect

---

## Phase D — deploy with persistence semantics

### Deployment notes
If deploying on a platform with ephemeral filesystem behavior, SQLite durability may only be partial unless the filesystem itself is persistent.

That means there are two different meanings of “durable”:

1. **process-durable** — survives app restarts inside the same persistent volume
2. **platform-durable** — survives redeploys/replacements because storage volume persists

### Operational rule
Only label the spine as truly durable if the deployment target provides persistent storage for `SPINE_DB_PATH`.

If storage is ephemeral at the platform layer, the console should use a more precise label such as:
- `process durable`
- `filesystem uncertain`
- `redeploy volatile`

Do not overclaim.

---

## Suggested `api/index.py` integration sketch

High-level replacement plan:

1. instantiate store once:
```python
from api.durable_spine import DurableSpineStore
store = DurableSpineStore()
```

2. protect write routes when desired:
```python
from fastapi import Depends
from api.auth_guard import require_operator_token
```

3. use `Depends(require_operator_token)` on protected routes

4. replace `_spine.append(...)` with `store.append_event(...)`

5. replace in-memory list reads with `store.list_events(...)`, `store.verify(...)`, `store.total_events()`

---

## Backward-compatibility rules

To avoid breaking existing clients, keep these stable:
- route paths
- major response keys
- hash semantics
- lane and event-type validation semantics

If you add new response fields, do so additively.

Good additive fields include:
- `storage_mode`: `ephemeral` | `durable`
- `auth_mode`: `open` | `bearer`
- `durability_scope`: `process` | `persistent-volume` | `unknown`

These fields would help the console label truth more precisely.

---

## Recommended new metadata fields

### On `GET /`
Potential additive fields:
```json
{
  "storage_mode": "durable",
  "auth_mode": "bearer",
  "durability_scope": "persistent-volume"
}
```

### On `GET /spine/events`
Potential additive fields:
```json
{
  "events": [],
  "total": 42,
  "storage_mode": "durable"
}
```

These are optional enhancements, not current contract requirements.

---

## Validation checklist before declaring the upgrade complete

### Durability
- [ ] create event
- [ ] restart process
- [ ] confirm event still present
- [ ] redeploy
- [ ] confirm event still present if platform storage is persistent

### Auth
- [ ] protected route rejects missing token with `401`
- [ ] protected route rejects bad token with `403`
- [ ] protected route accepts valid token
- [ ] unprotected routes still function as intended

### Contract stability
- [ ] route paths unchanged
- [ ] major response keys preserved
- [ ] existing console parser still works or degrades cleanly

---

## What the mobile console can claim after rollout

### Before durable integration
- `session-bound`
- `ephemeral`
- `diagnostic`

### After durable integration, before persistent-volume confirmation
- `durable (local store)`
- `platform durability unverified`

### After durable integration with persistent-volume confirmation
- `durable`
- `authenticated writes` if bearer token enabled

That is the honest ladder.

---

## Recommended next engineering step

Patch `api/index.py` to adopt `DurableSpineStore` and `require_operator_token`, then deploy on a target with known persistent storage semantics.

Until that patch lands, the new modules and docs should be treated as the implementation package for the next upgrade wave.
