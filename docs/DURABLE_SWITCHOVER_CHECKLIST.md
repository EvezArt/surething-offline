# Durable Operator Spine Switchover Checklist

Purpose: execute the switch from the current in-memory operator spine entrypoint to the durable/auth-capable entrypoint with minimal ambiguity and no false claims.

Current candidate entrypoint:
- `api/index_durable.py`

Current matching deploy config:
- `vercel.durable.json`

---

## Before switchover

### 1. Context bootstrap
Load:
- `agentvault/ops/ACTIVE_CONTEXT_SNAPSHOT.md`
- `agentvault/ops/PREMOVE_CONTEXT_PROTOCOL.md`
- `surething-offline/docs/OPERATOR_API_CONTRACT.md`
- `surething-offline/docs/PERSISTENCE_AUTH_ROLLOUT.md`

### 2. Confirm intended truth level
After switchover, the service may claim:
- durable local store
- optional authenticated writes

It may **not** claim platform-persistent durability unless the deployment target actually preserves filesystem state across redeploy/replacement.

### 3. Review environment expectations
Required/optional:
- `SPINE_DB_PATH`
- `OPERATOR_API_TOKEN` (optional, but recommended)

---

## Switchover methods

## Method A — replace existing `vercel.json`

Use when you are ready to make the durable entrypoint the active deployment target.

Change:
- replace current `vercel.json` contents with `vercel.durable.json`

Result:
- Vercel routes to `api/index_durable.py`

## Method B — replace current `api/index.py`

Use when you want the durable implementation under the canonical entrypoint path.

Change:
- replace `api/index.py` with the contents/behavior of `api/index_durable.py`
- optionally keep a backup copy of the old in-memory implementation

Result:
- existing `vercel.json` can keep pointing at `api/index.py`

### Recommendation
Method B is cleaner long-term.
Method A is lower-friction when working around weak in-place editing paths.

---

## Environment setup

### Minimum durable setup
```bash
SPINE_DB_PATH=data/operator_spine.db
```

### Recommended auth setup
```bash
OPERATOR_API_TOKEN=<long-random-secret>
```

### Stronger persistence setup
If platform storage supports a persistent mount, use a path like:
```bash
SPINE_DB_PATH=/data/operator_spine.db
```

Only then is `durability_scope=persistent-volume` a reasonable claim.

---

## Post-switch validation

### 1. Root route
Check `GET /`

Expected additive fields:
- `storage_mode`
- `auth_mode`
- `durability_scope`

### 2. Write path
Call `POST /spine/event`

Expect:
- `ok: true`
- `event_hash`
- `evidence_hash`
- `height`
- `storage_mode: durable`

If auth is enabled:
- missing bearer token should return `401`
- invalid bearer token should return `403`

### 3. Read path
Call `GET /spine/events`

Expect:
- events returned from SQLite-backed store
- `total`
- `storage_mode: durable`

### 4. Verify path
Call `GET /spine/verify`

Expect:
- valid chain response from stored events

### 5. Restart test
Restart the app / redeploy if storage should persist.
Then verify the event still exists.

If it survives restart only within the same container lifecycle but not redeploy, label accordingly.

---

## Honest label mapping for clients

### If SQLite works but filesystem persistence is unverified
Use labels like:
- `durable local store`
- `platform durability unverified`

### If storage survives verified redeploy on persistent volume
Use labels like:
- `durable`
- `persistent-volume`

### If auth token is set
Use labels like:
- `authenticated writes`
- `bearer protected`

### Never use
- `permanent`
- `immutable forever`
- `fully live health` for static diagnostic routes

---

## Console integration changes after switchover

The mobile operator console may update its copy/labels as follows:

### Home
- `spine_height` no longer session-bound
- show `storage_mode`, `auth_mode`, `durability_scope`

### Ledger
- may move from `ephemeral` to `durable local store` after backend confirmation

### Settings
- expose operator token input if bearer auth enabled

### Status messaging
- keep `/contradictions` and `/deploy/status` labeled as diagnostic or mixed until those payloads are upgraded from static-coded values

---

## Required context trace after switchover

After a successful switch, update:
- `agentvault/ops/ACTIVE_CONTEXT_SNAPSHOT.md`
- `surething-offline/docs/OPERATOR_API_CONTRACT.md`
- the open PR #2 comment thread

Record:
- which method was used
- whether auth is live
- whether storage is merely local durable or verified persistent-volume durable
- what the console is now allowed to claim

That closes the loop and prevents the next move from guessing.
