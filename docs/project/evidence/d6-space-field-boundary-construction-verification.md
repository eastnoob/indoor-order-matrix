# D6 boundary construction verification report

- Date: 2026-10-02
- Result: `verified_semantic_reproduction_with_disposable_blender_preview`

## Fresh commands

- `.pixi\\envs\\default\\python.exe -m py_compile scripts/design/space_field/run_boundary_construction_experiment.py scripts/design/space_field/render_boundary_construction_preview.py scripts/design/space_field/verify_boundary_construction_experiment.py` — exit `0`
- `.pixi\\envs\\default\\python.exe scripts/design/space_field/run_boundary_construction_experiment.py --output outputs/design/space_field_boundary_construction_experiment` — exit `0`
- `.pixi\\envs\\default\\python.exe scripts/design/space_field/run_boundary_construction_experiment.py --output outputs/design/space_field_boundary_construction_experiment/tmp_reproduction_20261002` — exit `0`
- `D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b --factory-startup --python scripts/design/space_field/render_boundary_construction_preview.py` — exit `0`; output limited to the disposable experiment directory.
- `D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b outputs/design/space_field_boundary_construction_experiment/boundary_construction_preview.blend --python-expr <read-only object inventory>` — exit `0`; read 18 disposable objects including the four candidate objects. Local user extensions emitted permission/unregister warnings during shutdown; no current user scene was opened or saved.
- `.pixi\\envs\\default\\python.exe scripts/design/space_field/verify_boundary_construction_experiment.py --primary outputs/design/space_field_boundary_construction_experiment --reproduction outputs/design/space_field_boundary_construction_experiment/tmp_reproduction_20261002` — exit `0`

## Reproduction

The following primary and temporary artifacts were byte-identical and
semantically identical: `boundary_comparison.json`, `fixture_manifest.json`,
`source_geometry.json`, `provenance.json`, `real_ifc_shadow_inspection.json`,
and `boundary_construction_diagnostic.svg`.

The primary artifact manifest contains 11 valid entries, including the
disposable Blender `.blend`, `.blend1` backup, PNG, JSON, and SVG files. Every
entry exists with matching byte count and SHA-256. The temporary directory is
not referenced by the primary manifest.

The PNG was inspected as a non-empty 1000 × 760 RGBA image. The SVG parsed as
XML and contains the required labels: `physical wall field`, `inner wall face`,
`outer wall face`, `wall centerline`, `authored closed curve`,
`automatic/derived candidate`, `candidate not accepted`, `user-confirmed`,
`not_verified`, and `not_available`.

The disposable Blender render required bounded repairs for argument forwarding,
JSON layer selection, Blender 5.2 engine enum, and missing World creation.
The final portable Blender process rendered both requested outputs. Blender
also emitted a thumbnail-directory warning; the target PNG write succeeded.

## Scope audit

- `features/`: unchanged;
- `adapters/`: unchanged;
- formal tests: unchanged;
- public API and dependencies: unchanged;
- source IFC: unchanged;
- current user Blender: not observed and not modified;
- free-space/connectivity/path: not computed;
- production boundary backend, mesh/polygon, resolution, route width, and
  threshold: not selected.

The repository's existing dirty/untracked state was preserved. No `git add .`,
commit, or source-scene cleanup was run.

See [verification_report.json](../../../outputs/design/space_field_boundary_construction_experiment/verification_report.json), [artifact_manifest.json](../../../outputs/design/space_field_boundary_construction_experiment/artifact_manifest.json), and [command_log.json](../../../outputs/design/space_field_boundary_construction_experiment/command_log.json) for machine-readable evidence.
