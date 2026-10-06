# D6 AnalysisDomain/UI handoff design repair v1

- Repair basis: review of `d8f68c79f608fd386b7bdf9d9a3bfa460f0490ae`
- Scope: bounded design evidence only; no production implementation
- Stop marker: **STOP FOR ANALYSISDOMAIN UI HANDOFF DESIGN REVIEW**

The repair freezes `draw_boundary` as a geometry-creation event. It records a
user-authored candidate as provisional and does not set `user_confirmed`,
`accepted`, or `lifecycle=confirmed`. Independent `confirm` and `assign` events
control promotion. The repaired fixture includes an independently confirmed
hand-drawn provisional and confirmed cases, an automatically generated
candidate promoted only after an explicit confirmation, and an
authored/automatic unresolved conflict where both candidates have explicit
actions but promotion remains blocked.

The verifier now asserts lifecycle, assignment, confirmation, acceptance,
evidence state, geometry state, event IDs, lineage, conflict IDs, and complete
non-visual hover projections for every case. The repaired package has 14 cases.
The original `artifacts/run_001/` and `artifacts/run_002/` remain unchanged;
repair outputs are under `artifacts/repair_v1/`.

Commands and outcomes:

```text
pixi run python -B -m py_compile scripts/design/analysis_domain_ui/run_probe.py scripts/design/analysis_domain_ui/verify_probe.py  # exit 0
pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/repair_v1/run_001  # exit 0
pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/repair_v1/run_002  # exit 0
pixi run python -B scripts/design/analysis_domain_ui/verify_probe.py --primary scripts/design/analysis_domain_ui/artifacts/repair_v1/run_001 --reproduction scripts/design/analysis_domain_ui/artifacts/repair_v1/run_002 --baseline-status C:/Users/tianf/AppData/Local/Temp/d6_ui_baseline_git.json --report scripts/design/analysis_domain_ui/artifacts/repair_v1/run_001/verification_report.json --scope-audit scripts/design/analysis_domain_ui/artifacts/repair_v1/run_001/scope_audit.json --manifest scripts/design/analysis_domain_ui/artifacts/repair_v1/run_001/artifact_manifest.json  # exit 0
git diff --check  # exit 0
```

The verifier reports byte-identical primary/reproduction JSON and SVG,
well-formed SVG XML, 14 truth cases, preserved baseline untracked evidence,
and `real_ifc_status: not_verified`. No full pytest, Blender, IFC adapter, or
production API path was run.

STOP FOR ANALYSISDOMAIN UI HANDOFF DESIGN REVIEW
