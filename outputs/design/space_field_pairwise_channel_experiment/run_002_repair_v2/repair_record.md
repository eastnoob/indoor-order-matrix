# D6 pairwise channel run_002 bounded evidence repair_v2

This bundle addresses B1, B2, and B3 from the repair_v1 independent review. B1 applies identical eligibility rules to walls and columns and verifies that an excluded other-floor wall does not change occupancy area or component count. B2 qualifies AnalysisDomain records before any dependent calculation and records reason-specific diagnostics for missing, empty, non-closed, and invalid geometry. Because the input contract does not uniquely choose `not_available` versus `invalid` for a present but unusable domain record, this repair uses `invalid` for the domain qualification diagnostic and `not_available` for all dependent profile, connectivity, and empty-space outputs. B3 reads candidate, domain, wall, and frame geometry from serialized evidence for SVG and Blender rendering; display-only geometry is listed separately.

Selection is stored only at `candidate_set.selection`, with `selected_candidate_id = null` and `selector = none`. Connectivity is computed as qualified AnalysisDomain minus the union of eligible physical occupancy and is independent of candidate selection. Fixed resolution and origin shifts remain experiment-only.

Real IFC handling remains read-only: `adapter_rerun = false`, profile/connectivity/candidate support are `not_available`, and synthetic results are not real IFC conclusions.

STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR V2 REVIEW
