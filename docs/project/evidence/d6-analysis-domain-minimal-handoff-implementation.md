# D6 AnalysisDomain minimal private handoff — implementation delivery

Date: 2026-10-08 (Europe/Berlin). Status: **implementation delivered; independent code review pending**. Base branch/HEAD: `codex/d6-analysis-domain-layout-handoff` / `b2d6cccc3c6c7182f955398e03f40cb5ded951f0`. The [frozen design](../analysis-domain-minimal-handoff-design.md), its [independent ACCEPT recheck](d6-analysis-domain-minimal-handoff-independent-review.md), and the appended D1–D3 owner decision in [progress](d6-space-field-design-progress.md) bound this private first slice. The design remained at SHA-256 `04d41412fdf620d870cd7520fcfac5c6716fc232ef659a3ec19bc588b7977076` (25,562 bytes).

## Implemented seam

- `features/_analysis_domain_handoff.py` adds the session-local `domain_handoff` and focused geometry/state helpers. A source revision hashes canonical JSON from the current `NeutralSceneV2`; frame/request and candidate identities are separate hashes. `confirm`/`replace` check those identities and `expected_session_revision`. The in-memory action history keeps accepted/refused attempts, idempotent retries, conflicts and observed input invalidation. Refused replacement leaves a requalified old choice active; source/frame/candidate drift removes the consumable handoff and cannot silently resurrect the old choice after an observed drift. Hover and select only alter the returned ephemeral candidate display state.
- `features/neutral_scene_views.py` adds private `_analysis_scene_view_with_domain_handoff`. It calls the accepted `_analysis_scene_view_with_semantic_enclosure` only on an explicit B2 request and passes its actual `scope_proposals` to the helper. After a qualified confirmation, the helper constructs one session child with `AnalysisDomain`, calls existing `analysis_scene_view(child)`, and returns only a narrowed preview, exact polygon, current/attempt states and provenance. It never exposes the full analysis view or calls `evaluate_scene`, free-space, topology or route consumers.
- Authored candidate outlines come from the uniquely resolved mesh refs via existing `mass_patch_from_mesh` → `plan_projection` → `component_shape`; a separately supplied outline must be topologically equal. Inferred B2 scopes use the installed Shapely constrained triangulation to make a session-only derived `MeshGeometry3D`; its actual plan projection must equal the selected polygon. Both paths requalify immediately before handoff. The original source scene, source roles/participation, opening facts and physical wall/column occupancy remain unchanged.
- `test/test_neutral_scene_analysis_regression.py` adds composed private-entry cases for authored/inferred confirmation, exact shape and hole retention, mismatch/disjoint refusal, no candidate, several candidates without automatic choice, ephemeral hover/select, stale session/source/frame/candidate identity, rejected and accepted replacement, switch-back, duplicate/conflicting action IDs, authored/inferred disagreement acknowledgement, local unresolved aperture refusal, source/occupancy immutability and default view compatibility.

The supported first slice is one finite valid polygon in a compatible explicit metre analysis plane and caller datum/cut. Exact preserved holes work in the authored path. Disjoint components, missing/duplicate refs, mismatched or lost-hole outlines, unsupported projections, stale identities, unresolved local B2 apertures and incompatible frames refuse. The frozen real S1 is **not** activated: its A11/A12 local unresolved aperture evidence remains a blocking input; this implementation did not rerun that real cohort. Missing authored floor metadata alone does not refuse an otherwise caller-qualified frame. No global plane, threshold, backend or automatic winner is introduced.

## Executed verification

| Command | Exit/result |
| --- | --- |
| `pixi run python -B -m py_compile features/_analysis_domain_handoff.py features/neutral_scene_views.py` | Exit 0. |
| `pixi run pytest -q test/test_neutral_scene_analysis_regression.py -k private_domain_handoff` | Focused run: 7 passed, 51 deselected, exit 0; the later composed run covers final bytes. |
| `pixi run pytest -q test/test_neutral_scene_analysis_regression.py` | 58 passed, exit 0. |
| `pixi run pytest -q test/test_neutral_scene_analysis_regression.py test/test_scene_contract.py test/test_geometry_views.py test/test_geometry_substitutes.py` | Final composed run: 177 passed, exit 0. |

The focused loop had one intermediate failing test caused by a duplicate fixture candidate ID; the test used a standalone scene for the intended candidate-drift case and the final focused/composed commands above passed. No full suite, native IFC conversion, real S1 shadow, Blender run or rendering was performed in this assignment. The later independent code reviewer and one final full-suite owner will validate the frozen bytes separately.

## Review identities and scope

| Changed path | Final worktree SHA-256 | Bytes |
| --- | --- | ---: |
| `features/_analysis_domain_handoff.py` | `bd3b94711f9c9ad0f0de2c10acd7200dde434aa2a5d487925589985c75c9cf50` | 21,395 |
| `features/neutral_scene_views.py` | `c40cb306a1f2cddfa35eec4631bfe6de0ec369ecc0621089ae4ce38fcc8943bf` | 50,869 |
| `test/test_neutral_scene_analysis_regression.py` | `8311d5533ab541f9971dca994462841754665f40e87bb5bf929e18a248e74c9c` | 105,085 |

The report and one appended progress entry are the only documentation changes in this implementation task. Frozen design/review/B2 records, adapters, exports, config, dependencies, source IFC and user Blender files are untouched. `git diff --check` passes for the edited tracked source/test files; the new helper has no trailing whitespace. The index remains empty. This report claims the private backend handoff and its focused verification only, not public UI, formal space-field results or production release readiness.

## Bounded independent-review repair (2026-10-08)

The independent review reproduced three failures on the frozen first implementation. This repair changes only the private handoff helper and its regression module; the public/default view, B2 implementation, scene objects, frozen design and reviewer-owned files remain untouched.

- The session projection is now reduced from its action history before use. An accepted confirmation must carry the checked source/frame/request/candidate binding and exact acknowledged conflict identities; a claimed current selection or modified binding inconsistent with that history returns `inconsistent_session_state` and an empty, nonconsumable session. This is in-memory consistency checking, not cryptographic authentication of a caller that can fabricate a whole event log.
- Every current handoff rechecks opposite-source polygon disagreements against the exact candidate identities acknowledged at confirmation. A later incompatible authored candidate records observed conflict drift, increments the session revision and makes the old choice unavailable. A stale action then refuses; a fresh confirmation with the current conflict ID restores it and increments revision again. An equal-outline authored candidate leaves the inferred choice active.
- The private child view preserves an authored `source_id` as an occupancy shell only for a unique spatial/floor support source. For an unrelated source such as furniture, the child detaches the shell identity while preserving the original domain/source provenance in the returned choice and child provenance. The original scene and default public view are unchanged; the existing slab control remains a shell.

Regression tests exercise the real private entry for the forged/unconfirmed and mismatched-binding states, later incompatible and equal-outline authored arrivals, stale/fresh acknowledgement revisions, furniture occupancy retention and slab support. `pixi run pytest -q test/test_neutral_scene_analysis_regression.py -k private_domain_handoff` passed **10** tests (51 deselected). The final composed command `pixi run pytest -q test/test_neutral_scene_analysis_regression.py test/test_scene_contract.py test/test_geometry_views.py test/test_geometry_substitutes.py` passed **180** tests. `pixi run python -B -m py_compile features/_analysis_domain_handoff.py features/neutral_scene_views.py` and scoped `git diff --check -- features/neutral_scene_views.py test/test_neutral_scene_analysis_regression.py` both exited 0. The ledger's pre-existing CRLF history reports trailing whitespace under whole-tree `git diff --check`; its 40,893-byte prefix remains byte-identical. No full suite, native IFC conversion, real S1, Blender or rendering run was part of this repair.

Final repair identities on branch `codex/d6-analysis-domain-layout-handoff`, HEAD `b2d6cccc3c6c7182f955398e03f40cb5ded951f0`, empty index: `features/_analysis_domain_handoff.py` 28,388 bytes SHA-256 `7f05bcf40139732d3580e017d7bd20668cbf69d627865d1a67d4f165a2d75c15`; `features/neutral_scene_views.py` 50,869 bytes SHA-256 `c40cb306a1f2cddfa35eec4631bfe6de0ec369ecc0621089ae4ce38fcc8943bf` (unchanged); `test/test_neutral_scene_analysis_regression.py` 111,858 bytes SHA-256 `688109f2074547e272fcfc66656bcd4ce91b2500cc8a52c041086c1c52152b8c`. The original reviewer reproduction remains reviewer-owned and intentionally retains its old-failure assertions.

STOP FOR ANALYSISDOMAIN MINIMAL HANDOFF IMPLEMENTATION REVIEW
