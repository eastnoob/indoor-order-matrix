# Distance backend contract probe

**Current disposition, 2026-11-03:** `.17.4a` is complete. The [readiness probe](distance-readiness-probe-2026-11-03.py) passed 72 nonspatial insertion-order/count/lineage checks under guarded Pixi NetworkX 3.6.1. Scalar labels plus deterministic tight-predecessor recovery are selected for the first implementation; no second normal-path Dijkstra. [Readiness evidence](distance-readiness-2026-11-03.md) supersedes the historical pending decision below. IFC performance and full-pair resource measurements remain implementation acceptance.

Date: 2026-11-02  
Scope: `.17.4a` bounded probe; no distance implementation, dependency change, or IFC run.

## Environment

The Pixi lock exposes `networkx 3.6.1` and `numpy 2.4.3`. A plain `pixi run
python` on this Windows host also places the user site directory before Pixi's
site-packages, so it imported an unrelated `networkx 3.7` until
`PYTHONNOUSERSITE=1` was set. All contract probes must therefore set
`PYTHONNOUSERSITE=1` and record `sys.executable` plus the imported package
paths; otherwise the run is not a reproducible Pixi probe. The probe conclusions
below are accepted only for the locked Pixi packages under that environment
guard.

The current Pixi environment exposes `networkx 3.6.1` and `numpy 2.4.3` under
that guard.
`scipy`, `igraph`, and `tcod` are not importable. The old note claiming that
SciPy 1.17.1 was already available is not valid for this workspace.

## Probe results

- NetworkX accepts floating non-negative edge weights.
- A virtual source edge carries a source-specific access offset and produces
  the expected floating shortest distance.
- Duplicate source-to-cell access observations can be reduced by an adapter to
  the minimum offset with stable provenance before graph construction.
- Under the guarded locked environment, a 10,000-cell in-memory 4-neighbor
  graph completed one Dijkstra run in `0.010076 s` on this machine. An earlier
  unguarded timing (`0.021565 s`) is superseded because it did not prove which
  NetworkX installation was imported. Both timings are only algorithm smoke
  checks, not IFC performance claims.
- Equal-cost paths change when edge insertion order changes (`s-b-t` versus
  `s-a-t`). NetworkX therefore cannot be trusted as the project's final
  deterministic tie resolver without an adapter-side recovery pass.
- Path state and source lineage can be recovered from selected node/edge
  records, but this is project adapter work rather than a native NetworkX
  output contract.

## Decision status

`.17.4a` remains **in progress**. NetworkX is suitable as a diagnostic oracle
and a possible bounded baseline, but the probe does not establish that it meets
the final IFC-scale performance or deterministic-path contract. SciPy remains a
candidate only if explicitly added and separately verified. No GitHub or
Consensus search was triggered because the current candidate set has not yet
failed every required gate; the next probe must test the adapter-side tie and
lineage recovery path before any package search.

## Commands

The probes were run through `PYTHONNOUSERSITE=1; pixi run python -` in the task
workspace, with the interpreter and imported module paths captured. They use
only in-memory graph structures and must not be treated as spatial or IFC
evidence. A probe that imports from `C:\\Users\\tianf\\AppData\\Roaming\\Python\\Python312\\site-packages`
is invalid and must be rerun under the guard.

