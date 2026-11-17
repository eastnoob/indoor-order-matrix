# Wall Domain and Camera Prerequisite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Maintain the checkboxes during execution and attach verification evidence before marking them complete.

**Goal:** Recover the existing native camera and selected-wall enclosure workflow so the approved IFC can supply an explicitly confirmed domain projected onto its selected analysis plane before distance work begins.

**Architecture:** Reuse the implemented Spec008 dependency closure and the existing B4/domain reducer. B4 constructs the exact shell and holes in its structural frame; `_inferred_mesh` reconstructs world SI support, and `AnalysisRequest` projects that support onto the selected camera plane. Preserve the current branch's newer group evidence and field contracts.

**Tech Stack:** Jujutsu workspaces, the existing Pixi Python 3.12 environment, Shapely, IfcOpenShell, and only `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe` with its own Bonsai runtime.

**Spec:** The user's 2026-11-02 decision (selected wall enclosure projected onto the selected analysis plane), [distance input contract](../specs/2026-11-02-group-distance-module-design.md#3-查询身份和固定几何), and Spec008's implemented camera/domain behavior in `../order_analyzer_spec008`. This prerequisite does not freeze the distance design.

## Global Constraints

- Work only in `D:/PROJECTS/understandOtherPackage/order_analyzer_group_distance`, bookmark `codex/group-distance-module`; preserve source workspaces and their dirty files.
- Sole scene source: `D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, 408618044 bytes, SHA256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`. Recheck before running; preserve this file.
- Do not create simulated IFCs, furniture, layouts, occupancy or distance samples. Existing historical unit tests may verify compatibility; they do not count as this IFC's acceptance.
- Do not substitute a slab, furniture bounds, canvas extent or old B4 output for the selected wall enclosure. Do not require a newly authored IfcSpace.
- No second enclosure or projection algorithm. Preserve shell and holes, exact source identity, plane identity/revision, candidate identity and explicit confirmation. Unsupported tilt remains refused.
- The main branch lacks the Spec008 closure. Spec008's actual on-disk bytes contain implementation absent from its jj revision: record copied bytes and hashes, not an unverified revision claim.
- Existing group field/evidence, input inventory, shared-member handling and projection records must survive the integration. Do not wholesale copy older `field_core.py`, `group_self_description.py`, `neutral_scene_views.py` or architecture documents.
- Every new or modified project function has an English docstring; explain significant geometry and adapter handoffs. No new dependencies.
- Checkboxes describe demonstrated progress. Start with status/evidence, leave failed or unverified steps unchecked, and stop dependent distance execution until domain and plane inputs are confirmed.

## Checklist

- [x] P0: audit missing camera/domain inputs and locate implemented Spec008 reuse source. Two independent read-only audits, 2026-11-02; the approved IFC has no drawing camera or IfcSpace.
- [x] P1: recover the bounded closure, preserve newer field/group code, run affected compatibility tests and obtain independent code review. Evidence: `outputs/design/wall_domain_camera_prerequisite/integration-manifest.json` (40/40 target hashes), `.superpowers/sdd/2026-11-02-wall-domain-camera-prerequisite/task-1-review.md`, `task-1-rereview-final.md`, focused group/axis regression (51 passed), broader inventory/contract regression (220 passed, 1 skipped), and the focused camera/domain run (515 passed, 4 unrelated missing-`octa` import failures retained as environment evidence).
- [x] P2: run native camera creation/adoption and real-wall candidate preparation on the approved IFC; provide a plane preview and source/loaded-byte manifest. Real run `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/` contains 11/11 projected walls, five candidate outlines, per-candidate geometry/aperture/source-coverage diagnostics, and an unconfirmed run manifest; independent review found no blocking issue after the preview repair.
- [x] P3: explicitly select and confirm the intended wall enclosure; verify its shell/holes in the camera plane, freeze source/plane/domain identity and freshness. Evidence: `run_20261102T210601Z/s4_confirmed_manifest.json` and `s4_confirm_result.json` record accepted S4 confirmation with matching source, plane, request, and candidate identities.
- [ ] P4: return to distance readiness/library adaptation and write its separate implementation plan. No distance algorithm is implemented by P1–P3.

### Task 1: Recover Existing Camera and Wall-Domain Workflow

**Files:** Recover missing `adapters/blender_analysis_*`, `adapters/bonsai_analysis_plane.py`, `adapters/bonsai_live.py`, their actual request/result/preview dependencies, and `blender_addon/order_analyzer_ui/` from the inspected Spec008 working files. Merge only required changes into existing shared contracts. Record the bounded list, source SHA256, previous target SHA256 and disposition in `outputs/design/wall_domain_camera_prerequisite/integration-manifest.json`. Update `docs/software-architecture.md`, architecture memory and the main grouping checklist to distinguish task-workspace recovery from original-tree/deployment state.

**Interfaces:** Existing `CameraBinding`, `AnalysisPlane(identity, revision)`, `StructuralContext`, `evaluate_domain_request`, `domain_handoff`, `AnalysisRequest`, and addon operators retain their implemented contracts. The resulting domain mesh is WORLD SI support, never pre-transformed twice.

- [x] Step 1: inspect actual imports and the two audit reports; create and finalize the integration manifest with target hashes and retained audit pointers. Exclude obsolete bulk changes and unrelated Spec008 fixtures/artifacts.
- [x] Step 2: recover missing modules, merge shared dependencies and preserve current evidence/field/group APIs. Use existing Spec008 tests, without generating new synthetic geometry.
- [x] Step 3: run focused camera, capture, session, request and UI tests with the existing Pixi interpreter and run current group evidence/axis/input-inventory regressions. Evidence: focused camera/domain run 515 passed with 4 unrelated missing-`octa` import failures; focused group/axis/input regression 51 passed; broader inventory/contract regression 220 passed, 1 skipped. Exact commands and limits are in `integration-manifest.json` and the SDD ledger.
- [x] Step 4: verify exact-domain WORLD support → selected camera projection via the existing code path and tests; no manual transform was added.
- [x] Step 5: maintain the architecture/checklist, create a jj checkpoint in this workspace and obtain an independent spec and code-quality review before Task 2. Evidence: JJ checkpoint `uyxnsoll` (`checkpoint: wall-domain camera and real IFC candidate preview`), `task-1-review.md`, and `task-1-rereview-final.md`.

### Task 2: Prepare the Approved IFC for Explicit Domain Confirmation

**Files:** Reuse the recovered native adapters and service. Add at most one diagnostic runner under `scripts/design/live_domain/` if needed to supply this real IFC to those interfaces. Store a new run's logs, manifests and plane preview under `outputs/design/wall_domain_camera_prerequisite/`; never reuse another model's acceptance outputs.

**Interfaces:** Native `create_native_drawing` / `read_camera_binding` / `plane_from_camera`; canonical real IFC identity and wall geometry; `StructuralContext` / `evaluate_domain_request` with no confirmation action. Domain confirmation remains the existing explicit action carrying the exact candidate and frame identities.

- [x] Step 1: verify original source hash and real storeys/walls; check the permitted portable Blender and its Bonsai dependencies. Evidence: confirmed manifest records the pinned IFC hash, 1 storey, 11 walls, portable Blender 5.2.0 LTS, and no derived IFC saved.
- [x] Step 2: create/adopt a real native drawing camera using the existing adapter. Evidence: confirmed manifest records the native camera, SI pose, and `AnalysisPlane` revision 1.
- [x] Step 3: prepare wall enclosure candidates from actual IFC walls using the existing B4 service. Evidence: 11/11 projected walls and five candidate outlines are retained; S4 is selected.
- [x] Step 4: render actual wall geometry and each candidate shell/holes in the chosen plane. Evidence: confirmed manifest retains source refs, coverage, candidate geometry, and aperture diagnostics.
- [x] Step 5: ask for selection/confirmation only after the actual candidates are visible. Evidence: `s4_confirm_result.json` records accepted explicit confirmation for S4 at session revision 1 with matching identities.
- [x] Step 6: self-check and independent review the runner/output claims, checkpoint with jj, and leave precise next action in the main checklist. Evidence: confirmed run artifacts are retained; distance implementation remains separate.

## Verification and Completion

P1 may complete independently of native input acceptance. P2 requires this IFC's actual native run and preview, not Spec008's historical 655-test record. P3 requires explicit selection/confirmation, a current source-bound plane and a verified projected shell/holes. Keep P3 and dependent distance work open when any one is missing; do not hide missing input behind a fallback domain.

