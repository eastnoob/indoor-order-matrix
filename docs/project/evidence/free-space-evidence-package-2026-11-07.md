# Free-space evidence package — 2026-11-07

Workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_evidence`.
Starting base: `58fdf846`. Root is the sole version writer. Prior dirty proxy
route-repair files remain outside this implementation's scope.

## Current status

The user authorized implementation of one descriptive free-space evidence
channel using the existing package standard. The implementation and independent
verification are complete in this isolated JJ workspace; accepted local
checkpoint is recorded separately below. This ledger records execution evidence;
it introduces no new framework, package standard or metric specification.

## Authorized implementation boundary

| Location | Responsibility |
| --- | --- |
| `features/free_space_evidence_package.py` | `build_free_space_evidence_package` factory, source-envelope projection and `build_free_space_package_contract` using shared contracts |
| `adapters/free_space_evidence_package.py` | `evaluate_free_space_package(scene, request, cache_directory=None)` and `evaluate_saved_free_space_package(snapshot)`; existing executor/codec reuse and cache authentication |
| `scripts/design/space_field/run_free_space_evidence_package.py` | Publish already retained evidence, shared output/contract/status, source receipt and visualization manifest |
| Native preview script | Read that same package and manifest; produce `free_space_evidence.png` and `free_space_evidence.blend` with the approved portable Blender |

The computation entry point owns its prerequisite free-space calculation via
the reusable `execute_analysis_request`/`FreeSpaceField` path. The saved reader
accepts an authenticated `ReadOnlyResultSnapshot`. Both use the ordinary
`EvidencePackage.evaluate(source_envelopes)` function and return the existing
`EvidencePackageOutput`; no parallel package type or changed evaluate signature
is introduced.

Exactly one derived descriptive channel, `free_space`, is emitted per cell. A
single field-scope `FieldResultEnvelope` retains the compact `free_space_run`
document once. Every cell output has source-channel lineage and
`observation.cell_locator = {row, column, cell_index, result_ref}`. The exact
locator resolves the original sample with `value`, `status`, `query`, `support`,
`source_ids`, `provenance` and `explanation`. The raw Boolean remains physical
occupancy (`True` occupied, `False` known empty). All six raw states remain
distinct: `established`, `conditional`, `unknown`, `outside`, `invalid`,
`not_available`. Envelope/output computation status does not replace those raw
states. The package adds no clearance, accessibility, score or room-model field.

## Cache and freshness boundary

The cache retains a validated compact document and shared package contract plus
an HMAC receipt tag held in the cache directory's separate signing-key file. A
miss invokes the existing calculation and serializer. A valid hit skips geometry
and field generators and rebuilds only the cheap output projection. Whole-package
dependencies bind source, domain/scope, query, plane, sampling and computation
and package implementation/schema versions. Validation must cover the retained
document's digest and its association with the cached contract. A changed input
cannot be reported as a hit merely because an old package status said fresh.

Cache origin remains the exact retained result; it is not relabeled as a current
native observation. Computation relative to supplied scene/request data and
independently verified live native currentness are separate claims. The saved
publication uses the shared freshness comparison with no current contract:
`freshness="unavailable"`, `read_state="historical"`. Authentic retained samples
remain usable historically. Self-comparison of a saved contract is not evidence
that the scene is unchanged.

## Independently retained source and planned delivery

| Item | Retained input expectation |
| --- | --- |
| Kind | `free_space_run` |
| Result ID | `fe3243c13b3f45daac8744efc46f3962` |
| Digest | `a22de58adc39c241ccb514afd52f2c1b7bbf4819f7ffb93d6a125aac92f4c120` |
| Lattice targets | 24,442 |
| Known free / raw occupied `False` | 14,047 |
| Occupied / raw occupied `True` | 7,023 |
| Outside / raw value `None` | 3,372 |
| Planned output directory | `outputs/design/free_space_evidence_package/run_20261107/` |

The runner authenticated the explicit ResultRef with separately retained
consumer expectations, then published without geometry projection or occupancy
regeneration. Artifacts are `free_space_package_output.json`,
`package_contract.json`, `package_status.json`, `source_manifest.json`,
`publication_receipt.json`, `visualization_manifest.json` and
`free_space_plan.svg`. Native preview artifacts use the same package/manifest.
The source is the retained job result at
`D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/outputs/blender_analysis/jobs/fe3243c13b3f45daac8744efc46f3962/result.json`;
publication took 30.188 s, with 23.448 s authenticated projection. The output
identity is `d5d694f0b4954510942d15d556715dd5410a2551c9c17cf64e6dec5a41607e4e`;
the package identity is `bc9df22c10346eaf2f891f2b52a8aceccc892b78ddbfbdcdae2f6514484d9a70`.
The full artifact hashes are in `publication_receipt.json` and the native hashes
are in `native_preview_receipt.json`.

## Verification record

| Check | Status / evidence |
| --- | --- |
| Shared package shape, one channel and complete cell scope | PASS — focused package/publication/preview suite 37 passed; independent verifier matched 24,442 targets |
| All six raw statuses and exact recovery of seven sample fields | PASS — fixture suite covers all six statuses; retained IFC itself observes established/outside only |
| Cache hit forbids geometry/field generators; miss/reuse/invalidation checks | PASS — cache and freshness suite covered by focused package tests |
| Tampered document/contract rejection and historical freshness | PASS — corrupt cache rejection and historical read checks pass |
| Actual retained-source counts, exact locators and provenance reconciliation | PASS — 14,047 free, 7,023 occupied, 3,372 outside; all locators and refs match |
| Actual publication command, timing, size and hashes | PASS — receipt and independent hash reconciliation |
| Portable Blender PNG/Blend generation and reopen verification | PASS — Blender 5.2.0 LTS, PNG 2400×1800, blend mesh counts match receipt |
| Independent specification and quality review | PASS — verifier: spec PASS, quality PASS; bounded raw-state coverage caveat |
| Accepted local jj commit / change | PASS — `codex/free-space-evidence-package` at `6a5da482` |

Relevant existing fixture families are in `test/test_analysis_requests.py` and
`test/test_blender_analysis_session.py`. They provide analytic scenes, missing
sources, substitute-backed samples, compact results and generator-forbidden
cache patterns. New package-specific test paths and actual command/results will
be recorded after implementation. No test pass or user visual acceptance is
claimed by this placeholder table.
