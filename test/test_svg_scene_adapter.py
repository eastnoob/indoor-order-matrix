"""Contract tests for the planar SVG Neutral Scene v2 adapter."""

import ast
from importlib import import_module
import json
import math
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
    scene = _load(fixture)
    payload = scene.to_dict()

    assert NeutralSceneV2.from_dict(json.loads(json.dumps(payload))).to_dict() == payload
    assert scene.context.input_mode == "svg"
    assert scene.context.source_schema == "SVG"
    assert scene.context.adapter_version == "svg-scene-adapter/0.4.0"
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

    repeated_ids = [item.id for item in _load(fixture).source_objects]
    assert [item.id for item in scene.source_objects] == repeated_ids
    assert len(scene.source_objects) == len({item.id for item in scene.source_objects})


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
    assert scene.authored_affordances[0].source_id == "chair-pullback"
    assert scene.authored_affordances[0].purpose == "pullback"
    assert scene.authored_affordances[0].source_furniture_refs == ("chair-1",)
    assert scene.authored_affordances[0].vertical_extent == (0.0, 0.9)
    assert len(scene.openings) == 1
    assert scene.openings[0].host_refs == ("wall-1",)
    assert scene.openings[0].opening_kind == "door"
    assert by_id["chair-1"].material_refs == ()
    assert by_id["chair-1"].surface_refs == ()
    assert {item.code for item in by_id["chair-1"].uncertainties} >= {
        "unresolved_material_ref",
        "unresolved_surface_ref",
    }
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


def test_planar_meshes_preserve_polygon_and_analytic_circle_sources(tmp_path: Path) -> None:
    """Polygon and circle geometry should retain their authored geometric source."""
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
    assert len(geometry["poly"].triangle_indices) == 2
    assert geometry["poly"].tessellation_settings["geometry_source"] == "authored_polygon"
    assert len(geometry["circle"].vertices) == 64
    assert geometry["circle"].tessellation_settings["geometry_source"] == "analytic_circle"
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
    assert {item.code for item in scene.source_objects[0].uncertainties} == {
        "missing_geometry",
        "unsupported_svg_geometry",
    }


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
    loader_source = Path("features/scene_loader.py").read_text(encoding="utf-8")

    assert "xml.etree" in source
    assert "scene_loader" not in source
    assert "_adapter_geometry_for_shape" not in loader_source
    assert "_compose_svg_affine" not in loader_source
    assert "import Rect" not in source


def test_plain_neutral_scene_payload_round_trips_without_svg_parser() -> None:
    """Source-independent code should consume a plain v2 payload after adaptation."""
    payload = _load(SVG_FIXTURES[0]).to_dict()

    rebuilt = NeutralSceneV2.from_dict(json.loads(json.dumps(payload)))

    assert rebuilt.to_dict() == payload


def test_legacy_id_roles_remain_compatibility_facts_not_authored_v2(
    tmp_path: Path,
) -> None:
    """Id-derived legacy roles must not cross the authored Neutral Scene boundary."""
    svg = tmp_path / "legacy_roles.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <line id="axis1" x1="0" y1="20" x2="100" y2="20"/>
        <path id="bottom_entry" d="M 20 100 L 40 80"/>
        <rect id="chair-by-name" x="10" y="10" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    objects = {item.id: item for item in scene.source_objects}

    assert scene.authored_grid_axes == ()
    assert scene.authored_grids == ()
    assert scene.openings == ()
    assert all(item.source_role == "unknown" for item in objects.values())
    assert all(
        "source_role_unavailable" in {warning.code for warning in item.uncertainties}
        for item in objects.values()
    )


def test_only_explicit_group_metadata_creates_v2_group_semantics(
    tmp_path: Path,
) -> None:
    """Fixture-specific parent names must not become authored Neutral Scene groups."""
    svg = tmp_path / "group_authorship.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <g id="west_lounge">
          <rect id="chair-legacy" x="5" y="5" width="10" height="10"/>
        </g>
        <g data-role="chair" data-group="authored-lounge">
          <rect id="chair-explicit" x="30" y="5" width="10" height="10"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    objects = {item.id: item for item in scene.source_objects}

    assert [(group.id, group.group_role, group.member_refs) for group in scene.authored_groups] == [
        ("authored-lounge", "source_group", ("chair-explicit",))
    ]
    assert objects["chair-legacy"].source_role == "unknown"
    assert objects["chair-legacy"].group_refs == ()
    assert objects["chair-explicit"].source_role == "chair"
    assert objects["chair-explicit"].group_refs == ("authored-lounge",)


def test_full_svg_affine_transforms_are_applied_once_in_world_coordinates(
    tmp_path: Path,
) -> None:
    """Scale, shear, nesting, and centered rotation must survive adapter handoff."""
    svg = tmp_path / "affine.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="scaled" data-role="table" x="1" y="2" width="3" height="4"
              transform="scale(2 3)"/>
        <rect id="sheared" data-role="table" x="0" y="0" width="2" height="2"
              transform="matrix(1 0 0.5 1 0 0)"/>
        <g transform="translate(10 20)">
          <rect id="nested" data-role="table" x="1" y="1" width="2" height="1"
                transform="scale(2)"/>
        </g>
        <rect id="center-rotated" data-role="table" x="20" y="10" width="2" height="1"
              transform="rotate(90 10 10)"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = load_svg_neutral_scene_for_test(svg, source_length_unit="m")
    geometry = {item.source_representation_id: item.vertices for item in scene.geometries}

    _assert_points(
        geometry["scaled"],
        ((2.0, 6.0, 0.0), (8.0, 6.0, 0.0), (8.0, 18.0, 0.0), (2.0, 18.0, 0.0)),
    )
    _assert_points(
        geometry["sheared"],
        ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (3.0, 2.0, 0.0), (1.0, 2.0, 0.0)),
    )
    _assert_points(
        geometry["nested"],
        ((12.0, 22.0, 0.0), (16.0, 22.0, 0.0), (16.0, 24.0, 0.0), (12.0, 24.0, 0.0)),
    )
    _assert_points(
        geometry["center-rotated"],
        ((10.0, 20.0, 0.0), (10.0, 22.0, 0.0), (9.0, 22.0, 0.0), (9.0, 20.0, 0.0)),
    )


def load_svg_neutral_scene_for_test(
    path: Path,
    *,
    source_length_unit: str,
) -> NeutralSceneV2:
    """Load an SVG with a non-default source unit for focused geometry tests."""
    from ..adapters import load_svg_neutral_scene

    return load_svg_neutral_scene(path, source_length_unit=source_length_unit)


def _assert_points(
    actual: object,
    expected: tuple[tuple[float, float, float], ...],
) -> None:
    """Compare ordered 3D point sequences with floating-point tolerance."""
    assert len(actual) == len(expected)
    for actual_point, expected_point in zip(actual, expected):
        assert actual_point == pytest.approx(expected_point)


def test_malformed_svg_path_becomes_uncertainty_instead_of_crashing(
    tmp_path: Path,
) -> None:
    """Parser failures from malformed paths remain explicit adapter uncertainty."""
    svg = tmp_path / "malformed-path.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
        '<path id="broken" data-role="table" d="M 0 0 C"/>'
        '</svg>',
        encoding="utf-8",
    )

    scene = load_svg_neutral_scene_for_test(svg, source_length_unit="m")

    assert any(
        uncertainty.code == "path_parse_failed"
        for uncertainty in scene.uncertainties
    ) or any(
        uncertainty.code == "path_parse_failed"
        for obj in scene.source_objects
        for uncertainty in obj.uncertainties
    )


def test_circle_and_ellipse_use_authored_curve_tessellation_not_bbox(
    tmp_path: Path,
) -> None:
    """Analytic SVG curves should retain curved area and non-corner vertices."""
    svg = tmp_path / "curves.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle id="circle" data-role="table" cx="20" cy="20" r="10"/>
        <ellipse id="ellipse" data-role="table" cx="60" cy="20" rx="15" ry="5"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = load_svg_neutral_scene_for_test(svg, source_length_unit="m")
    geometry = {item.source_representation_id: item for item in scene.geometries}

    assert len(geometry["circle"].vertices) >= 32
    assert len(geometry["ellipse"].vertices) >= 32
    assert geometry["circle"].tessellation_settings["geometry_source"] == "analytic_circle"
    assert geometry["ellipse"].tessellation_settings["geometry_source"] == "analytic_ellipse"
    assert _mesh_area(geometry["circle"]) == pytest.approx(math.pi * 100.0, rel=0.01)
    assert _mesh_area(geometry["ellipse"]) == pytest.approx(math.pi * 75.0, rel=0.01)


def _mesh_area(geometry: object) -> float:
    """Return XY triangle area for one transport mesh used by focused tests."""
    vertices = geometry.vertices
    return sum(
        abs(
            (vertices[b][0] - vertices[a][0]) * (vertices[c][1] - vertices[a][1])
            - (vertices[b][1] - vertices[a][1]) * (vertices[c][0] - vertices[a][0])
        )
        / 2.0
        for a, b, c in geometry.triangle_indices
    )


def test_concave_polygon_triangulation_stays_inside_authored_polygon(
    tmp_path: Path,
) -> None:
    """Concave polygon triangles must cover only the authored polygon interior."""
    from shapely.geometry import Polygon

    svg = tmp_path / "concave.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
        <polygon id="u-shape" data-role="table"
          points="0,0 4,0 4,4 3,4 3,1 1,1 1,4 0,4"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = load_svg_neutral_scene_for_test(svg, source_length_unit="m")
    mesh = scene.geometries[0]
    authored = Polygon(((0, 0), (4, 0), (4, 4), (3, 4), (3, 1), (1, 1), (1, 4), (0, 4)))
    triangles = [Polygon((mesh.vertices[a][:2], mesh.vertices[b][:2], mesh.vertices[c][:2])) for a, b, c in mesh.triangle_indices]

    assert triangles
    assert all(authored.covers(triangle) for triangle in triangles)
    assert sum(triangle.area for triangle in triangles) == pytest.approx(authored.area)


def test_unsupported_use_geometry_is_uncertain_not_bbox_source(tmp_path: Path) -> None:
    """An unresolved SVG use reference must not become an authored bbox mesh."""
    svg = tmp_path / "unsupported_use.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <use id="unresolved" data-role="boundary" href="#missing"
             x="10" y="20" width="30" height="40"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries == ()
    assert scene.source_objects[0].geometry_refs == ()
    assert "unsupported_svg_geometry" in {
        warning.code for warning in scene.source_objects[0].uncertainties
    }


def test_duplicate_explicit_source_ids_are_rejected_at_adapter_boundary(
    tmp_path: Path,
) -> None:
    """Ambiguous explicit SVG ids should fail before Neutral Scene refs are built."""
    svg = tmp_path / "duplicate_ids.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="duplicate" data-role="chair" x="0" y="0" width="10" height="10"/>
        <rect id="duplicate" data-role="chair" x="20" y="0" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate explicit SVG source id 'duplicate'"):
        _load(svg)


def test_missing_source_ids_receive_stable_neutral_ids_and_uncertainty(
    tmp_path: Path,
) -> None:
    """Id-less authored elements need deterministic neutral identity without fake source ids."""
    svg = tmp_path / "missing_ids.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <g data-role="chair">
          <rect x="0" y="0" width="10" height="10"/>
          <rect x="20" y="0" width="10" height="10"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )

    first = _load(svg)
    second = _load(svg)

    assert [item.id for item in first.source_objects] == [
        "svg-element-000001",
        "svg-element-000002",
    ]
    assert [item.id for item in second.source_objects] == [item.id for item in first.source_objects]
    assert all(item.source_id is None for item in first.source_objects)
    assert all(
        "missing_source_id" in {warning.code for warning in item.uncertainties}
        for item in first.source_objects
    )


def test_generated_neutral_ids_avoid_explicit_source_id_collisions(
    tmp_path: Path,
) -> None:
    """Traversal ids should deterministically skip ids explicitly owned by SVG elements."""
    svg = tmp_path / "generated_id_collision.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <g data-role="chair">
          <rect x="0" y="0" width="10" height="10"/>
          <rect id="svg-element-000001" x="20" y="0" width="10" height="10"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.id for item in scene.source_objects] == [
        "svg-element-000002",
        "svg-element-000001",
    ]
    assert len({item.id for item in scene.source_objects}) == 2


def test_generic_supported_geometry_is_collected_without_role_metadata(
    tmp_path: Path,
) -> None:
    """Supported visible geometry must reach v2 even when no role can be inferred."""
    svg = tmp_path / "generic_geometry.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="shape-a" x="1" y="2" width="10" height="20"/>
        <circle cx="40" cy="20" r="5"/>
        <polyline id="shape-c" points="60,10 70,20 80,10" fill="none"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.source_id for item in scene.source_objects] == [
        "shape-a",
        None,
        "shape-c",
    ]
    assert all(item.source_role == "unknown" for item in scene.source_objects)
    assert all(item.geometry_refs for item in scene.source_objects)
    assert all(
        "source_role_unavailable" in {warning.code for warning in item.uncertainties}
        for item in scene.source_objects
    )


def test_duplicate_ids_on_generic_geometry_are_rejected(tmp_path: Path) -> None:
    """Duplicate ids must be rejected even when legacy role filtering would drop them."""
    svg = tmp_path / "generic_duplicate_ids.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="shape" x="0" y="0" width="10" height="10"/>
        <circle id="shape" cx="30" cy="30" r="5"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate explicit SVG source id 'shape'"):
        _load(svg)


def test_dangling_explicit_references_are_omitted_with_uncertainty(
    tmp_path: Path,
) -> None:
    """Every emitted adapter reference must resolve to a Neutral Scene record."""
    svg = tmp_path / "dangling_refs.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="chair" data-role="chair" data-material-ref="missing-material"
              data-surface-ref="missing-surface" x="10" y="10" width="10" height="10"/>
        <rect id="zone" data-role="affordance" data-purpose="pullback"
              data-source-furniture-refs="chair missing-chair"
              x="5" y="5" width="20" height="20"/>
        <rect id="wall" data-role="boundary" x="0" y="0" width="100" height="2"/>
        <line id="door" data-role="opening" data-host-refs="wall missing-wall"
              x1="20" y1="0" x2="30" y2="0"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    by_id = {item.id: item for item in scene.source_objects}
    scene_codes = {item.code for item in scene.uncertainties}

    assert by_id["chair"].material_refs == ()
    assert by_id["chair"].surface_refs == ()
    assert scene.authored_affordances[0].source_furniture_refs == ("chair",)
    assert scene.openings[0].host_refs == ("wall",)
    assert by_id["wall"].opening_refs == ("door",)
    assert {item.code for item in by_id["chair"].uncertainties} >= {
        "unresolved_material_ref",
        "unresolved_surface_ref",
    }
    assert scene_codes >= {
        "unresolved_affordance_owner_ref",
        "unresolved_opening_host_ref",
    }


def test_multiple_explicit_analysis_domains_are_rejected(tmp_path: Path) -> None:
    """The adapter must not silently select one of several authored domains."""
    svg = tmp_path / "multiple_domains.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="domain-a" data-role="analysis_domain" x="0" y="0" width="40" height="40"/>
        <rect id="domain-b" data-role="analysis_domain" x="50" y="50" width="40" height="40"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple explicit SVG analysis domains"):
        _load(svg)


def test_closed_stroke_only_path_remains_faceless(tmp_path: Path) -> None:
    """A closed path with explicit no-fill styling must remain line geometry."""
    svg = tmp_path / "stroke_only.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <path id="outline" d="M 1 1 L 10 1 L 10 10 Z"
              style="fill:none;fill-rule:evenodd;stroke:#000"/>
        </svg>""",
        encoding="utf-8",
    )

    mesh = _load(svg).geometries[0]

    assert mesh.triangle_indices == ()
    assert mesh.tessellation_settings["fill"] == "none"
    assert mesh.tessellation_settings["fill_rule"] == "evenodd"


def test_multi_subpath_fill_is_preserved_as_lines_with_uncertainty(
    tmp_path: Path,
) -> None:
    """Potential holes must not be flattened into a fabricated filled polygon."""
    svg = tmp_path / "path_hole.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <path id="ring" fill="black" fill-rule="evenodd"
              d="M 1 1 L 19 1 L 19 19 L 1 19 Z M 5 5 L 5 15 L 15 15 L 15 5 Z"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    mesh = scene.geometries[0]

    assert mesh.triangle_indices == ()
    assert mesh.tessellation_settings["subpath_count"] == 2
    assert "unsupported_path_fill_topology" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


@pytest.mark.parametrize(
    ("element", "source_id"),
    [
        ('<circle id="zero" cx="10" cy="10" r="0"/>', "zero"),
        ('<circle id="negative" cx="10" cy="10" r="-1"/>', "negative"),
        ('<circle id="nonfinite" cx="10" cy="10" r="NaN"/>', "nonfinite"),
        ('<ellipse id="flat" cx="10" cy="10" rx="4" ry="0"/>', "flat"),
    ],
)
def test_invalid_circle_and_ellipse_dimensions_are_uncertain(
    tmp_path: Path,
    element: str,
    source_id: str,
) -> None:
    """Nonpositive or nonfinite curve dimensions must not produce geometry."""
    svg = tmp_path / f"{source_id}.svg"
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">{element}</svg>',
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries == ()
    assert scene.source_objects[0].geometry_refs == ()
    assert "invalid_curve_dimensions" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


def test_curved_path_records_sampling_strategy_and_count(tmp_path: Path) -> None:
    """Path transport geometry must disclose its deterministic curve sampling."""
    svg = tmp_path / "curve_sampling.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path id="curve" fill="none" d="M 0 0 C 10 20 20 20 30 0"/>
        </svg>""",
        encoding="utf-8",
    )

    settings = _load(svg).geometries[0].tessellation_settings

    assert settings["curve_sampling_strategy"] == "fixed_samples_per_segment"
    assert settings["curve_samples_per_segment"] == 16
    assert settings["curve_sampling_tolerance"] is None
    assert settings["sampled_vertex_count"] == 17


def test_duplicate_id_between_defs_and_visible_geometry_is_rejected(
    tmp_path: Path,
) -> None:
    """Every explicit document id must be unique, including non-emitted resources."""
    svg = tmp_path / "defs_duplicate.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <defs><path id="shared" d="M 0 0 L 1 1"/></defs>
        <rect id="shared" x="2" y="2" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate explicit SVG source id 'shared'"):
        _load(svg)


def test_fallback_ids_reserve_ids_owned_by_nonemitted_resources(
    tmp_path: Path,
) -> None:
    """Generated ids must skip explicit ids even when their owner is not emitted."""
    svg = tmp_path / "defs_reserved_id.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <defs><path id="svg-element-000001" d="M 0 0 L 1 1"/></defs>
        <rect x="2" y="2" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.id for item in scene.source_objects] == ["svg-element-000002"]


def test_empty_explicit_document_id_is_rejected(tmp_path: Path) -> None:
    """An explicitly present empty id must not be reinterpreted as a missing id."""
    svg = tmp_path / "empty_id.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <rect id="" x="2" y="2" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="empty explicit SVG id"):
        _load(svg)


def test_resource_container_geometry_is_not_emitted_as_source_geometry(
    tmp_path: Path,
) -> None:
    """Geometry under non-rendering SVG resource containers must stay non-source."""
    svg = tmp_path / "resources.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <clipPath id="clip"><rect id="clip-shape" width="5" height="5"/></clipPath>
        <mask id="mask"><rect id="mask-shape" width="5" height="5"/></mask>
        <marker id="marker"><path id="marker-shape" d="M 0 0 L 1 1"/></marker>
        <pattern id="pattern"><rect id="pattern-shape" width="5" height="5"/></pattern>
        <symbol id="symbol"><circle id="symbol-shape" cx="2" cy="2" r="1"/></symbol>
        <defs id="defs"><path id="defs-shape" d="M 0 0 L 1 1"/></defs>
        <rect id="visible" x="10" y="10" width="20" height="20"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.source_id for item in scene.source_objects] == ["visible"]
    assert [item.source_representation_id for item in scene.geometries] == ["visible"]


def test_simple_stylesheet_class_and_id_rules_control_fill_topology(
    tmp_path: Path,
) -> None:
    """Simple local class and id rules must determine fill and fill-rule facts."""
    svg = tmp_path / "stylesheet_fill.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <style>
          .outline { fill: none; }
          #styled { fill-rule: evenodd; }
        </style>
        <path id="styled" class="outline" d="M 1 1 L 10 1 L 10 10 Z"/>
        </svg>""",
        encoding="utf-8",
    )

    mesh = _load(svg).geometries[0]

    assert mesh.triangle_indices == ()
    assert mesh.tessellation_settings["fill"] == "none"
    assert mesh.tessellation_settings["fill_rule"] == "evenodd"


def test_unresolved_stylesheet_selector_forces_faceless_uncertain_geometry(
    tmp_path: Path,
) -> None:
    """Unsupported CSS selectors must not allow a possibly stroke-only face."""
    svg = tmp_path / "unresolved_stylesheet.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <style>path[data-mode="outline"] { fill: none; }</style>
        <path id="styled" data-mode="outline" d="M 1 1 L 10 1 L 10 10 Z"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries[0].triangle_indices == ()
    assert "unresolved_css_presentation" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


def test_nested_svg_viewport_geometry_is_rejected_with_uncertainty(
    tmp_path: Path,
) -> None:
    """Nested viewport coordinates must never pass through without composition."""
    svg = tmp_path / "nested_viewport.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <svg id="viewport" x="20" y="30" width="40" height="20"
             viewBox="0 0 10 10" preserveAspectRatio="xMidYMid meet">
          <rect id="nested-shape" x="1" y="1" width="4" height="4"/>
        </svg>
        <rect id="visible" x="70" y="70" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)
    objects = {item.id: item for item in scene.source_objects}
    geometries = {item.source_representation_id: item for item in scene.geometries}

    assert objects["nested-shape"].geometry_refs == ()
    assert "unsupported_nested_svg_viewport" in {
        item.code for item in objects["nested-shape"].uncertainties
    }
    assert "nested-shape" not in geometries
    assert "visible" in geometries


@pytest.mark.parametrize(
    "fill_declaration",
    (
        "fill: var(--surface-fill)",
        "fill: initial",
        "fill: context-fill",
        "fill-rule: var(--surface-rule)",
    ),
)
def test_unresolved_css_property_values_force_faceless_geometry(
    tmp_path: Path,
    fill_declaration: str,
) -> None:
    """Unsupported CSS property values must never manufacture a filled face."""
    svg = tmp_path / "unresolved_css_value.svg"
    svg.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <style>.surface {{ {fill_declaration}; }}</style>
        <path id="surface" class="surface" d="M 1 1 L 10 1 L 10 10 Z"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries[0].triangle_indices == ()
    assert "unresolved_css_presentation" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


def test_inherited_css_keyword_is_conservatively_faceless(tmp_path: Path) -> None:
    """An inherited fill remains faceless when the adapter declines CSS-wide values."""
    svg = tmp_path / "inherited_fill.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <g fill="none">
          <path id="surface" style="fill: inherit" d="M 1 1 L 10 1 L 10 10 Z"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries[0].triangle_indices == ()
    assert "unresolved_css_presentation" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


def test_inline_important_fill_is_conservatively_faceless(tmp_path: Path) -> None:
    """Inline important declarations must not bypass conservative CSS handling."""
    svg = tmp_path / "important_fill.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <path id="surface" style="fill: none !important"
              d="M 1 1 L 10 1 L 10 10 Z"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries[0].triangle_indices == ()
    assert "unresolved_css_presentation" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


def test_external_stylesheet_marker_forces_conservative_fill(tmp_path: Path) -> None:
    """External stylesheet dependence must prevent locally fabricated fill topology."""
    svg = tmp_path / "external_stylesheet.svg"
    svg.write_text(
        """<?xml-stylesheet type="text/css" href="theme.css"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
          <rect id="surface" x="1" y="1" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert scene.geometries[0].triangle_indices == ()
    assert "unresolved_css_presentation" in {
        item.code for item in scene.source_objects[0].uncertainties
    }


@pytest.mark.parametrize("source_id", ("bad id", " padded", "tail ", "line\nbreak"))
def test_whitespace_containing_explicit_ids_are_rejected(
    tmp_path: Path,
    source_id: str,
) -> None:
    """SVG ids containing XML whitespace must be rejected rather than normalized."""
    svg = tmp_path / "invalid_whitespace_id.svg"
    svg.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <rect id="{source_id}" x="1" y="1" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid explicit SVG id"):
        _load(svg)


def test_normalization_changing_explicit_id_is_rejected(tmp_path: Path) -> None:
    """A non-NFC id must not acquire a different neutral identity during validation."""
    svg = tmp_path / "non_normalized_id.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
        <rect id="e\u0301" x="1" y="1" width="10" height="10"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid explicit SVG id"):
        _load(svg)


def test_foreign_namespace_geometry_is_excluded_but_reserves_ids(
    tmp_path: Path,
) -> None:
    """Foreign geometry is non-source while every foreign id still reserves identity."""
    svg = tmp_path / "foreign_geometry.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"
                  xmlns:x="urn:example:foreign" viewBox="0 0 20 20">
        <foreignObject id="foreign-container" x="0" y="0" width="5" height="5">
          <x:rect id="svg-element-000001" x="1" y="1" width="2" height="2"/>
          <rect id="embedded-svg" x="1" y="1" width="2" height="2"/>
        </foreignObject>
        <rect x="10" y="10" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    scene = _load(svg)

    assert [item.id for item in scene.source_objects] == ["svg-element-000002"]
    assert scene.source_objects[0].provenance["source_namespace"] == (
        "http://www.w3.org/2000/svg"
    )


def test_foreign_namespace_ids_participate_in_duplicate_validation(
    tmp_path: Path,
) -> None:
    """A foreign element id must still collide with the same visible SVG id."""
    svg = tmp_path / "foreign_duplicate.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"
                  xmlns:x="urn:example:foreign" viewBox="0 0 20 20">
        <foreignObject><x:rect id="shared"/></foreignObject>
        <rect id="shared" x="10" y="10" width="5" height="5"/>
        </svg>""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate explicit SVG source id 'shared'"):
        _load(svg)
