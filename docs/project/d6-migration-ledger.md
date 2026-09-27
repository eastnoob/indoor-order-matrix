# D6 clean-room migration ledger

This ledger records current implementation candidates against the clean-room
layout descriptor contract. `unknown` means the new contract has not yet
tested the behavior; it is not an approval to migrate the component.

| candidate | current_location | classification | contract_reason | tests | replacement_or_stop | status |
|---|---|---|---|---|---|---|
| placement/unit conversion | `adapters/ifc_bonsai.py` (`_native_world_transform`, unit helpers); `adapters/svg_scene.py` (SVG affine/unit handling) | unknown | Existing conversions are adapter-specific and have not passed the canonical frame and provenance contract. | `test/test_ifc_bonsai_adapter.py`; `test/test_svg_scene_adapter.py` (reference evidence only) | Re-evaluate behind canonical frame normalization in Task 6/7. | open |
| geometry extraction | `adapters/ifc_bonsai.py`; `adapters/svg_scene.py`; `features/geometry_substitutes.py` | unknown | Source geometry, projection status, and provenance have not been compared with clean-room records. | Existing adapter and geometry tests are reference evidence only. | Re-evaluate after canonical projection tests and adapters. | open |
| MassPatch construction | `features/mass_patch_generation.py`; `features/mass_patch_collection.py`; `features/mass_patch_cuboid_cover.py` | unknown | MassPatch behavior is outside the first descriptor slice until canonical geometry equivalence is demonstrated. | `test/test_mass_patch_*.py` (reference evidence only) | Stop for the first slice unless a later migration comparison proves a narrow need. | open |
| authored group extraction | `adapters/ifc_bonsai.py` (`_native_group_records`); `adapters/svg_scene.py` (`_authored_groups`) | unknown | Group membership must remain explicit source fact data and has not passed the canonical record contract. | Existing IFC/SVG adapter tests are reference evidence only. | Re-evaluate in the adapter checkpoints. | open |
| trend estimation | `features/column_grid.py`; `features/position_grammar.py`; preview trend helpers | unknown | Existing trend outputs are derived legacy behavior; the clean-room estimator and status vocabulary are not selected. | `test/test_column_grid_trend_regression.py` (reference evidence only) | Stop until a later descriptor decision selects and tests an estimator. | open |
| evaluator rows | `features/scene_evaluator.py`; `features/affordance/evaluator.py`; `features/room_analysis_model.py` | unknown | Evaluator payloads are not normative descriptor results and may encode unsupported semantics. | Existing evaluator regressions (reference evidence only) | Keep as reference; compare only in the migration checkpoint. | open |
| SVG parsing | `adapters/svg_scene.py`; `features/scene_loader.py` | unknown | SVG IDs and element names cannot define canonical semantics; translation has not been tested. | `test/test_svg_scene_adapter.py`; SVG fixtures (reference evidence only) | Wrap only behind the canonical SVG adapter if contract tests pass. | open |
| IFC adapter | `adapters/ifc_bonsai.py` | unknown | Existing adapter includes broader facts and optional runtime paths; canonical IFC obligations are not yet proven. | `test/test_ifc_bonsai_adapter.py`; IFC fixtures (reference evidence only) | Add a separate canonical bridge in Task 6; do not repair rich IFC here. | open |
| preview | `adapters/blender_preview.py`; `features/affordance/visualization.py` | reference_only | Preview output is presentation behavior and is outside the first canonical descriptor contract. | `test/test_blender_preview.py` (reference evidence only) | Stop for the first slice. | open |
| tests | `test/` and `skills/*/tests/` | reference_only | Existing tests document current behavior but do not establish clean-room semantics. | Existing suite; targeted tests added per checkpoint. | Add independent canonical tests without changing legacy tests. | open |

The ledger records computable contract evidence only. It makes no claim about
psychological or perceptual validity.
