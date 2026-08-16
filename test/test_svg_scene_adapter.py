"""Contract tests for the planar SVG Neutral Scene v2 adapter."""

import ast
from importlib import import_module
import json
from pathlib import Path
import sys

import pytest

from ..features.scene_contract import NeutralSceneV2
from ..features.scene_loader import load_structured_svg_scene


SVG_FIXTURES = (
    Path("test/SVG_baseline.svg"),
    Path("test/SVG_oblique.svg"),
    Path("test/SVG_chaoticsvg.svg"),
)
FORBIDDEN_WEIGHT_KEYS = {
    "weights",
    "walk-block",
    "walk_block",
    "see-block",
    "see_block",
    "grouping-strength",
    "grouping_strength",
    "boundary-strength",
    "boundary_strength",
}


def test_svg_adapter_exposes_public_loader() -> None:
    """The adapters package should expose the supported SVG loader API."""
    adapters = import_module("order_analyzer.adapters")

    assert callable(adapters.load_svg_neutral_scene)


def test_svg_adapter_supports_existing_top_level_import_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter should remain usable when the repository root is on sys.path."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    sys.modules.pop("adapters", None)

    adapters = import_module("adapters")

    assert callable(adapters.load_svg_neutral_scene)


def _load(path: Path) -> NeutralSceneV2:
    """Load one fixture through the public adapter with explicit units."""
    from ..adapters import load_svg_neutral_scene

    return load_svg_neutral_scene(path, source_length_unit="mm")


def _all_keys(value: object) -> set[str]:
    """Collect nested JSON object keys for forbidden-weight assertions."""
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


@pytest.mark.parametrize("fixture", SVG_FIXTURES)
def test_real_svg_fixtures_validate_and_round_trip_without_fabricated_facts(
    fixture: Path,
) -> None:
    """Real planar fixtures should become strict, source-ordered v2 scenes."""
    legacy = load_structured_svg_scene(fixture)
    scene = _load(fixture)
    payload = scene.to_dict()

    assert NeutralSceneV2.from_dict(json.loads(json.dumps(payload))).to_dict() == payload
    assert scene.context.input_mode == "svg"
    assert scene.context.source_schema == "SVG"
    assert scene.context.source_length_unit == "mm"
    assert scene.context.analysis_length_unit == "m"
    assert scene.context.capability_flags == {
        "planar_geometry": True,
        "height_queries": False,
        "volume_queries": False,
        "closed_solid_geometry": False,
        "optical_queries": False,
        "vertical_queries": False,
    }
    assert scene.analysis_domain is None
    assert scene.authored_affordances == ()
    assert not (FORBIDDEN_WEIGHT_KEYS & _all_keys(payload))

    legacy_ids = [item["id"] for item in legacy["objects"]]
    mapped_object_ids = [
        item.id for item in scene.source_objects if item.provenance["legacy_bucket"] == "objects"
    ]
    assert mapped_object_ids == legacy_ids
    assert len(mapped_object_ids) == len(set(mapped_object_ids))


def test_existing_structured_svg_loader_behavior_remains_unchanged() -> None:
    """The v1 compatibility loader should retain representative legacy facts."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    assert len(scene["objects"]) == 44
    assert len(scene["columns"]) == 9
    assert len(scene["column_axes"]) == 8
    assert scene["objects"][0]["id"] == "north_table_r1_c1"
    assert scene["objects"][0]["furniture_group"] == "north_table_group_r1_c1"
    assert scene["boundaries"][0]["id"] == "room_boundary"
    assert scene["boundaries"][0]["weights"] == {
        "walk_block": 0.0,
        "see_block": 0.0,
        "grouping_strength": 0.0,
    }
    assert set(scene) == {
        "source",
        "size",
        "objects",
        "boundaries",
        "entries",
        "paths",
        "columns",
        "column_axes",
        "regions",
        "uncertainties",
    }


def test_source_objects_preserve_global_svg_element_order(tmp_path: Path) -> None:
    """Neutral source objects should retain order across legacy loader buckets."""
    svg = tmp_path / "source_order.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="wall-first" data-role="boundary" x="0" y="0" width="100" height="2"/>
        <rect id="chair-second" data-role="chair" x="10" y="10" width="10" height="10"/>
        <line id="door-third" data-role="opening" x1="40" y1="0" x2="60" y2="0"/>
        <rect id="column-fourth" data-role="column" x="80" y="80" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.id for item in scene.source_objects] == [
        "wall-first",
        "chair-second",
        "door-third",
        "column-fourth",
    ]


def test_explicit_column_axes_are_preserved_without_column_axis_inference(
    tmp_path: Path,
) -> None:
    """Only authored axis records may enter the Neutral Scene grid scaffold."""
    svg = tmp_path / "axes.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80">
        <rect id="column-only" data-role="column" x="5" y="5" width="10" height="10"/>
        <line id="axis-a" data-role="column_axis" data-grid="grid-a"
              data-branch="u" data-list="A" x1="0" y1="40" x2="100" y2="40"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [axis.id for axis in scene.authored_grid_axes] == ["axis-a"]
    assert scene.authored_grid_axes[0].branch_identifier == "u"
    assert scene.authored_grid_axes[0].list_identifier == "A"
    assert [(grid.id, grid.axis_refs) for grid in scene.authored_grids] == [
        ("grid-a", ("axis-a",))
    ]


def test_columns_without_explicit_axes_do_not_create_a_grid(tmp_path: Path) -> None:
    """Column geometry alone must not be promoted to authored grid facts."""
    svg = tmp_path / "columns.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <rect id="column-a" data-role="column" x="2" y="2" width="4" height="4"/>
        <rect id="column-b" data-role="column" x="12" y="12" width="4" height="4"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.authored_grid_axes == ()
    assert scene.authored_grids == ()


def test_explicit_furniture_groups_are_deduplicated_in_source_order(
    tmp_path: Path,
) -> None:
    """Authored furniture memberships should be stable and free of duplicate refs."""
    svg = tmp_path / "groups.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">
        <g data-role="chair" data-furniture-group="dining-a">
          <rect id="chair-b" x="20" y="5" width="10" height="10"/>
          <rect id="chair-a" x="5" y="5" width="10" height="10"/>
        </g>
        <rect id="legacy-region-only" data-role="table" data-region="legacy-zone"
              x="50" y="5" width="20" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [(group.id, group.member_refs) for group in scene.authored_groups] == [
        ("dining-a", ("chair-b", "chair-a"))
    ]


def test_explicit_affordance_opening_and_domain_are_mapped(tmp_path: Path) -> None:
    """Explicit functional geometry should retain source and host provenance."""
    svg = tmp_path / "explicit_facts.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
        <rect id="chair-1" data-role="chair" data-material-ref="mat-chair"
              data-surface-ref="seat-finish" x="20" y="20" width="20" height="20"/>
        <rect id="chair-pullback" data-role="affordance" data-purpose="pullback"
              data-source-furniture-refs="chair-1" data-z-min="0" data-z-max="900"
              x="10" y="10" width="40" height="50"/>
        <line id="door-1" data-role="opening" data-host-refs="wall-1"
              data-opening-kind="door" x1="80" y1="0" x2="100" y2="0"/>
        <rect id="wall-1" data-role="boundary" data-boundary-strength="0.8"
              x="0" y="0" width="200" height="2"/>
        <polygon id="study-domain" data-role="analysis_domain"
              points="0,0 200,0 200,100 0,100"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    by_id = {item.id: item for item in scene.source_objects}

    assert scene.analysis_domain is not None
    assert scene.analysis_domain.source_id == "study-domain"
    assert scene.analysis_domain.selection_method == "explicit_svg_element"
    assert len(scene.authored_affordances) == 1
    assert scene.authored_affordances[0].purpose == "pullback"
    assert scene.authored_affordances[0].source_furniture_refs == ("chair-1",)
    assert scene.authored_affordances[0].vertical_extent == (0.0, 0.9)
    assert len(scene.openings) == 1
    assert scene.openings[0].host_refs == ("wall-1",)
    assert scene.openings[0].opening_kind == "door"
    assert by_id["chair-1"].material_refs == ("mat-chair",)
    assert by_id["chair-1"].surface_refs == ("seat-finish",)
    assert by_id["wall-1"].opening_refs == ("door-1",)
    assert not (FORBIDDEN_WEIGHT_KEYS & _all_keys(scene.to_dict()))


def test_furniture_does_not_invent_affordance_or_analysis_domain(tmp_path: Path) -> None:
    """Furniture and room-boundary names alone should not fabricate authored facts."""
    svg = tmp_path / "plain_furniture.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="chair-affordance-looking-name" data-role="chair"
              x="20" y="20" width="20" height="20"/>
        <rect id="room_boundary" data-role="boundary" x="0" y="0" width="100" height="100"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.authored_affordances == ()
    assert scene.analysis_domain is None


def test_planar_affordance_without_height_is_preserved_as_uncertain(
    tmp_path: Path,
) -> None:
    """Explicit planar affordance geometry should not require fabricated height."""
    svg = tmp_path / "planar_affordance.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="chair-1" data-role="chair" x="10" y="10" width="10" height="10"/>
        <rect id="chair-use" data-role="affordance" data-purpose="pullback"
              data-source-furniture-refs="chair-1" x="5" y="5" width="20" height="30"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert len(scene.authored_affordances) == 1
    assert scene.authored_affordances[0].vertical_extent == (0.0, 0.0)
    assert [item.code for item in scene.authored_affordances[0].uncertainties] == [
        "vertical_extent_unavailable"
    ]


def test_planar_meshes_use_points_then_record_rect_fallback(tmp_path: Path) -> None:
    """Explicit polygon points should win while point-poor shapes record bbox fallback."""
    svg = tmp_path / "geometry.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <polygon id="poly" data-role="table" points="0,0 30,0 20,20 0,10"/>
        <circle id="circle" data-role="table" cx="60" cy="20" r="10"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    geometry = {item.source_representation_id: item for item in scene.geometries}

    assert len(geometry["poly"].vertices) == 4
    assert geometry["poly"].triangle_indices == ((0, 1, 2), (0, 2, 3))
    assert geometry["poly"].tessellation_settings["geometry_source"] == "points"
    assert len(geometry["circle"].vertices) == 4
    assert geometry["circle"].tessellation_settings["geometry_source"] == "rect_fallback"
    assert all(vertex[2] == 0.0 for item in scene.geometries for vertex in item.vertices)
    assert all(item.is_closed is False for item in scene.geometries)


def test_pointless_zero_extent_record_reports_missing_geometry(tmp_path: Path) -> None:
    """A degenerate bbox must not masquerade as usable planar geometry."""
    svg = tmp_path / "missing_geometry.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <text id="label-like-object" data-role="chair" x="10" y="10">chair</text>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries == ()
    assert scene.source_objects[0].geometry_refs == ()
    assert [item.code for item in scene.source_objects[0].uncertainties] == [
        "missing_geometry"
    ]


def test_open_boundary_polyline_is_not_fabricated_as_a_surface(
    tmp_path: Path,
) -> None:
    """An open multi-segment path should retain vertices without fan triangles."""
    svg = tmp_path / "open_boundary.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path id="open-wall" data-role="boundary" d="M 0 0 L 50 0 L 50 50"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert len(scene.geometries[0].vertices) == 3
    assert scene.geometries[0].triangle_indices == ()


def test_units_are_explicit_and_invalid_units_are_rejected() -> None:
    """The adapter must delegate unit validation to the Neutral Scene contract."""
    from ..adapters import load_svg_neutral_scene

    with pytest.raises(ValueError, match="source_length_unit"):
        load_svg_neutral_scene(SVG_FIXTURES[0], source_length_unit="viewBox")


def test_geometry_coordinates_and_unit_labels_use_analysis_unit(
    tmp_path: Path,
) -> None:
    """Converted coordinate values and mesh unit labels must stay consistent."""
    from ..adapters import load_svg_neutral_scene

    svg = tmp_path / "units.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
        <line id="axis" data-role="column_axis" x1="0" y1="0" x2="1000" y2="0"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = load_svg_neutral_scene(
        svg,
        source_length_unit="mm",
        analysis_length_unit="cm",
    )

    assert scene.geometries[0].vertices[1] == (100.0, 0.0, 0.0)
    assert scene.geometries[0].units == "cm"
    assert scene.context.world_coordinate_system["y_direction"] == "down"
    assert scene.context.world_coordinate_system["viewbox_size"] == (1000.0, 1000.0)


def test_svg_adapter_import_graph_excludes_analysis_and_bim_dependencies() -> None:
    """The source adapter should not import inference, evaluation, BIM, or OCTA code."""
    source = Path("adapters/svg_scene.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        (node.module or "").lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert not any(
        token in module
        for module in imported
        for token in ("ifc", "blender", "octa", "evaluator", "inference")
    )


def test_plain_neutral_scene_payload_round_trips_without_svg_parser() -> None:
    """Source-independent code should consume a plain v2 payload after adaptation."""
    payload = _load(SVG_FIXTURES[0]).to_dict()

    rebuilt = NeutralSceneV2.from_dict(json.loads(json.dumps(payload)))

    assert rebuilt.to_dict() == payload
