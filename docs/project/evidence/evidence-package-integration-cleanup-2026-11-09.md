# Evidence Package Integration Cleanup Evidence

Started: 2026-11-09; final scoped verification: 2026-11-10

Candidate workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/evidence-package-structure-e86`

Candidate base: common ancestor `8524943e` (`codex/group-axis-field-hierarchy`).
Reference implementation line: `a336524b -> 932f5fd0 -> 9f071266`.
The main worktree remains separate and retains its pre-existing dirty changes.

## Changes checked

- `features/field_core.py`: stale/unavailable audit-channel observation redaction and optional caller-supplied `dependency_graph` validation before package callbacks.
- `test/test_evidence_package_output.py`: regression coverage for redaction, compact in-memory dependencies, and callback-before-cycle rejection.
- Package structure, architecture, design index, and implementation-plan wording now distinguish raw identity-only reads from freshness-gated resolver/context reads; unavailable dependencies without a typed source output have no observation; published outputs keep compact references.

## Verification

Commands were run from the candidate workspace with Pixi's locked environment.

| Command | Result |
|---|---|
| `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py -q` | 53 passed |
| `pixi run python -m compileall -q features test` | exit 0 |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_group_distance_evidence_package.py -q` | 33 passed |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_group_axis_potential_preview.py test/test_group_axis_potential_field.py test/test_free_space_distance.py test/test_free_space_field_inspection.py -q` | 21 passed, 11 failures, 9 skipped; all 11 failures are `FileNotFoundError` for absent retained IFC replay artifacts |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_distance.py test/test_free_space_field_inspection.py -q` | 9 passed, 9 skipped |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_evidence_package.py test/test_free_space_package_publication.py -q` | collection blocked by existing relative-import-beyond-top-level-package errors |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_evidence_package_freshness.py test/test_group_distance.py test/test_group_distance_evidence_package.py test/test_group_distance_clearance.py test/test_free_space_distance.py -q` | 149 passed, 10 skipped, 3 clearance failures because environment has `networkx==3.7` while that test's numerical contract requires `3.6.1` |

The missing replay files and relative-import collection failures are inherited
fixture/workspace limitations, not failures in the changed evidence-package
core. No full-suite, real IFC, Blender, or NetworkX 3.6.1 rerun was performed.

## Boundary conclusion

The candidate is technically ready for owner review as an isolated integration
checkpoint. It is not a mainline merge. Moving the mainline bookmark remains a
separate authorized action after the owner accepts the candidate and its stated
fixture/version limits.

## 2026-11-10 design review and repair

Superpowers design/code review identified five contract/documentation edges:
the diagram mixed runtime output fields with outer package records; channel
algorithm identity is package-function-level in the current runtime; freshness
is supplied to the resolver by its caller; indirect-cycle checking only runs
when the caller supplies the complete graph; and persisted JSON has no generic
typed decoder. The structure, output-contract, minimum-standard, architecture,
memory, index, and parent checklist now distinguish these boundaries.

The review also found that stale/unavailable dependencies were blocked only for
`computed` outputs. A focused regression for a `partial` output with a numeric
observation failed before the production edit (`DID NOT RAISE`), then passed
after the output boundary rejected every non-null observation from such a
dependency. The two stale/unavailable observation regressions pass. Current
focused verification is 53 passed across evidence-package output, field-core,
and freshness tests; `compileall` exits 0. The package consumer migration and
mainline integration remain pending.

The follow-up spec correction now separates failure behavior precisely:
stale/unavailable freshness produces a `not_available` dependency status and
forbids a non-null derived observation; output status and reason text remain
the consuming package's responsibility. Typed readback rejects missing or
mismatched identities, while indirect cycles are rejected before callbacks
only when the caller supplies a complete graph. Independent review found no
remaining blocking mismatch. Independent verification from the candidate
workspace reran
`$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py -q`
(53 passed, exit 0) and
`pixi run python -m compileall -q features test` (exit 0). The resulting spec
SHA-256 is `695F62DF505AC4AF307388D2A3D77669D464226F42D3D3A0737E43AFBB6668E0`.
