# Technical Corrections — 2026-03-22

This file is the canonical correction layer for the current public `surething-offline` kit.

## Superseded surfaces

Treat these as superseded until edited in place:

- `modules/02_hyperloop.md`
- `MASTER_CONTEXT.md` where the operator language implies stronger mathematical or empirical support than the current implementation provides

## E8 correction

Do not describe a hash-derived 8D vector as reproducing the E8 root system.

Use the hash only to index an exact canonical E8 object.

### Exact rule

- E8 root system: fixed canonical set of 240 roots in R^8
- E8 Lie algebra dimension: 248
- `N = 248` is a dimensional anchor only
- the hash may choose:
  - a signed permutation or symmetry action
  - an ordering of roots
  - a projection basis
  - rendering parameters

### Replace fuzzy checks with exact checks

Do not use an approximate angle threshold.

Use these exact checks instead:

- `root_count == 240`
- `rank == 8`
- normalized Gram-spectrum matches canonical E8 exactly
- reflection closure holds

## Hyperloop correction

Treat Hyperloop as a deterministic event-selection and visualization scaffold over an append-only spine.

Allowed claims:

- exact symmetry-indexed geometry
- reproducible hash-conditioned projections
- typed event provenance
- falsifiable state-correlation experiments

Not supported:

- proof that arbitrary hash bytes generate E8
- exact detection of subjective maximal awareness
- proof that AI integration implies consciousness

## Composite proxy correction

Rename CPF to `Composite Phenomenology Proxy`.

Use it as an experimental composite correlate rather than a solved definition.

Recommended operational form:

```text
CPF_t = z(ISD_t) + z(phi*_t) + z(report_consistency_t) - z(Brier_t)
```

Where:

- `ISD_t` = integration/segregation dynamics statistic
- `phi*_t` = chosen operational integration metric
- `report_consistency_t` = within-subject agreement or no-report concordance
- `Brier_t` = self-prediction calibration error

## Migration rule

Until the older files are edited in place, operators should prepend or cite `OPERATOR_OVERRIDE_V3.md` in active sessions using the public kit.
