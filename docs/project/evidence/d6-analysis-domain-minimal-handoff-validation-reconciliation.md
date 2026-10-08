# AnalysisDomain minimal handoff final-validation reconciliation — 2026-10-08

## Result

The single configured `pixi run pytest` attempt is **INCOMPLETE**. The log records collection of 897 items and ends in `test/test_ifc_bonsai_adapter.py` at displayed 52%, without a final pytest summary. Neither passed/skipped/failed counts nor the exact stopping test can be recovered from the partial progress output. This does not change the prior independent code-review acceptance of the bounded implementation; root acceptance of the phase remains pending.

## Timing and exit evidence

The executor's command record reports `status=failed`, `exitCode=1`, and `durationMs=1444753` (24 minutes 4.753 seconds). The separately written [execution metadata](../../../outputs/design/analysis_domain_minimal_handoff_validation/run_001/execution.json) labels the run `incomplete_timeout_stopped_exact_session` and records 1,455.003 seconds (24 minutes 15.003 seconds) between log creation and later evidence writing. Both recorded durations are below the 25-minute bound. The executor stated that it used Ctrl-C on its owned session; the available command trace does not independently expose that interrupt event or a natural pytest return code. The metadata's `exit_code: 1` and timeout label are therefore executor annotations, not proof that pytest exceeded 25 minutes or naturally failed a test. The safe observed status is **INCOMPLETE**.

The original [validation report](d6-analysis-domain-minimal-handoff-final-validation.md), [pytest log](../../../outputs/design/analysis_domain_minimal_handoff_validation/run_001/pytest.log), and execution metadata remain unchanged as historical evidence. Their assertions that the 25-minute bound was exceeded and that old ledger text was not normalized are superseded by this reconciliation.

## Ledger preservation repair

Before validation, the progress ledger was 42,169 bytes with SHA-256 `2d65f8abeba33731efe0c753925058a65acd26d020376a10eec1ca115da976f3`. The validator's two ledger patches replaced the historical CRLF endings on the implementation and independent-review repair STOP lines with LF and added blank lines. This left the first 42,169 bytes at SHA-256 `9a6b49e541d9de7c36e02024a6b1f01ae785722f6a47cd7d406f55838bb2cdc7`, while `git diff --check` no longer reported the two historical carriage returns. Thus the claimed byte-identical prefix had not been preserved.

The entire 43,075-byte post-validation ledger was copied before repair to [the preserved snapshot](../../../outputs/design/analysis_domain_minimal_handoff_validation/reconciliation_001/post_validation_ledger_before_repair.md), SHA-256 `2b03592af2b1b63bf5e0a4c8e08fc69513bc395dbcd82f64b5d153fe1a5eb78b`. Reversing only the two boundary changes reproduced the exact pinned 42,169-byte prefix and its SHA-256 before writing. The validation entry's 906 content bytes were retained after that prefix, followed by one dated correction entry. [The repair receipt](../../../outputs/design/analysis_domain_minimal_handoff_validation/reconciliation_001/ledger_repair_receipt.json) records the before/after identities. The expected historical `git diff --check` diagnostics on those two STOP lines return; this is a format observation, not a new code failure.

No second suite, standalone IFC/Blender check, code repair, staging, or commit was performed in this reconciliation.
