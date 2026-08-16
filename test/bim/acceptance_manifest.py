"""Stable contract for the generated BIM acceptance fixture."""

from collections.abc import Mapping


_REQUIRED_OUTPUTS = {
    "test/output/blender_demo_description.json",
    "test/output/blender_demo_room_analysis_model.json",
}

_ALLOWED_INPUT_MODES = {"ifc", "blender_geometry", "hybrid", "svg"}


ACCEPTANCE_MANIFEST = {
    "fixture_ids": [
        "room",
        "floor",
        "wall_north",
        "table_group_aligned",
        "table_group_oblique",
        "sofa",
        "low_cabinet",
        "glass_partition",
        "carpet",
        "grid_main",
        "chair_affordance_aligned",
        "chair_affordance_oblique",
    ],
    "required_outputs": [
        "test/output/blender_demo_description.json",
        "test/output/blender_demo_room_analysis_model.json",
    ],
    "allowed_input_modes": ["ifc", "blender_geometry", "hybrid", "svg"],
    "regeneration": {
        "generator_path": "test/blender/generate_bim_acceptance_scene.py",
        "entrypoint": "generate_acceptance_scene",
        "manual_edits": False,
    },
}


def validate_acceptance_manifest(manifest: Mapping[str, object]) -> None:
    """Validate identifiers, required artifacts, and supported source modes."""
    fixture_ids = list(manifest.get("fixture_ids", []))
    required_outputs = set(manifest.get("required_outputs", []))
    input_modes = set(manifest.get("allowed_input_modes", []))

    # Ambiguous ids would make later generated geometry impossible to address
    # deterministically across IFC, Blender, and serialized output artifacts.
    duplicate_ids = sorted(
        fixture_id for fixture_id in set(fixture_ids) if fixture_ids.count(fixture_id) > 1
    )
    if duplicate_ids:
        raise ValueError(f"duplicate fixture id: {duplicate_ids[0]}")

    missing_outputs = sorted(_REQUIRED_OUTPUTS - required_outputs)
    if missing_outputs:
        raise ValueError(f"missing required output: {missing_outputs[0]}")

    # Adapter modes are an explicit handoff boundary. Unknown modes must not
    # silently acquire source semantics from viewport or object names.
    unsupported_modes = sorted(input_modes - _ALLOWED_INPUT_MODES)
    if unsupported_modes:
        raise ValueError(f"unsupported input mode: {unsupported_modes[0]}")

    missing_modes = sorted(_ALLOWED_INPUT_MODES - input_modes)
    if missing_modes:
        raise ValueError(f"missing supported input mode: {missing_modes[0]}")
