# AnalysisDomain minimal handoff final validation

Date: 2026-10-08 (Europe/Berlin)

## Frozen baseline

The validation started on branch `codex/d6-analysis-domain-layout-handoff` at
HEAD `b2d6cccc3c6c7182f955398e03f40cb5ded951f0`. The frozen implementation,
view, regression test, implementation report, and design hashes matched the
requested identities before execution and after the owned validation session.
The independent-review report was not edited; its post-validation SHA-256 is
`dd1ea83125baf2566446795439392f5779851970182f9971e774727a3c1430b7`.

## Reserved full-suite execution

Exactly one configured command was run from the project root:

```text
pixi run pytest
```

Pytest collected 897 items and reached the existing IFC adapter area before
the 25-minute wall-time bound. It did not produce a final pytest summary or
reliable pass/skip counts. The exact owned session was stopped with Ctrl-C at
the bound; execution status is **INCOMPLETE**, not pass or failure. The full
captured output is [pytest.log](../../../outputs/design/analysis_domain_minimal_handoff_validation/run_001/pytest.log),
with timing and identity metadata in
[execution.json](../../../outputs/design/analysis_domain_minimal_handoff_validation/run_001/execution.json).

## Preservation checks

The branch, HEAD, and empty index were preserved. The frozen source, test,
design, implementation report, and independent-review report hashes were
unchanged across the validation. Only this validation report, its run artifacts,
and the final ledger entry are owned by this validation; pre-existing dirty and
untracked work remains intact.

The known whole-tree whitespace diagnostic remains nonblocking: prior
`git diff --check` reports exit 2 because of CRLF carriage returns on two
historical STOP-marker lines, including one prior repair append. No old text was
normalized and no new production or test code was changed.

## Limits

This result records bounded execution evidence only. It is not production,
public API/UI, live IFC, Blender, native adapter, formal AnalysisDomain, room,
free-space, topology, route, or walkability approval. Root acceptance remains
pending.
