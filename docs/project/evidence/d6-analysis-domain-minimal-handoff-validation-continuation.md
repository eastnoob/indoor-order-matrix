# AnalysisDomain minimal handoff validation continuation — 2026-10-08

## Outcome

The configured 897-node suite has **complete composed coverage** on the frozen implementation: 884 passed and 13 skipped, with no remaining nodes. This is the combination of 430 unambiguous passed nodes from the interrupted original run and one controlled continuation of the other 467 collected nodes. The original `pixi run pytest` remains **INCOMPLETE**; it did not produce one uninterrupted full-suite PASS.

## Coverage split

One collect-only command, `pixi run pytest --collect-only -q`, returned 897 nodes in 43 modules. The original [partial log](../../../outputs/design/analysis_domain_minimal_handoff_validation/run_001/pytest.log) contains only pass symbols through the first 17 fully completed modules (430 nodes). Its next module, `test/test_ifc_bonsai_adapter.py`, shows 40 pass symbols among 66 collected nodes; the active node and remaining results were uncertain. The continuation reran all 66 nodes in that module plus every later module (401 nodes), for 467 selected nodes. The first 40 IFC results were duplicate coverage and are counted only from the continuation in the composed totals.

The one continuation command was `pixi run pytest -vv --durations=20` with the 26 module paths listed in [coverage.json](../../../outputs/design/analysis_domain_minimal_handoff_validation/continuation_001/coverage.json). The [verbose log](../../../outputs/design/analysis_domain_minimal_handoff_validation/continuation_001/pytest.log) gives an outcome for every selected node in collected order: 454 passed, 13 skipped, no failure, in pytest's 802.39 seconds. The slow real IFC adapter node passed in 693.32 seconds. The owned Pixi process exited 0; [execution.json](../../../outputs/design/analysis_domain_minimal_handoff_validation/continuation_001/execution.json) records PID 73844, UTC 10:27:38.381–10:41:06.984 and monotonic elapsed 808.594 seconds. Its source is the subprocess launcher, rather than a later wall-clock estimate. The 13 skips remain skips; they occur in the optional IFC workflow test modules.

The [coverage record](../../../outputs/design/analysis_domain_minimal_handoff_validation/continuation_001/coverage.json) lists the 17 original completed modules, 26 continued modules, exact collection and per-node outcome hashes, all skipped node identities, duplicate treatment and final 897-node reconciliation. The collect-only output is retained in [collect.log](../../../outputs/design/analysis_domain_minimal_handoff_validation/continuation_001/collect.log). Collection was not a test run.

## Preservation and limits

The frozen implementation, view, regression test, implementation report, design and independent review each retain their pinned SHA-256 identity. Branch `codex/d6-analysis-domain-layout-handoff`, HEAD `b2d6cccc3c6c7182f955398e03f40cb5ded951f0` and the empty index remain unchanged. The recovered 44,275-byte progress ledger was retained byte-for-byte before the appended continuation entry; its historical CRLF `git diff --check` diagnostics remain. Original run_001 evidence, its reconciliation artifacts, earlier reviews, source IFC and Blender files were not changed. No second full-suite run, separate native IFC/Blender probe, code repair, staging or commit occurred.

Root can accept **composed configured-suite coverage** for the bounded private handoff, alongside the independent implementation review. Existing adapter tests do not establish that the new handoff activates real S1 or works in a live Blender session; the private scope and root acceptance decision remain separate.
