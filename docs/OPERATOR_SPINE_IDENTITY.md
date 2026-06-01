# Operator Spine Identity

This repository is currently the live **operator/API spine** for the EVEZ system.

Although the repo name is `surething-offline`, the observed production role is closer to:

**logical name:** `evez-operator-api`

The current live deployment attached to this role is the Vercel project/deployment name:

- `evez-operator`

## What this repo is responsible for

This repo should be treated as the primary system of record for:
- operator API routes
- append-only operator spine events
- contradiction reporting
- deploy-status truth
- FIRE anchor payload construction
- MCP / HTTP control-plane surfaces used by AI operators and operator UIs

## What this repo is not

This repo is not the canonical public brand shell.
That role belongs to:

- `EvezArt/evez-os`

`evez-os` is the named public/product shell and visual/public surface.
This repo is the operator truth layer behind or beside that shell.

## Relationship to other layers

- `EvezArt/evez-os` → brand shell / public surface
- `EvezArt/surething-offline` → operator spine / API truth
- `EvezArt/evez-sim` → simulation lane
- `EvezArt/agentvault` → registry / memory / audit
- `EvezArt/CrawFather` → shared skills / souls / plugin layer

## Practical rule

If a feature is primarily about:
- live control-plane status
- contradictions
- operator ledger events
- deploy health
- operator tooling for AI/agents

it belongs here unless intentionally promoted or proxied elsewhere.

If a feature is primarily about:
- public shell
- product identity
- visual cognition surface
- branded dashboard/landing experience

it belongs in `evez-os`.

## Naming repair

The repo name and the live role are currently misaligned.
The safe interpretation today is:

- repository name: `surething-offline`
- live role: `evez-operator-api`
- deployment label: `evez-operator`

Docs and build briefs should use that distinction until a deliberate rename or migration happens.
