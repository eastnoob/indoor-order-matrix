# Distance readiness evidence — 2026-11-03

Decision: **READINESS ACCEPTED; design frozen for implementation.** This closes the preimplementation feasibility gate. It does not claim production distance code, a constructed IFC FreeSpaceField, full-pair measurements, or real route visualization.

## Guarded backend and tie probe

Command:

```powershell
$env:PYTHONNOUSERSITE='1'; $env:PYTHONPATH='.'
pixi run python docs/project/evidence/distance-readiness-probe-2026-11-03.py
```

Observed output recorded by the script:

- Pixi interpreter: `.pixi/envs/default/python.exe`.
- NetworkX `3.6.1` imported from the Pixi environment; no user-site package was used.
- 72 permutation checks passed over an in-memory 4-neighbor graph. The selected route and lineage were invariant to edge insertion order; conditional and optimistic counts followed the declared ordering.
- Peak `tracemalloc` for the bounded probe was `48,966` bytes and runtime was `0.00925 s`. This is nonspatial contract evidence only, not an IFC performance claim.
- The accepted route contract uses NetworkX scalar labels as numerical authority, then deterministic tight-predecessor DAG recovery. No second Dijkstra is used in the normal path. Recomposition residual and ULP diagnostics are recorded and never affect route/status selection.

The probe deliberately uses no furniture, layout, simulated geometry, route result, or IFC-derived distance.

## S4 confirmed handoff and grid seam

The same guarded probe audited `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`:

- `s4_confirmed_manifest.json`: `status=confirmed`.
- `s4_confirm_result.json`: `status=active`, `handoff_executed=true`, selected candidate `S4`, and active `analysis_domain` equal to the manifest's `confirmed_domain`.
- The manifest/result confirmation binding, request identity, candidate identity, candidate version, domain geometry references, source revision and camera-plane binding matched.
- The old `domain_result.json` remains `status=not_available` with `analysis_domain=null` and was explicitly rejected as a distance input.
- Pinned source bytes were rehashed: `408618044` bytes, SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`.
- Confirmed S4 scope area is `56.04000065088288 m²`, with bounds approximately `[0.30000001, 0.30000001] → [5.0, 12.30000019]` in the recorded plane coordinates.
- An explicit feasibility grid of `spacing=0.1 m`, origin `(0.3,0.3)`, `121` rows × `47` columns covers the confirmed domain. This is a probe parameter, not a silent production default; the implementation CLI must require `--spacing-m` or record an existing scene setting.
- The query fingerprint includes `domain_id`, `frame`, `plane=null`, `height_band=null`, `demand=null`, `tolerance=0.0`, and `revision`; metadata fingerprint was `602c2cc1b6502254f492a076c71b5377e386058ed46bc5eb86d234c592bda43c`.

The S4 result is a real retained prerequisite artifact. The grid and occupancy instance remain implementation work, and coordinate translation must be performed once by the scene-view handoff rather than by a second projection.

## Readiness ruling

The frozen implementation contract is in `docs/superpowers/specs/2026-11-02-group-distance-module-design.md`. The unresolved runtime checks are intentionally later: same-view group/occupancy/grid construction, all 37 groups and 666 unordered pairs, source-batched peak resource measurement, route/package reconciliation, and output-only camera-plane visualization. Missing or unobserved runtime states remain unclaimed.
