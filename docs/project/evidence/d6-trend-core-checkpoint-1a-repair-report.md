# D6 Trend Core Checkpoint 1A Repair Report

Status: **ready for review; IFC adapter integration is explicitly deferred**

## Accepted evidence

- `resolve_function_substitute` now delegates semantic matching to the shared
  `d6-trend-substitute-registry/v1` contract.
- A candidate is accepted only when its binding and target substitute carry the
  registry's `representation_identifier`, and the target SourceObject carries
  `provenance.representation_identifier == "Analysis"`.
- Missing or unresolved bindings and substitutes propagate as
  `not_available`; `invalid` is reserved for malformed or invalid geometry.
- Canonical A (`member_frame`, `member_axis`), C (`overall_group_axis`), and D
  (`layout_axis`) consume only resolved Analysis substitute geometry. Body
  geometry remains compatibility/audit evidence and cannot alter these values.

## Fixture evidence

`test/test_trend_core_checkpoint_1a.py` includes Body and Analysis meshes with
different positions and orientations. Replacing the Body meshes leaves all
canonical A/C/D descriptors unchanged. The fixture also covers target Body
provenance rejection, missing/unresolved substitutes, ambiguous candidates,
partial propagation, isotropic undefined directions, translation/rotation,
tessellation invariance, and strict JSON serialization.

## Verification

- `pixi run pytest test/test_trend_core_checkpoint_1a.py -q`: 12 passed
- `pixi run pytest test/test_group_self_description.py -q`: 34 passed
- `pixi run pytest scripts/design/group_level/test_trend_substitute_registry.py -q`: 5 passed
- `pixi run pytest -q`: 847 passed, 13 skipped
- `git diff --check`: passed

## Scope audit

The repair changes only the shared contract loader, substitute resolver,
group trend calculation, focused tests, registry compatibility wrapper, and
this checkpoint evidence. No IFC adapter, NeutralSceneV2 definition, public
room model, automatic space, selector, Bayesian/ML code, source IFC, Blender
file, or dependency was changed. Existing unrelated untracked work remains
untouched.

## Limitation and next stage

The IFC adapter still does not emit the typed `OM_FunctionSubstitutes` binding;
real IFC scenes therefore remain `not_available` until Checkpoint 1B. This
checkpoint does not begin that integration.

STOP FOR TREND CORE CHECKPOINT 1A REVIEW
