# Vercel Durability Note

Purpose: prevent false durability claims when deploying the operator spine on Vercel.

---

## Current live deployment fact

The current production deployment for `evez-operator` is still sourced from `surething-offline` commit:

- `b76bb6094f12a66c8017f2452093b79078626964`

That means the durable/auth-capable spine entrypoint is **not live yet**.

---

## Platform reality

Based on the current Vercel documentation path reviewed during this convergence work, Vercel positions persistent data for functions around external storage services such as:
- Upstash Redis
- Vercel Blob
- other dedicated storage integrations

The docs surfaced examples of production persistence using external storage drivers rather than making a broad promise that function-local filesystem writes are durable across redeploys/replacements.

That means the safe operating assumption is:

- SQLite inside the function/project filesystem may improve local/process continuity
- but it must **not** automatically be treated as platform-durable persistent history on Vercel
- especially not across redeploys, replacement instances, or infrastructure churn

---

## Honest durability ladder on Vercel

### Level 1 — session/process-bound
Current live `api/index.py` behavior.

Safe label:
- `ephemeral`
- `session-bound`

### Level 2 — local durable implementation
When `api/index_durable.py` is active and SQLite writes succeed locally.

Safe label:
- `durable local store`
- `platform durability unverified`

### Level 3 — verified persistent storage
Only after the storage backend is externalized or otherwise verified to survive redeploys/replacements.

Safe label:
- `durable`
- `persistent backend`

---

## What not to claim on Vercel yet

Do not claim any of the following merely because SQLite is enabled:
- permanent ledger
- redeploy-safe persistence
- persistent-volume durability
- immutable historical retention across platform replacement

Those claims require verification beyond local file writes.

---

## Recommended path for true durability

If the operator spine must be honestly durable on Vercel, prefer one of these paths:

1. move event persistence to an external durable store
2. use a platform/storage layer with verified persistence semantics
3. keep SQLite only as an implementation bridge and label it conservatively until redeploy survival is proven

---

## Console implication

The mobile operator console should keep these distinctions visible:
- `ephemeral`
- `durable local store`
- `platform durability unverified`
- `persistent backend`

This preserves trust and keeps the UI from overstating what the backend actually guarantees.
