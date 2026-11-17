# Checkpoint semantic validation prerequisite

Date: 2026-11-16. Parent scope: Plan A of the package-owned parameter and
model-side cache design. This is a required repair before Plan B, arising from
the final scoped review's remaining Important finding. A was not yet accepted when this repair was dispatched; the final outcome is recorded below.

## Binding requirement

A matching input fingerprint and structurally valid JSON cannot authorize a
saved route to suppress search. Checkpoint reuse must independently establish
that its route and exact evidence describe the current graph, group accesses,
geometry and policy. Preserve rejected original bytes before replacement.

## One bounded task

- Allowed production file: `features/group_distance_repair.py`.
- Allowed test file: `test/test_group_distance_route_repair.py`.
- Keep `_checkpoint_matches` as the structural gate; add the smallest contextual
  check at the actual `global_repair_result` read/completion boundary.
- Resolve route cells and moves against the current accepted graph, including
  diagonal support. Validate state headings, actual group access membership,
  endpoints and offsets. Recompose distance from current graph weights and
  independently selected current accesses.
- Recheck only the saved route with the existing exact geometry helpers.
  Validate its saved pass/failure and witnesses against that fresh result.
  A valid checkpoint must still suppress the expensive source search.
- Reject validly shaped but false cell, edge, heading, access, distance and
  witness records. Retain rejected bytes; no output/schema/formula change,
  fixture edits, new search, or new persistence mechanism.

## Acceptance and recovery

1. A fresh implementer authors tests and the fix; root applies tests first and
   records behavioral failure, then applies the production fix.
2. Use actual small graph/access fixtures. Repair the old empty-graph mock so
   the valid round trip describes a possible route. Keep its invocation-count
   assertions: first call searches, identical second call does not, changed
   policy searches, and restored policy reuses the matching version.
3. Run all route-repair tests plus clearance and package regressions. Every
   mandatory node must execute without skip/xfail/deselection. Freeze the final
   complete A candidate and repeat A's full required acceptance set.
4. A different reviewer gives explicit specification and quality verdicts over
   this repair. Root verifies tested bytes, docstrings and diff before creating
   a nonempty local checkpoint with explicit filesets.
5. Only the final A implementation and a subsequent accurate handoff may
   advance the A accepted bookmark. B still starts from that full handoff ID.

Root remains sole jj writer in `parameter-cache-a-implementation`. Preserve the
prior unaccepted candidate, test logs and failed reviews. No owner integration,
push, cache deletion, workspace cleanup or repository-wide history restoration.
Visuals are omitted: graph/access/numerical comparisons and sentinels answer the
correctness questions directly.

## Actual acceptance

Final implementation: 92ff7d521415c95d505c2e35eca60781e09b7f96. Independent SPEC PASS / QUALITY
APPROVED; focused 155/155 and complete A 533/533 pass. All 315 frozen
file hashes matched; restored policy independently reuses the original version
with exactly two searches across four requests. Exact evidence and limitations
are recorded in ../handoffs/2026-11-15-plan-a-accepted.md.
