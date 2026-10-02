# D6 封闭房间 / AnalysisDomain candidate verification report

- 日期：2026-10-02
- 结果：`verified_semantic_reproduction_with_known_ifc_timestamp_difference`

## Commands

- exit `0` — `.pixi\envs\default\python.exe -m py_compile scripts/design/space_field/run_enclosed_room_domain_candidate_experiment.py`
- exit `0` — `.pixi\envs\default\python.exe scripts/design/space_field/run_enclosed_room_domain_candidate_experiment.py --output outputs/design/space_field_domain_candidate_experiment`
- exit `0` — `.pixi\envs\default\python.exe scripts/design/space_field/run_enclosed_room_domain_candidate_experiment.py --output outputs/design/space_field_domain_candidate_experiment/tmp_reproduction_20261002`

## Reproduction

- case_payload_equal: `True`
- priority_equal: `True`
- constraints_equal: `True`
- fixture_manifest_equal: `True`

All candidate semantics, priority resolution, constraints, and `fixture_manifest.json` matched the temporary reproduction. The JSON/geometry/provenance/SVG artifacts matched byte-for-byte. The disposable IFC differs only in the auto-generated IfcOpenShell `FILE_NAME` timestamp; its stable fixture ids and observed payload remain equivalent.

## Artifact hashes

| Artifact | Primary SHA-256 | Reproduction SHA-256 |
|---|---|---|
| `candidate_results.json` | `39fab218db7a161b9b32be1a376e485b3d8edc6d6179090f6a73d01ee66ffdf4` | `39fab218db7a161b9b32be1a376e485b3d8edc6d6179090f6a73d01ee66ffdf4` |
| `fixture_manifest.json` | `c453baf033938a32fb5a366b6331d98e1e9428c86c1552c3b61571ab95783041` | `c453baf033938a32fb5a366b6331d98e1e9428c86c1552c3b61571ab95783041` |
| `source_geometry.json` | `118b36c5a586fc0cca1bcaa7e3ff261be41667333c8c063d2818bf5cb4146791` | `118b36c5a586fc0cca1bcaa7e3ff261be41667333c8c063d2818bf5cb4146791` |
| `provenance.json` | `0ee99a0c4fc9c48b04c06b976cedeab777bfb1a74f5a3e0a7de1f7f6390ed294` | `0ee99a0c4fc9c48b04c06b976cedeab777bfb1a74f5a3e0a7de1f7f6390ed294` |
| `interaction_states.svg` | `ddd28e73490fa19c9027d48466df7b01a3e83ef040ceebfdf2dce188c5028f9f` | `ddd28e73490fa19c9027d48466df7b01a3e83ef040ceebfdf2dce188c5028f9f` |
| `fixture_workspace/ifc4_description_fixture.ifc` | `b76e8512b5ad3e37ce51181f6a43286225b002cf257652403ad6757618a1c249` | `2b0023577a8a80a1581b758bbf7b18be203d618d238ee87d95bd88071cea85db` |

## Scope audit

- production `features/`: unchanged
- `adapters/`: unchanged
- formal tests: unchanged
- public API/dependencies: unchanged
- source IFC and user Blender: unchanged
- live IFC geometry adapter: `not_verified`
- free-space/connectivity/path: `not_computed`
- production backend/resolution/threshold: `not_selected`

The temporary output is under `outputs/design/space_field_domain_candidate_experiment/tmp_reproduction_20261002/`, inside the allowed experiment output root.
