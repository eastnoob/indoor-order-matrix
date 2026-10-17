# D6 pairwise channel run_002 repair_v4 record

Date: 2026-10-03

Artifact root: `D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v4`

This bounded repair creates a new `repair_v4` directory and preserves `run_001`, `run_002`, `run_002_repair_v1`, `run_002_repair_v2`, `run_002_repair_v3`, their historical evidence, the source IFC, and user Blender files. It does not modify production code, adapters, NeutralSceneV2, public API, formal tests, dependencies, or source IFC.

## Blocker 1: status contract

For the fixture with a present `AnalysisDomain` record and missing geometry, the serialized diagnostic status is `not_available`, with `geometry_status = missing` and `reason_code = missing_domain_geometry`. Candidate evidence, profile, connectivity, component, and topology outputs are all `not_available`. The aggregate qualification decision is explicitly `DEFERRED` in the design record. The validator assertion fails if missing geometry is rewritten as `invalid`; no new unified API enum is introduced.

## Blocker 2: final artifact consistency

`mutation_test_report.json` is rebuilt before validation. Its six mutation cases use stable `<temporary-root>` placeholders, and the suite is run twice with identical normalized payloads. The final artifact manifest is written after all content is final, excludes itself, and is checked separately for fresh bytes and SHA-256 entries.

## Determinism and visual boundary

JSON/XML parsing, status-contract assertions, the six mutation tests, deterministic repeat comparison, manifest checks, git scope, and whitespace checks are bounded to the repair directory. The existing PNG, Blend, Blend1, and SVG are reused because the repaired missing-domain fixture is not part of the rendered panels; their content is rechecked before review. `real_ifc_audit.adapter_rerun` remains `false`.

STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR V4 REVIEW
