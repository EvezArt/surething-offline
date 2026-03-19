# Persistent Backend Options

Purpose: define the honest persistence path for the EVEZ operator spine once Vercel-local SQLite stops being sufficient.

This document assumes the current state is:
- live production still runs the old in-memory spine entrypoint
- `api/index_durable.py` exists as a durable/auth-capable replacement candidate
- SQLite may improve local durability but must not automatically be treated as redeploy-safe persistent history on Vercel

---

## Decision frame

The operator spine needs persistence for:
- append-only event history
- stable `height`
- stable `tip`
- replayable ledger reads
- verifiable continuity across deploy/restart/replacement

The persistence layer must preserve these truths:
- event hashing semantics stay stable
- route surface should remain stable
- clients should not need a rewrite just because storage moves

That means the storage backend should sit behind the spine contract, not replace it.

---

## Recommended backend classes

## Option 1 — external relational database

Examples:
- Postgres-compatible database
- managed SQL backend

### Why it is strong
- straightforward durable storage model
- good fit for append-only rows
- supports indexes, replay, analytics, and auditing
- easier to model chain continuity and event uniqueness

### Good fit for operator spine?
Yes. This is the strongest general-purpose long-term option.

### Best use
- durable event ledger
- contradiction history
- deploy-health snapshots
- future authenticated operator writes

### Tradeoff
- more infrastructure than local SQLite
- requires connection management and credentials

---

## Option 2 — external key-value / Redis-style store

Examples:
- managed Redis / KV system

### Why it is useful
- simple remote persistence
- fast writes and reads
- convenient for tip pointers, counters, and ephemeral/hot indexes

### Good fit for operator spine?
Partially.
Good for:
- current height
- current tip hash
- fast recent-event access

Less ideal for:
- long-term append-only audit as the sole source of truth
- rich historical querying unless carefully modeled

### Best use
- cache + hot index layer
- supplemental state next to a stronger ledger backend

### Tradeoff
- easy to drift into mutable operational state instead of a true ledger
- historical replay/audit semantics need more discipline

---

## Option 3 — object / blob storage append log

Examples:
- blob/object storage with event segments or snapshots

### Why it is useful
- durable object retention
- cheap storage for archived event batches
- good for snapshots/export history

### Good fit for operator spine?
Partially.
Strong as an archive layer.
Weak as the only live mutable index unless paired with another backend.

### Best use
- event snapshots
- cold archive
- export / backup

### Tradeoff
- append/read semantics are more awkward for a live API
- height/tip lookups are less convenient without an index layer

---

## Option 4 — keep SQLite, but move it to truly persistent infrastructure

Examples:
- VM/container with persistent volume
- service where filesystem persistence is explicit and verified

### Why it is useful
- minimal code change from current `DurableSpineStore`
- preserves current implementation path
- easiest short-term migration if a persistent volume exists

### Good fit for operator spine?
Yes, if the platform durability is actually verified.

### Tradeoff
- depends entirely on the runtime/storage guarantees
- not acceptable if persistence semantics are unclear or ephemeral

---

## Recommended order

### Best long-term architecture
1. relational durable ledger backend
2. optional KV/cache layer for hot reads and counters
3. optional blob/archive snapshots

### Best short-term honest upgrade
1. move the durable spine to infrastructure with verified persistent storage
2. keep labels conservative until restart/redeploy persistence is proven
3. later migrate to relational backend if operational scope expands

---

## Storage truth labels

Use these labels precisely:

### `ephemeral`
- in-memory only
- lost on restart/redeploy

### `durable local store`
- stored on local filesystem/database
- survives some restarts
- platform durability not yet verified

### `persistent backend`
- backed by an external or verified persistent storage system
- durable across deploy/replacement by design

### `archived`
- retained in object/blob/snapshot form
- not necessarily the live write index

---

## Recommendation for EVEZ right now

### If the goal is the fastest honest upgrade
Move the operator spine to a runtime with verified persistent storage and use the current SQLite-backed durable store there.

### If the goal is the strongest production topology
Adopt an external relational backend as the operator ledger source of truth, then optionally use KV/blob as supporting layers.

### If staying on Vercel
Treat local SQLite as an implementation bridge only, not as guaranteed persistent truth, unless redeploy persistence is explicitly verified.

---

## Console implication

The mobile operator console should expose the backend truth level it is actually connected to:
- `ephemeral`
- `durable local store`
- `persistent backend`
- `archived`

This is the only way to keep the interface powerful without turning it into lying theater.
