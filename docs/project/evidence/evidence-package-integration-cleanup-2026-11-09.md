# Evidence Package Integration Cleanup Evidence

Started: 2026-11-09; core-subset verification: 2026-11-10;
saved-snapshot rollout locally verified on 2026-11-10; mainline integration
remains separate.

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

These results describe the initial core-subset check on 2026-11-10. The missing
replay files and relative-import collection failures were fixture/workspace
limitations at that check. The continuation below uses located retained
artifacts; it must record actual reruns before treating these limits as
resolved. No full-suite, Blender, or NetworkX 3.6.1 rerun was performed here.

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

This paragraph records the review's earlier state. The saved-snapshot rollout
below supersedes its decoder limit and resolves channel tracing through
existing metadata rather than a new type hierarchy.

The review also found that stale/unavailable dependencies were blocked only for
`computed` outputs. A focused regression for a `partial` output with a numeric
observation failed before the production edit (`DID NOT RAISE`), then passed
after the output boundary rejected every non-null observation from such a
dependency. The two stale/unavailable observation regressions pass. Current
focused verification at that core-subset checkpoint was 53 passed across evidence-package output, field-core,
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

## 2026-11-10 saved-snapshot rollout

The owner continued the existing plan; no new plan or mainline merge was
authorized. The core-subset checkpoint is `51b8c6e7`, mainline remains
`14eca2e7`, and original reference bookmark remains `9f071266`. Root alone
writes JJ history. Preserve unrelated dirty work and the free-space bookmark
conflict; no remote push.

Fixed-v1 JSON readers reuse existing validated envelope/output types. Required
saved output identity detects declaration/identity drift; serialized-only
`payload_fingerprint` hashes complete canonical saved content excluding itself,
including values, states, provenance and source/recipe fingerprints. This is
not a new typed output property. Computation identity deliberately excludes
readings/statuses; empty dependencies are omitted to restore historical
publication IDs. Legacy no-dependency/no-fingerprint files remain readable with
exact artifact SHA and fresh contract comparison.

| Package/source | Retained artifact and original boundary | Algorithm and input tracing | Replay acceptance |
| --- | --- | --- | --- |
| Free-space | Free-space workline `outputs/design/free_space_evidence_package/run_20261107/`; complete 24,442-cell publication, one `free_space` reading per cell and original physical occupancy retained. | Channel provenance declares producer, algorithm/schema and output function/version; `derived_from` points to the compact field-scope source whose cache identity binds the exact document and recipe. | Fixed-schema decode, independent source reconstruction and selected-channel readback are recorded in the retained report. Freshness applies only to the pinned reconstruction; live scene was not observed. |
| Group distance | Distance workline `run_global_full_current_20261106_merged/distance_evidence_package/`; `euclidean_distance` and `path_distance` stay separate. | Output provenance declares adapter method, output/schema versions, underlying distance versions, query/plane, dependency fingerprints and exact free-space ResultRef. Source lineage preserves each original pair. | Two different targets of `path_distance` were consumed together; wrong scope and changed plane were rejected. Freshness applies only to pinned retained inputs. |
| Axis potential | Main workline `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z/`; 37 source envelopes and 4,112 outputs. | Existing output provenance declares method/formula and algorithm/schema; source `cache_identity` and `derived_from` bind actual axes. Package function/version remains the enclosing identity. | Roundtrip and original producer-order reexecution preserve all outputs/sources. Sorted-source replay only permutes a historical audit list; no distance input or new formula was added. |
| Geometry | Existing IFC-derived world-plane envelope publication, read as source adapter. Member-pair observations remain audit-only; aggregation remains deferred. | Channel method plus `inherits_top_level` uses envelope algorithm/schema/source fingerprint; cache identity binds query, recipe and input. | Read 666 envelopes from `outputs/design/group_geometry_relation_field_ifc/run_20261028T115320Z_5135f3/envelopes.json` (SHA-256 `ca6796e6909be950080bf593ab253c35e285818c5dd7b1d35d5ddafc78b8aaa1`); all fields preserved. |
| Trend | Existing IFC-derived world-plane envelope publication, read as source adapter. Preserve saved channel sets and suppressed/public metadata. | Channel method plus `inherits_top_level` uses envelope algorithm/schema/source fingerprint; source cache identity and plane remain intact. | Read 37 envelopes from `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/envelopes.json` (SHA-256 `de0434b947e562b0ed9f486fe134da118e5d25b81199582dc9374903336534c0`); preserved four historical raw names while marking two as audit-only. |

These producers already carry the metadata required for channel algorithm and
input tracing; lack of a separate typed channel-algorithm object is not an
unfinished responsibility. The actual legacy omission is the newly introduced
serialized full-payload fingerprint, handled by artifact SHA and fixed-schema
identity checks during old-file replay. Per-channel complete content can be
fingerprinted with `fingerprint_evidence_dependency(output_channel)`.

The camera-plane free-space/distance snapshots share native IFC, query and
exact ResultRef `fe3243c13b3f45daac8744efc46f3962`, digest
`a22de58adc39c241ccb514afd52f2c1b7bbf4819f7ffb93d6a125aac92f4c120`.
Their complete cell scope is 3,372 outside plus 21,070 established, including
14,047 free and 7,023 occupied cells. Retained potential/trend/geometry use
world-plane Z0 and another query; no matching camera-plane publications were
found. This prevents a distance-to-potential business integration claim.

The distinct output-only readback `EvidencePackage` uses full
package/output/target/channel addresses, selected refs, pinned file SHA,
freshly built current contracts and a complete graph matching actual
declarations. Fresh reads preserve observation/status/scale; stale/unavailable
reads have `observation=None`. Two different targets of the same distance
channel must actually be read in one result. The original potential's unused
optional stale dependency must leave independent pure-axis outputs intact.
Original packages and source adapters remain unchanged by this readback view.

Owner-reported core verification from the candidate workspace:

| Command/evidence | Result |
| --- | --- |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py -q` | 91 passed |
| Output-only RED before implementation | 33 failed, 18 passed; confirms the missing saved-readback cases before the repair |
| Compileall for core, focused tests and existing potential replay | exit 0 |

The complete retained replay report is
`outputs/design/evidence_package_readback/run_20261110T100740Z/report.json`
(SHA-256 `0412f58333a142477510cc2cd7755d0054e7a5b3e2ca2c5172e1dd3cfa2a7bfe`)
and records `errors: []`, exact source counts/hashes, the two-target distance
readback, plane mismatch refusal, missing-context redaction and the historical
potential ordering failure plus its correction. The scoped P1 review approved
the adapter with no remaining findings. Earlier missing-fixture/version failures
remain dated history and are not silently reclassified as current runs.

Continuation review found that package-ID equality alone could pair a current
contract from snapshot B with saved output A. Before numeric readback the
consumer must bind independently supplied current source envelopes against the
saved source/query/scope/cache identities and source reading content. Missing
current source evidence yields unavailable; input/query/plane mismatch is
rejected. Historical/current top-level audit labels alone must not invalidate
otherwise identical input content. The P1 probe used wrong-scope cached/current
contracts of the same package and incorrectly admitted a real distance reading
of approximately 5.21766 as fresh. Core review had no other findings. The
repair, focused tests and retained replay are complete; the scoped P1 review
approved the adapter with no remaining findings.

The repair interface is
`consume_saved_evidence_package(..., current_source_envelopes=...)`. Before
numeric use its independent current sources must match a binding signature of
`target`, `query`, `channel_set`, `cache_identity`, `raw_status`, `value`,
`support` and `source_ids`. The signature includes source readings and channel
records, but excludes outer audit provenance such as `source_freshness` and
visualization. Absent current context yields unavailable; a mismatch is refused.
The adapter also rejects a cached contract whose target scope is unrelated to
the saved source/output targets. The exact source-context refresh command is
recorded in `outputs/design/evidence_package_readback/run_20261110T100740Z/REPRODUCE.md`;
that refresh reads the existing full report rather than regenerating the heavy
roundtrip.

The first retained replay also stopped with `AssertionError` in the potential
reexecution comparison. This was localized to source ordering: runtime outputs
sort their source envelopes by cache identity, while the historical callback
wrote its `per_group` audit list in producer-envelope order. The saved-output
roundtrip preserves all 4,112 outputs and 37 sources exactly and retains the
historical `83802ece…` output identity. Reexecution using the original
`envelopes.json`, SHA-256
`de0434b947e562b0ed9f486fe134da118e5d25b81199582dc9374903336534c0`,
reproduces all 4,112 outputs exactly. Reexecuting from runtime-sorted sources
only permutes that audit list. This is an original-input-order determinism
boundary, not a need to change the algorithm/formula/version in this task.
The final report retains the failed comparison and its corrected input binding.

## Final local verification — 2026-11-10

The report pins three independently sourced package contexts: free-space from
the original compact result, distance from the retained input bundle and saved
repair result, and potential from the separately retained producer-order
envelopes plus its IFC digest. It confirms exact output/source roundtrips and
re-evaluations for 24,442 free-space outputs, 1,332 distance outputs across
666 pairs, and 4,112 potential outputs across 37 sources. The report also
preserves 666 geometry and 37 trend source envelopes; these are adapters, not
new package producers. Its current completion block records the P1 source and
scope review as independently approved.

Fresh candidate checks, run with Pixi from the candidate workspace:

| Command | Result |
| --- | --- |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py test/test_evidence_package_readback.py test/test_group_distance_evidence_package.py -q` | 165 passed |
| `pixi run python -m compileall -q features/field_core.py scripts/design/group_level/run_group_axis_potential_ifc_replay.py scripts/design/group_level/replay_evidence_package_readback.py test/test_evidence_package_output.py test/test_evidence_package_readback.py` | exit 0 |
| Free-space package/publication tests under a temporary in-memory package alias, with pytest importlib mode | 26 passed |
| `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_readback.py -q` | 22 passed |

The earlier direct free-space collection errors were caused by this isolated
candidate directory's non-package name and package-relative test imports. The
temporary alias test invocation loads the candidate root as a package without
changing repository files. Historical broad-suite limits remain: missing IFC
fixtures in unrelated legacy tests and the recorded NetworkX 3.7 versus 3.6.1
clearance expectation. No full suite or live scene/native visualization replay
was run in this continuation. Exact refresh and replay scope are documented in
`outputs/design/evidence_package_readback/run_20261110T100740Z/REPRODUCE.md`.

The local checkpoint advances only the candidate integration bookmark. The
mainline, original reference bookmark, unrelated main-workspace changes and the
existing free-space bookmark conflict remain outside this change. No merge or
push was performed. Distance-to-potential business integration remains
unimplemented because the retained distance and potential snapshots use
different query planes.
