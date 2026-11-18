# AnalysisContext ancestor verification — 2026-11-18

This record covers the documentation and implementation evidence available in
the `analysis-context-ancestor-20261118` worktree. It records the complete
suite collection limitation, final independent reviews, and the final local
jj checkpoint. No remote push or merge is claimed.

## Contract verified from the current source

- `AnalysisContext` has one required `analysis_plane`; it is the scene default.
- Each package call resolves a frozen `PackageAnalysisContext` snapshot.
- An explicit `package_planes` set replaces the scene default and is never
  automatically merged with it.
- More than one plane requires package capability and explicit call permission.
- Empty, duplicate, malformed, conflicting, and unauthorized selections fail
  before producer, processor, storage, or cache work.
- A package may ignore the snapshot. In that case selection does not trigger
  projection, grid, or model extraction and does not alter output/cache identity
  or bytes.
- A plane-using package owns the dependency declaration: identity and revision
  must enter its output, contract, parameter snapshot, or explicit dependency
  before cache lookup. The generic cache layer does not guess plane use.
- Free-space, group-axis, group-distance, output-port, and lifecycle callers
  resolve and forward the snapshot through nested package calls. The unique
  complete source-query inference path remains migration compatibility only.
- UI/native settings, `.blend` restart, and native lifecycle integration remain
  deferred.

## Fresh focused test evidence

Command:

```text
pixi run pytest test/test_package_analysis_context.py -q -k "not imports_under_both_namespaces_without_heavy_engines"
```

Result:

```text
44 passed, 1 deselected in 1.10s
```

The unfiltered command was also run:

```text
pixi run pytest test/test_package_analysis_context.py -q
```

It produced `44 passed, 1 failed`. The only failure was
`test_context_contract_imports_under_both_namespaces_without_heavy_engines`:
its subprocess inserts the worktree parent (`.../.worktrees`) and then cannot
import `order_analyzer`. This is recorded as a scoped import-path/environment
failure. It is not evidence for or against the package-context contract, and it
must not be reported as a full-suite result.

The complete requested suite was also run:

```text
pixi run pytest test/ -q
```

It stopped during collection with 48 errors. The errors are the existing
nested-worktree import shape (`..features` relative imports beyond the
top-level package and `octa` not present on `sys.path`), so no implementation
assertion ran in those modules. The focused package-context boundary suite
passed independently:

```text
pixi run pytest test/test_package_analysis_context.py test/test_evidence_package_output.py test/test_evidence_package_processing.py test/test_output_port_cache.py -q -k "not context_contract_imports_under_both_namespaces_without_heavy_engines"
```

```text
258 passed, 1 deselected in 11.33s
```

## Static caller audit

Command:

```text
rg -n "\.evaluate\(|\.process_output\(" features adapters blender_addon --glob "*.py"
```

Fresh result: 21 matches. The package-relevant calls in free-space,
group-axis, group-distance, output-port, and lifecycle paths pass the resolved
`analysis_context`; unrelated field, affordance, and geometry evaluators use a
different API and are not evidence-package entrypoints.

## Final review gates

- Final Grill-Me review: PASS. It confirmed resolver precedence, explicit
  replacement, multi-plane admission, early invalid-input ordering, caller
  propagation, ignored-plane cache identity, and package-owned plane
  dependencies.
- Final Superpowers review: SPEC PASS / QUALITY PASS. It confirmed the linear
  jj checkpoint chain and found only stale pending ledger text, which was
  corrected before the final checkpoint.
- Final compile check: `pixi run python -m compileall -q features adapters scripts/design/group_level test/test_package_analysis_context.py` passed.
- Final local jj checkpoint: `documentation-and-verification` (created after
  this record was updated).

## Known limits

- No UI interaction, native settings persistence, `.blend` restart, or full
  physical-model recomputation was performed for this change.
