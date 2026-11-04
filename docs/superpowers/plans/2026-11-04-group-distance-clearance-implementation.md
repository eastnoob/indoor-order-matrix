# Directional clearance group-distance implementation plan

Date: 2026-11-04  
Spec: `docs/superpowers/specs/2026-11-04-group-distance-clearance-design.md`  
Mode: `$stop-that-shit change`  
Workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge`  
Version writer: root only; workers must not snapshot, commit, rebase or push.

## Scope matrix

| Requirement | Code / artifact | Acceptance |
|---|---|---|
| Opt-in policy and identity | `features/group_distance.py`, input builders, retained JSON | `None` reproduces v4; constrained manifest is group-distance/3 |
| Exact polygon/domain clearance | `features/group_distance.py` | asymmetric thresholds, boundary and between-endpoint bottleneck tests |
| Heading state and turns | `features/group_distance.py` | deterministic shortest feasible path; no zero-cost turn |
| Access orientation | `features/group_distance.py` | source/target directional access tests |
| Support/status lineage | kernel + IFC validator | side/turn support refs and status precedence |
| Reader compatibility | runners, preview, Blender renderer | v1/v2 retained readers stay valid; v3 constrained output validates |
| Real S3 comparison | `outputs/design/group_distance_ifc/run_clearance_constrained_s3/` | 37 groups, 666 pairs, same ResultRef/input bytes, replay equal |
| User visual evidence | preview + native board outputs | same-region old/new route and narrowest L/R/total |

## Checklist

- [ ] Record this design/plan and update architecture memory with the new version boundary.
- [ ] Add an opt-in immutable `clearance_policy` handoff and fingerprint without changing the no-policy path.
- [ ] Implement exact polygon/domain ray clearance, full segment intervals, continuous heading turns, directional accesses and constrained source-batched Dijkstra.
- [ ] Add focused synthetic tests for thresholds, total bottleneck, between-endpoint obstacle, boundary, turns, access orientation, uncertainty and deterministic feasible selection.
- [ ] Extend runner validation and preview/native readers for constrained identity and compact clearance witnesses; preserve v1/v2 behavior.
- [ ] Run focused Pixi tests and verify the no-policy v4 replay/hash remains unchanged.
- [ ] Run the same S3 37-group/666-pair constrained job from the historical free-space ResultRef; save all output hashes and a comparison summary.
- [ ] Render the same real pair(s) with old/new routes, corridor bands and narrowest cross-section; record user visual review as pending.
- [ ] Obtain independent specification/code review, fix load-bearing findings, rerun affected checks.
- [ ] Freeze hashes, update the evidence ledger, and create one local jj checkpoint containing only task-owned paths.

## Agent briefs

### Implementer

Outcome: implement the smallest complete constrained branch in the files above.

Dependencies: existing v4 code and authenticated retained S3 bundle.

Must preserve: v1/v2 readers, no-policy v4 byte behavior, exact domain coverage, physical edge arithmetic, deterministic tie ordering, all 666 pair scope.

Expected evidence: focused tests, constrained validator tests, same-bundle replay, changed-file list and hashes.

Visual: required only after numerical route package exists; reuse v4 board inputs.

Stopping condition: no unresolved implementation/test failure within the listed scope; do not commit.

### Independent verifier

Run from the frozen candidate, not the implementer's report. Verify focused tests, no-policy v4 replay/hash, constrained identity/status/witness invariants, real S3 output pair scope and replay, and artifact hashes. Do not edit or commit.

Visual: inspect the generated old/new route board and confirm it uses the same S3 input/result references; user acceptance remains pending.

## Rulings

- Ruling: use retained physical projected polygons plus exact domain boundary — cached cell unions cannot answer directional first-hit distances.
- Ruling: evaluate segment/turn intervals over the full geometry — endpoint/midpoint-only checks can miss an interior bottleneck.
- Ruling: keep constrained routing opt-in — historical v1/v2/v4 consumers must remain readable and reproducible.
- Ruling: keep endpoint offsets metric-only — treating centroid→proxy as corridor evidence would overstate walkability.
