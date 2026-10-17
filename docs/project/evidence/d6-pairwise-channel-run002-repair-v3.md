# D6 pairwise channel run_002 repair_v3 record

Date: 2026-10-03

Artifact root: `D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v3`

This bounded repair creates a new `repair_v3` directory and preserves `run_001`, `run_002`, `run_002_repair_v1`, `run_002_repair_v2`, and their historical evidence. It does not modify production code, adapters, NeutralSceneV2, public API, formal tests, source IFC, or user Blender files.

## Independent oracle

`independent_validate.py` reads serialized fixture inputs and evidence only. It does not import the producer runner or producer eligibility, domain, union, or component helpers. It independently recomputes:

- domain validity from record presence, `geometry_parts`, ring closure, polygon validity, and positive area;
- wall/column eligibility from `level`, `status`, `geometry_valid`, and reconstructed polygon validity;
- occupancy as the union of valid furniture-group polygons plus independently eligible wall/column polygons;
- components as polygon parts of qualified-domain difference after the occupancy union;
- candidate geometry from serialized support source IDs and reconstructed source polygons.

The independent report records the exact source fields, formulas, and output paths.

## Mutation tests

`mutation_test_report.json` records six temporary-copy mutations: candidate geometry, source ID, candidate count, component count, excluded-wall occupancy, and invalid-domain topology promoted to computed. Each was expected to fail, did fail, and returned a nonzero validator exit status.

## Status and provenance

The input contract says missing domain geometry is a missing input condition and that dependent free-space/topology outputs remain `not_available`. v3 records `missing_domain_geometry` diagnostically, preserves the owner aggregate decision as `DEFERRED`, and does not invent a unified API status. Candidate provenance uses `candidate_support_source_ids` for sources supporting a candidate and `global_occupancy_source_ids` for sources included in global occupancy; the fixture assertion is recorded in the independent validation report.

## Visual and hash validation

The portable Blender executable was used for render and Blend readback. SVG parsing, PNG readback, and serialized candidate geometry checks pass. The manifest records bytes and SHA-256 for JSON, SVG, PNG, Blend, Markdown, Python, and backup artifacts. The final artifact manifest records the byte count and SHA-256 for every listed file; its own SHA-256 is independently recomputed after the final write.

Commands and output paths are recorded in `outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v3\validation_report.json` and `outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v3\independent_validation_report.json`.

## Real-IFC boundary

`real_ifc_audit.json` retains `adapter_rerun = false`; synthetic fixture results and native inventory counts are not used to infer real-IFC readiness.

STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR V3 REVIEW
