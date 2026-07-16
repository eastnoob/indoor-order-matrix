import ast
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE = Path("test/floorplan_order_fixture.svg")
VALID_GRASSHOPPER_BRANCHES = [
    {
        "path": "{0;objects;0}",
        "kind": "object_record",
        "id": "table",
        "role": "table",
    },
    {
        "path": "{0;metrics;0}",
        "kind": "metric_row",
        "id": "adapter_readiness.adapter_reference_coverage",
    },
    {
        "path": "{0;graphs;walk_graph}",
        "kind": "graph_namespace",
        "id": "walk_graph",
    },
]


def _fixture_elements():
    root = ET.parse(FIXTURE).getroot()
    return list(root.iter())


def test_floorplan_fixture_has_structured_metadata():
    elements = _fixture_elements()
    roles = {element.attrib.get("data-role") for element in elements}
    groups = {element.attrib.get("data-group") for element in elements}
    regions = {element.attrib.get("data-region") for element in elements}

    assert "table" in roles
    assert "sofa" in roles
    assert "armchair" in roles
    assert "boundary" in roles
    assert "opening" in roles
    assert "north_tables" in groups
    assert "west_lounge" in groups
    assert "center_lounge" in groups
    assert "east_armchairs" in groups
    assert "north_tables" in regions


from features.affordance.models import Rect
from features.column_grid import column_grid_evidence
from features.scene_evaluator import evaluate_scene
from features.scene_loader import load_structured_svg_scene
from features.scene_inference import infer_scene_evidence


def test_load_structured_svg_scene_returns_expected_scene_records():
    scene = load_structured_svg_scene(FIXTURE)

    assert scene["source"] == str(FIXTURE)
    assert scene["size"] == (1000.0, 1000.0)
    assert len(scene["objects"]) >= 20
    assert len(scene["boundaries"]) >= 2
    assert len(scene["entries"]) >= 2
    assert len(scene["regions"]) >= 4
    assert len(scene["paths"]) >= 1
    assert len(scene["column_axes"]) >= 2
    slanted_region = [
        region for region in scene["regions"] if region["id"] == "region_slanted_test"
    ][0]
    assert slanted_region["points"]
    assert "axis-angle" not in slanted_region["metadata"]
    entries = {entry["id"]: entry for entry in scene["entries"]}
    assert entries["bottom_entry"]["rect"].cx == 457.5
    assert entries["bottom_entry"]["rect"].cy == 882.5
    assert entries["right_entry_arc"]["rect"].cx == 905.0
    assert entries["right_entry_arc"]["rect"].cy == 795.0

    boundary_weights = {
        item["id"]: item["weights"]
        for item in scene["boundaries"] + scene["entries"] + scene["paths"]
    }
    assert boundary_weights["outer_wall"]["walk_block"] == 1.0
    assert boundary_weights["outer_wall"]["see_block"] == 1.0
    assert boundary_weights["path_placeholder"]["walk_block"] == 0.0
    assert boundary_weights["path_placeholder"]["grouping_strength"] == 0.2
    assert boundary_weights["glass_boundary"]["walk_block"] == 1.0
    assert boundary_weights["glass_boundary"]["see_block"] == 0.15
    assert boundary_weights["rug_boundary"]["walk_block"] == 0.0
    assert boundary_weights["rug_boundary"]["grouping_strength"] == 0.85
    assert boundary_weights["material_boundary"]["walk_block"] == 0.0
    assert boundary_weights["material_boundary"]["see_block"] == 0.0
    assert boundary_weights["material_boundary"]["grouping_strength"] == 0.55
    boundaries = {boundary["id"]: boundary for boundary in scene["boundaries"]}
    assert boundaries["outer_wall"]["metadata"]["thickness"] == "8"
    assert boundaries["internal_partition"]["metadata"]["thickness"] == "5"
    assert boundaries["glass_boundary"]["metadata"]["thickness"] == "3"
    assert boundaries["rug_boundary"]["metadata"]["thickness"] == "0"
    assert boundaries["diagonal_boundary"]["points"] == [(635.0, 305.0), (825.0, 495.0)]
    assert boundaries["diagonal_boundary"]["metadata"]["boundary-kind"] == "visual"
    assert boundaries["room_boundary"]["adapter_refs"] == {
        "ifc_guid": "ifc-room-boundary",
        "source_layer": "A-WALL",
    }

    object_ids = {obj["id"] for obj in scene["objects"]}
    assert "north_table_r1_c1" in object_ids
    assert "west_sofa_1" in object_ids
    assert "east_armchair_left" in object_ids
    objects = {obj["id"]: obj for obj in scene["objects"]}
    assert objects["north_table_r1_c1"]["adapter_refs"] == {
        "rhino_guid": "rhino-north-table-r1-c1",
        "source_layer": "I-FURN",
    }

    north_tables = [
        obj
        for obj in scene["objects"]
        if obj["group"] == "north_tables" and obj["role"] == "table"
    ]
    assert len(north_tables) == 6
    assert all(obj["rect"].width > 0 and obj["rect"].height > 0 for obj in north_tables)


def test_svg_id_fixture_without_manual_regions_loads_semantic_proxy_records():
    """ID-only SVG fixtures should still become neutral scene records."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    assert len(scene["objects"]) >= 20
    assert len(scene["regions"]) == 0
    assert len(scene["paths"]) == 0
    assert len(scene["entries"]) >= 2
    assert len(scene["column_axes"]) >= 2

    objects = {obj["id"]: obj for obj in scene["objects"]}
    assert objects["north_table_r1_c1"]["role"] == "table"
    assert objects["north_table_r1_c1"]["group"] == "north_tables"
    assert objects["west_sofa_1"]["role"] == "sofa"
    assert objects["east_work_chair"]["role"] == "chair"


def test_svg_loader_separates_pilers_from_explicit_column_axes():
    """Piler records are columns; explicit SVG axis records are column axes."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    column_ids = {item["id"] for item in scene["columns"]}
    axis_ids = {item["id"] for item in scene["column_axes"]}

    assert "columns" in scene
    assert len(scene["columns"]) == 9
    assert {"piler", "piler1", "piler6", "piller", "pller"} <= column_ids
    assert {"column_axis_x", "column_axis_y", "axis1", "axis6"} <= axis_ids
    assert all(item["role"] == "column" for item in scene["columns"])
    assert all(item["role"] == "column_axis" for item in scene["column_axes"])


def test_svg_loader_preserves_authored_dashed_axis_path_extents():
    """Dashed axis paths should load as compact long authored axes."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    axes = {axis["id"]: axis for axis in scene["column_axes"]}

    # The SVG stores visible dashed grid axes as filled cubic path segments; the
    # loader keeps their bbox extent while simplifying calculation points to the
    # centerline that downstream grid and distance metrics need.
    assert axes["axis1"]["rect"].height > 900
    assert axes["axis4"]["rect"].width > 900
    assert axes["axis6"]["rect"].width > 900
    assert len(axes["axis1"]["points"]) == 2
    assert len(axes["axis4"]["points"]) == 2


def test_svg_loader_only_treats_explicit_axis_ids_as_column_axes(tmp_path):
    """Axis labels and axis-like path names should not become column axes."""
    svg = tmp_path / "axis_ids.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path id="axis1" d="M0,0 L100,0" />
  <path id="axis_label" d="M0,10 L100,10" />
  <path id="axis_walk_path" d="M0,20 L100,20" />
</svg>""",
        encoding="utf-8",
    )

    scene = load_structured_svg_scene(svg)

    assert [axis["id"] for axis in scene["column_axes"]] == ["axis1"]


def test_svg_loader_preserves_explicit_furniture_group_id(tmp_path):
    """SVG proxy group labels should normalize into furniture_group metadata."""
    svg = tmp_path / "furniture_group.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect id="table" data-role="table" data-region="dining" data-furniture-group="dining_set_1" x="10" y="10" width="20" height="10" />
  <rect id="chair" data-role="chair" data-region="dining" data-furniture-group="dining_set_1" x="10" y="30" width="20" height="10" />
</svg>""",
        encoding="utf-8",
    )

    scene = load_structured_svg_scene(svg)

    assert {obj["metadata"]["furniture-group"] for obj in scene["objects"]} == {
        "dining_set_1"
    }
    assert {obj["furniture_group"] for obj in scene["objects"]} == {"dining_set_1"}


def test_svg_table_sets_are_distinct_furniture_groups_inside_north_region():
    """Each north table set should be a furniture group inside one region."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    north_objects = [
        obj for obj in scene["objects"]
        if obj["region"] == "north_tables"
    ]
    north_furniture_groups = {
        obj["furniture_group"]
        for obj in north_objects
    }

    assert north_furniture_groups == {
        "north_table_group_r1_c1",
        "north_table_group_r1_c2",
        "north_table_group_r1_c3",
        "north_table_group_r2_c1",
        "north_table_group_r2_c2",
        "north_table_group_r2_c3",
    }
    assert {obj["region"] for obj in north_objects} == {"north_tables"}


def test_adapter_payload_keeps_physical_columns_as_scene_records():
    """Columns should stay visible to adapter targets without sharing axis records."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    payload = evaluate_scene(scene)["adapter_payload"]
    record_ids = {record["id"] for record in payload["scene_records"]}

    assert {"piler", "piler1", "piler6", "piller", "pller"} <= record_ids


def test_evaluator_emits_column_grid_relation_rows():
    """Matrix rows should expose explicit-axis C_global and C_local_profile evidence."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            {
                "id": "seating",
                "region": "seating",
                "role": "region",
                "rect": Rect(cx=40, cy=40, width=40, height=40),
                "metadata": {},
            }
        ],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
        ],
    }
    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}

    assert rows["column_grid_C_global"]["status"] == "computed"
    assert rows["column_grid_C_local_profile"]["status"] == "computed"
    assert rows["column_grid_C_global"]["column_grid_evidence"]["global_relations"]
    assert rows["column_grid_C_local_profile"]["column_grid_evidence"]["local_profiles"]
    assert matrix["adapter_payload"]["column_grid_handoff"]["C_global"]["evidence_count"] > 0
    assert matrix["adapter_payload"]["column_grid_handoff"]["C_local_profile"]["evidence_count"] > 0


def test_evaluator_does_not_fabricate_column_grid_local_profiles_without_bays():
    """Explicit axes without bays should not invent C_local_profile evidence."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            {
                "id": "seating",
                "region": "seating",
                "role": "region",
                "rect": Rect(cx=40, cy=40, width=40, height=40),
                "metadata": {},
            }
        ],
        "columns": [],
        "column_axes": [
            {
                "id": "line_only",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=50, width=0, height=100),
                "points": [(50, 0), (50, 100)],
                "metadata": {"branch-id": "without_bays", "axis-list": "y"},
            },
        ],
    }

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    handoff = matrix["adapter_payload"]["column_grid_handoff"]

    assert rows["column_grid_C_global"]["status"] == "computed"
    assert rows["column_grid_C_local_profile"]["status"] == "not_available"
    assert rows["column_grid_C_local_profile"]["evidence"] == []
    assert handoff["C_global"]["evidence_count"] > 0
    assert handoff["C_local_profile"]["evidence_count"] == 0
    assert handoff["C_local_profile"]["items"] == []


def test_evaluator_marks_empty_column_grid_relation_evidence_not_available():
    """Computed column grids with no region evidence should expose unavailable rows."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
        ],
    }

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    handoff = matrix["adapter_payload"]["column_grid_handoff"]

    assert rows["column_grid_C_global"]["status"] == "not_available"
    assert rows["column_grid_C_global"]["score"] is None
    assert rows["column_grid_C_local_profile"]["status"] == "not_available"
    assert rows["column_grid_C_local_profile"]["score"] is None
    assert handoff["C_global"]["evidence_count"] == 0
    assert handoff["C_local_profile"]["evidence_count"] == 0


def test_column_grid_evidence_builds_bays_from_explicit_axes():
    """Explicit axes should create neutral systems, branches, bays, and graph edges."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=0, width=300, height=0),
                "points": [(0, 0), (300, 0)],
                "metadata": {
                    "grid-id": "main",
                    "branch-id": "orthogonal",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=100, width=300, height=0),
                "points": [(0, 100), (300, 100)],
                "metadata": {
                    "grid-id": "main",
                    "branch-id": "orthogonal",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {
                    "grid-id": "main",
                    "branch-id": "orthogonal",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=120, cy=50, width=0, height=100),
                "points": [(120, 0), (120, 100)],
                "metadata": {
                    "grid-id": "main",
                    "branch-id": "orthogonal",
                    "axis-list": "y",
                },
            },
        ],
    }
    evidence = column_grid_evidence(scene)

    assert evidence["systems"][0]["id"] == "main"
    assert evidence["branches"][0]["id"] == "orthogonal"
    assert len(evidence["bays"]) == 1
    assert evidence["bays"][0]["axis_ids"] == ["x0", "x1", "y0", "y1"]
    assert evidence["bays"][0]["adjacent_bay_ids"] == []


def test_column_grid_evidence_bay_adjacency_excludes_diagonal_bays():
    """Multi-bay grids should connect edge neighbors without diagonal leakage."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=0, width=200, height=0),
                "points": [(0, 0), (200, 0)],
                "metadata": {"axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=100, width=200, height=0),
                "points": [(0, 100), (200, 100)],
                "metadata": {"axis-list": "x"},
            },
            {
                "id": "x2",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=200, width=200, height=0),
                "points": [(0, 200), (200, 200)],
                "metadata": {"axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=200, width=0, height=200),
                "points": [(0, 0), (0, 200)],
                "metadata": {"axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=40, width=0, height=80),
                "points": [(100, 0), (100, 200)],
                "metadata": {"axis-list": "y"},
            },
            {
                "id": "y2",
                "role": "column_axis",
                "rect": Rect(cx=200, cy=120, width=0, height=160),
                "points": [(200, 0), (200, 200)],
                "metadata": {"axis-list": "y"},
            },
        ],
    }
    evidence = column_grid_evidence(scene)
    bays = {tuple(bay["axis_ids"]): bay for bay in evidence["bays"]}

    assert len(evidence["bays"]) == 4
    corner = bays[("x0", "x1", "y0", "y1")]
    right = bays[("x0", "x1", "y1", "y2")]
    lower = bays[("x1", "x2", "y0", "y1")]
    diagonal = bays[("x1", "x2", "y1", "y2")]
    assert set(corner["adjacent_bay_ids"]) == {right["id"], lower["id"]}
    assert diagonal["id"] not in corner["adjacent_bay_ids"]


def test_column_grid_evidence_bay_adjacency_excludes_skipped_strip_bays():
    """A bay strip should connect neighbors without jumping over middle bays."""
    scene = {
        "source": "unit",
        "size": (400.0, 100.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=0, width=300, height=0),
                "points": [(0, 0), (300, 0)],
                "metadata": {"axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=100, width=300, height=0),
                "points": [(0, 100), (300, 100)],
                "metadata": {"axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"axis-list": "y"},
            },
            {
                "id": "y2",
                "role": "column_axis",
                "rect": Rect(cx=200, cy=50, width=0, height=100),
                "points": [(200, 0), (200, 100)],
                "metadata": {"axis-list": "y"},
            },
            {
                "id": "y3",
                "role": "column_axis",
                "rect": Rect(cx=300, cy=50, width=0, height=100),
                "points": [(300, 0), (300, 100)],
                "metadata": {"axis-list": "y"},
            },
        ],
    }
    evidence = column_grid_evidence(scene)
    bays = {tuple(bay["axis_ids"]): bay for bay in evidence["bays"]}

    assert len(evidence["bays"]) == 3
    left = bays[("x0", "x1", "y0", "y1")]
    middle = bays[("x0", "x1", "y1", "y2")]
    right = bays[("x0", "x1", "y2", "y3")]
    assert middle["id"] in left["adjacent_bay_ids"]
    assert right["id"] in middle["adjacent_bay_ids"]
    assert right["id"] not in left["adjacent_bay_ids"]


def test_column_grid_evidence_bay_adjacency_stays_within_system():
    """Same-named branches in different systems should not share bay edges."""
    scene = {
        "source": "unit",
        "size": (300.0, 200.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {
                    "grid-id": "north",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {
                    "grid-id": "north",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {
                    "grid-id": "north",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {
                    "grid-id": "north",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {
                    "grid-id": "south",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=200, width=100, height=0),
                "points": [(0, 200), (100, 200)],
                "metadata": {
                    "grid-id": "south",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=150, width=0, height=100),
                "points": [(0, 100), (0, 200)],
                "metadata": {
                    "grid-id": "south",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y2",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=150, width=0, height=100),
                "points": [(100, 100), (100, 200)],
                "metadata": {
                    "grid-id": "south",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
        ],
    }
    evidence = column_grid_evidence(scene)
    bays_by_system = {bay["system_id"]: bay for bay in evidence["bays"]}

    assert len(evidence["bays"]) == 2
    assert bays_by_system["north"]["adjacent_bay_ids"] == []
    assert bays_by_system["south"]["adjacent_bay_ids"] == []


def test_column_grid_evidence_system_id_overrides_shared_grid_id_for_adjacency():
    """Explicit system IDs should split bays even when grid and branch IDs match."""
    scene = {
        "source": "unit",
        "size": (300.0, 100.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x2",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=200, width=100, height=0),
                "points": [(0, 200), (100, 200)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=150, width=0, height=100),
                "points": [(0, 100), (0, 200)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=150, width=0, height=100),
                "points": [(100, 100), (100, 200)],
                "metadata": {
                    "grid-id": "shared-grid",
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
        ],
    }
    evidence = column_grid_evidence(scene)
    bays_by_system = {bay["system_id"]: bay for bay in evidence["bays"]}

    assert {system["id"] for system in evidence["systems"]} == {
        "east-system",
        "west-system",
    }
    assert len(evidence["bays"]) == 2
    assert bays_by_system["east-system"]["adjacent_bay_ids"] == []
    assert bays_by_system["west-system"]["adjacent_bay_ids"] == []
    assert evidence["local_profiles"] == []
    assert evidence["global_relations"] == []


def test_column_grid_evidence_local_profiles_keep_reused_axis_ids_system_scoped():
    """Local bay profiles should not collide when systems reuse branch and axis IDs."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [
            {
                "id": "west_region",
                "role": "region",
                "rect": Rect(cx=50, cy=50, width=20, height=20),
                "metadata": {},
            },
            {
                "id": "east_region",
                "role": "region",
                "rect": Rect(cx=250, cy=250, width=20, height=20),
                "metadata": {},
            },
        ],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {
                    "system-id": "west-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=250, cy=200, width=100, height=0),
                "points": [(200, 200), (300, 200)],
                "metadata": {
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=250, cy=300, width=100, height=0),
                "points": [(200, 300), (300, 300)],
                "metadata": {
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "x",
                },
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=200, cy=250, width=0, height=100),
                "points": [(200, 200), (200, 300)],
                "metadata": {
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=300, cy=250, width=0, height=100),
                "points": [(300, 200), (300, 300)],
                "metadata": {
                    "system-id": "east-system",
                    "branch-id": "shared",
                    "axis-list": "y",
                },
            },
        ],
    }
    evidence = column_grid_evidence(scene)
    bay_ids = [bay["id"] for bay in evidence["bays"]]

    assert len(bay_ids) == len(set(bay_ids))
    for profile in evidence["local_profiles"]:
        for bay_id in profile["included_bay_ids"]:
            # A local profile ID must resolve to one bay in the same authored branch.
            matches = [bay for bay in evidence["bays"] if bay["id"] == bay_id]
            assert len(matches) == 1
            assert matches[0]["system_id"] == profile["system_id"]
            assert matches[0]["branch_id"] == profile["branch_id"]
        for grammar_item in profile["bay_grammar"]:
            assert grammar_item["bay_id"] in profile["included_bay_ids"]


def test_column_grid_evidence_reports_global_and_local_profiles_for_regions():
    """Furniture regions should relate to explicit global and local column-grid evidence."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [
            {
                "id": "seating",
                "role": "region",
                "rect": Rect(cx=40, cy=40, width=40, height=40),
                "metadata": {},
            }
        ],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
            {
                "id": "line_only",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=50, width=0, height=100),
                "points": [(150, 0), (150, 100)],
                "metadata": {"branch-id": "without_bays", "axis-list": "y"},
            },
        ],
    }

    grid = column_grid_evidence(scene)

    assert grid["global_relations"]
    assert grid["local_profiles"]
    assert all(item["metric"] == "C_global" for item in grid["global_relations"])
    assert all(item["metric"] == "C_local_profile" for item in grid["local_profiles"])
    assert all(
        {
            "agreement",
            "region_angle",
            "region_id",
            "source",
            "target_angle",
            "target_id",
            "target_kind",
            "target_strength",
        }
        <= item.keys()
        for item in grid["global_relations"]
    )
    assert all("agreement_score" not in item for item in grid["global_relations"])
    assert all(
        {
            "branch_angle",
            "frame_agreement",
            "region_angle",
            "region_id",
            "source",
            "system_id",
        }
        <= item.keys()
        for item in grid["local_profiles"]
    )
    assert all("agreement_score" not in item for item in grid["local_profiles"])
    assert {item["scale"] for item in grid["local_profiles"]} == {0, 1, "all"}
    assert all(item["seed_bay_ids"] for item in grid["local_profiles"])
    assert all(item["included_bay_ids"] for item in grid["local_profiles"])
    assert all(item["bay_grammar"] for item in grid["local_profiles"])
    assert all(
        {
            "bay_id",
            "overlap_area",
            "overlap_score",
            "region_area",
            "region_center_in_bay",
        }
        <= grammar_item.keys()
        for item in grid["local_profiles"]
        for grammar_item in item["bay_grammar"]
    )
    assert {item["branch_id"] for item in grid["local_profiles"]} == {"with_bays"}


def test_column_grid_evidence_does_not_infer_axes_from_columns():
    """Columns alone are evidence, not enough to silently create a grid."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [],
        "columns": [
            {
                "id": "piler_1",
                "role": "column",
                "rect": Rect(cx=0, cy=0, width=10, height=10),
                "metadata": {},
            },
            {
                "id": "piler_2",
                "role": "column",
                "rect": Rect(cx=100, cy=0, width=10, height=10),
                "metadata": {},
            },
        ],
        "column_axes": [],
    }
    evidence = column_grid_evidence(scene)

    assert evidence["systems"] == []
    assert evidence["bays"] == []
    assert evidence["status"] == "not_available"
    assert evidence["reason"] == "missing_explicit_column_axes"


def test_svg_id_fixtures_do_not_contain_manual_region_marks():
    """Official SVG fixtures should leave activity regions to inference."""
    fixture_names = ["SVG_baseline.svg", "SVG_chaoticsvg.svg", "SVG_oblique.svg"]

    for name in fixture_names:
        svg = (Path("test") / name).read_text(encoding="utf-8")

        assert 'data-role="region"' not in svg
        assert "id=\"region_" not in svg
        assert "data-region=" not in svg


def test_svg_loader_preserves_rotated_rect_points_and_orientation():
    """SVG transforms should become neutral rotated geometry, not only moved centers."""
    scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    objects = {obj["id"]: obj for obj in scene["objects"]}

    sofa = objects["center_sofa_upper"]

    assert round(sofa["orientation"], 4) == 90.0
    assert len(sofa["points"]) == 5
    assert sofa["rect"].width > 50
    assert sofa["rect"].height > 140


def test_svg_id_fixtures_infer_regions_and_gap_paths_without_manual_markers():
    """The current framework should infer structure after manual region/path marks are removed."""
    fixture_names = ["SVG_baseline.svg", "SVG_chaoticsvg.svg", "SVG_oblique.svg"]
    for path in [Path("test") / name for name in fixture_names]:
        scene = load_structured_svg_scene(path)
        evidence = infer_scene_evidence(scene)

        assert scene["regions"] == []
        assert scene["paths"] == []
        assert len(evidence["furniture_groups"]) >= 5
        assert len(evidence["inferred_region_candidates"]) >= 5
        assert evidence["inferred_region_gap_paths"]
        assert any(
            network["scope"] == "inter_region" and network["edges"]
            for network in evidence["spatial_networks"]
        )


def test_inference_exposes_canonical_furniture_groups_without_legacy_group_api():
    """Runtime inference should expose one canonical furniture-group system."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    evidence = infer_scene_evidence(scene)

    assert "furniture_groups" in evidence
    assert "activity_" + "groups" not in evidence
    assert len(evidence["furniture_groups"]) >= 5
    group = {
        item["id"]: item
        for item in evidence["furniture_groups"]
    }["furniture_group_center_lounge"]
    assert group["metadata"]["level"] == "furniture_group"
    assert group["activity_region_id"] == "center_lounge"
    assert group["member_ids"]
    assert group["furniture_affordance_extent_ids"]
    assert "group-axis-angle" in group["metadata"]


def test_svg_group_only_fixture_infers_regions_without_region_labels():
    """Furniture groups should be enough to infer activity regions."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    for obj in scene["objects"]:
        # Simulate a BIM/SVG base map that provides furniture group ids but no
        # final activity-region assignment.
        obj["region"] = "global"
        obj["metadata"]["region"] = "global"

    evidence = infer_scene_evidence(scene)
    candidate_regions = {
        candidate["region"]
        for candidate in evidence["inferred_region_candidates"]
    }

    assert scene["regions"] == []
    assert {
        "north_tables",
        "west_lounge",
        "center_lounge",
        "east_armchairs",
        "east_work",
    } <= candidate_regions
    assert len(evidence["furniture_groups"]) >= 5
    assert evidence["inferred_region_gap_paths"]


def test_inferred_oblique_region_keeps_member_frame_without_correction():
    """Inferred regions should use member trend while keeping shape diagnostics."""
    scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    evidence = infer_scene_evidence(scene)
    groups = {
        group["region"]: group
        for group in evidence["furniture_groups"]
    }
    candidates = {
        candidate["region"]: candidate
        for candidate in evidence["inferred_region_candidates"]
    }

    group = groups["center_lounge"]
    center = candidates["center_lounge"]

    assert group["metadata"]["group-axis-basis"] == "member_frame_consensus"
    assert float(group["metadata"]["group-axis-geometry-angle"]) > 0.0
    assert float(group["metadata"]["group-axis-primary-extent"]) > 150.0
    assert len(center["points"]) >= 5
    assert center["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert center["metadata"]["axis-group-ids"] == "furniture_group_center_lounge"
    assert center["metadata"]["region-shape-basis"] in {
        "oriented_rectangle",
        "regularized_convex_hull",
    }
    assert center["metadata"]["shape-axis-basis"] == "region_polygon_pca"
    assert float(center["metadata"]["axis-strength"]) > 0.0
    assert float(center["metadata"]["axis-primary-extent"]) > 150.0
    assert float(center["metadata"]["axis-secondary-extent"]) > 100.0
    assert 0.0 <= float(center["metadata"]["axis-angle"]) <= 20.0


def test_west_lounge_member_frame_trend_ignores_semienclosed_pca_diagonal():
    """Semienclosed lounge trend should correct a false PCA diagonal."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    evidence = infer_scene_evidence(scene)
    candidates = {
        candidate["region"]: candidate
        for candidate in evidence["inferred_region_candidates"]
    }

    west = candidates["west_lounge"]

    assert west["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert float(west["metadata"]["axis-member-alignment"]) > 0.95
    assert float(west["metadata"]["axis-angle"]) <= 5.0
    assert float(west["metadata"]["shape-axis-angle"]) > 40.0


def test_oblique_west_lounge_corrects_to_rotated_rectangular_frame():
    """Rotated semienclosed lounge should keep its rotated rectangular frame."""
    scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    evidence = infer_scene_evidence(scene)
    candidates = {
        candidate["region"]: candidate
        for candidate in evidence["inferred_region_candidates"]
    }

    west = candidates["west_lounge"]

    assert west["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert 15.0 <= float(west["metadata"]["axis-angle"]) <= 20.0
    assert float(west["metadata"]["shape-axis-angle"]) > 70.0


def test_member_frame_trend_drives_rotated_east_work_fixture():
    """Rotated directional furniture should drive trend instead of bbox PCA."""
    scene = load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg"))
    evidence = infer_scene_evidence(scene)
    groups = {
        group["region"]: group
        for group in evidence["furniture_groups"]
    }

    east_work = groups["east_work"]

    assert east_work["metadata"]["group-axis-basis"] == "member_frame_consensus"
    assert float(east_work["metadata"]["group-axis-strength"]) > 0.95
    assert 60.0 <= float(east_work["metadata"]["group-axis-angle"]) <= 70.0


def test_single_directional_table_has_strong_member_frame_trend():
    """A single clear furniture frame should be strong even without repetition."""
    from features.scene_evaluator import evaluate_scene
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_single_directional_table",
        "size": (400.0, 300.0),
        "objects": [
            {
                "id": "single_table",
                "role": "table",
                "group": "single_work",
                "region": "single_work",
                "rect": Rect(cx=200.0, cy=150.0, width=120.0, height=40.0),
                "points": [],
                "orientation": 30.0,
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {"role": "table", "region": "single_work"},
            }
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    region = {
        candidate["region"]: candidate
        for candidate in matrix["inferred_region_candidates"]
    }["single_work"]

    assert region["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert float(region["metadata"]["axis-strength"]) > 0.95
    assert 29.0 <= float(region["metadata"]["axis-angle"]) <= 31.0


def test_horizontal_and_vertical_groups_have_clear_pca_frames():
    """Furniture-group frame clarity should not punish horizontal versus vertical layout."""
    from features.scene_evaluator import evaluate_scene
    from features.affordance.models import Rect

    def record(record_id, region, cx, cy, width, height):
        return {
            "id": record_id,
            "role": "table",
            "group": region,
            "region": region,
            "rect": Rect(cx=cx, cy=cy, width=width, height=height),
            "points": [],
            "orientation": 0.0,
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": "table", "region": region},
        }

    scene = {
        "source": "synthetic_pca_frame_equivalence",
        "size": (600.0, 600.0),
        "objects": [
            record("h1", "horizontal", 120, 120, 80, 30),
            record("h2", "horizontal", 240, 120, 80, 30),
            record("h3", "horizontal", 360, 120, 80, 30),
            record("v1", "vertical", 120, 300, 30, 80),
            record("v2", "vertical", 120, 420, 30, 80),
            record("v3", "vertical", 120, 540, 30, 80),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    candidates = {
        candidate["region"]: candidate
        for candidate in matrix["inferred_region_candidates"]
    }

    assert candidates["horizontal"]["metadata"]["axis-basis"] == (
        "furniture_group_frame_mean"
    )
    assert candidates["vertical"]["metadata"]["axis-basis"] == (
        "furniture_group_frame_mean"
    )
    assert float(candidates["horizontal"]["metadata"]["axis-strength"]) > 0.8
    assert float(candidates["vertical"]["metadata"]["axis-strength"]) > 0.8


def test_chaotic_probe_has_weaker_north_table_trend_than_baseline():
    """Trend strength should drop when members in the same region are less aligned."""
    baseline = infer_scene_evidence(
        load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    )
    chaotic = infer_scene_evidence(
        load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg"))
    )
    baseline_north = {
        candidate["region"]: candidate
        for candidate in baseline["inferred_region_candidates"]
    }["north_tables"]
    chaotic_north = {
        candidate["region"]: candidate
        for candidate in chaotic["inferred_region_candidates"]
    }["north_tables"]

    assert float(baseline_north["metadata"]["axis-strength"]) > float(
        chaotic_north["metadata"]["axis-strength"]
    )


def test_load_structured_svg_scene_normalizes_adapter_references(tmp_path):
    svg = tmp_path / "adapter_refs.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect id="wall" data-role="boundary" data-boundary-kind="wall"
        data-rhino-guid="rhino-1" data-ifc-guid="ifc-1"
        data-visualarq-id="va-1" data-source-layer="A-WALL"
        x="10" y="20" width="30" height="40" />
</svg>""",
        encoding="utf-8",
    )

    scene = load_structured_svg_scene(svg)

    assert scene["boundaries"][0]["adapter_refs"] == {
        "rhino_guid": "rhino-1",
        "ifc_guid": "ifc-1",
        "visualarq_id": "va-1",
        "source_layer": "A-WALL",
    }


def test_structured_svg_can_drive_affordance_based_region_inference(tmp_path):
    from features.affordance.models import Rect

    svg = tmp_path / "affordance_regions.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <g id="left_group" data-group="left" data-region="left">
    <rect id="left_table" data-role="table" x="20" y="20" width="60" height="30" />
    <rect id="left_chair" data-role="chair" data-affordance-bottom="20"
          x="35" y="60" width="30" height="25" />
  </g>
  <g id="right_group" data-group="right" data-region="right">
    <rect id="right_table" data-role="table" x="160" y="20" width="60" height="30" />
    <rect id="right_chair" data-role="chair" data-affordance-bottom="20"
          x="175" y="60" width="30" height="25" />
  </g>
</svg>""",
        encoding="utf-8",
    )

    matrix = evaluate_scene(load_structured_svg_scene(svg))

    inferred = {region["region"]: region for region in matrix["inferred_regions"]}
    assert inferred["left"]["rect"] == Rect(cx=50.0, cy=60.0, width=100.0, height=120.0)
    assert inferred["left"]["metadata"]["spacing_margin"] == "21.25"
    assert inferred["right"]["rect"] == Rect(cx=190.0, cy=60.0, width=100.0, height=120.0)
    assert inferred["right"]["metadata"]["spacing_margin"] == "21.25"
    assert matrix["inferred_region_gap_paths"][0]["rect"] == Rect(
        cx=120.0,
        cy=60.0,
        width=40.0,
        height=120.0,
    )


def test_svg_affordance_baker_writes_profile_values_as_explicit_metadata(tmp_path):
    from features.svg_affordance_baker import bake_svg_affordance_metadata

    source = tmp_path / "source.svg"
    target = tmp_path / "baked.svg"
    source.write_text(
        """<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg">
  <rect id="chair" data-role="chair" x="10" y="10" width="20" height="20" />
  <rect id="table" data-role="table" data-affordance-bottom="12" x="50" y="10" width="40" height="20" />
</svg>""",
        encoding="utf-8",
    )

    bake_svg_affordance_metadata(source, target)
    baked = target.read_text(encoding="utf-8")

    assert 'data-affordance-front="40"' in baked
    assert 'data-affordance-bottom="12"' in baked
    assert 'data-affordance-top="60"' not in baked


def test_loader_exports_public_api():
    import features

    assert hasattr(features, "load_structured_svg_scene")
    assert hasattr(features, "export_adapter_payload_json")
    assert hasattr(features, "validate_adapter_payload_json")


from features.scene_evaluator import (
    evaluate_scene,
    export_adapter_payload_json,
    scene_metric_overlay_svg,
    validate_adapter_payload_json,
)


def test_export_adapter_payload_json_writes_stable_handoff_file(tmp_path):
    scene = load_structured_svg_scene(FIXTURE)
    target = tmp_path / "adapter_payload.json"

    payload = export_adapter_payload_json(scene, target)
    written = json.loads(target.read_text(encoding="utf-8"))

    assert payload["source"] == str(FIXTURE)
    assert written["source"] == str(FIXTURE)
    assert written["record_count"] == 46
    assert written["handoff_contract"] == {
        "id": "neutral_adapter_payload",
        "version": 1,
    }
    assert written["adapter_capability_matrix"]["ready_handoffs"] == [
        "host_relationships",
        "route_topology_handoff",
        "visual_analysis_handoff",
        "material_calibration_handoff",
        "column_grid_handoff",
    ]
    assert written["notebook_audit_manifest"]["status"] == "ordered_clean_overlay"


def test_validate_adapter_payload_json_reports_handoff_contract(tmp_path):
    scene = load_structured_svg_scene(FIXTURE)
    target = tmp_path / "adapter_payload.json"
    export_adapter_payload_json(scene, target)

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": True,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 46,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
    }


def test_validate_adapter_payload_json_rejects_incomplete_handoff_contract(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
                {
                    "scene_records": [],
                    "external_refs": {},
                    "metric_rows": [],
                    "score_matrix": {},
                    "evidence_geometry": {},
                    "adapter_capability_matrix": {"ready_handoffs": []},
                    "notebook_audit_manifest": {"status": "draft"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": ["handoff_contract", "grasshopper_branches"],
        "contract_id": None,
        "contract_version": None,
        "record_count": 0,
        "ready_handoff_count": 0,
        "notebook_status": "draft",
        "contract_errors": [
            "handoff_contract is missing",
            "adapter_capability_matrix.ready_handoffs is empty",
            "notebook_audit_manifest.status is not ordered_clean_overlay",
        ],
    }


def test_validate_adapter_payload_json_rejects_unsupported_contract(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
                {
                    "handoff_contract": {"id": "legacy_adapter_payload", "version": 99},
                    "scene_records": [],
                    "external_refs": {},
                    "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                    "metric_rows": [],
                    "score_matrix": {},
                    "evidence_geometry": {},
                    "adapter_capability_matrix": {
                        "ready_handoffs": ["host_relationships"]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "legacy_adapter_payload",
        "contract_version": 99,
        "record_count": 0,
        "ready_handoff_count": 1,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": [
            "handoff_contract is not neutral_adapter_payload version 1"
        ],
    }


def test_validate_adapter_payload_json_rejects_partial_ready_handoffs(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "scene_records": [],
                "external_refs": {},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": ["host_relationships"]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 0,
        "ready_handoff_count": 1,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": [
            "adapter_capability_matrix.ready_handoffs missing: column_grid_handoff, material_calibration_handoff, route_topology_handoff, visual_analysis_handoff"
        ],
    }


def test_validate_adapter_payload_json_rejects_incomplete_grasshopper_branch_groups(
    tmp_path,
):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 1,
                "scene_records": [{"id": "table"}],
                "external_refs": {},
                "grasshopper_branches": [
                    {
                        "path": "{0;objects;0}",
                        "kind": "object_record",
                        "id": "table",
                        "role": "table",
                    }
                ],
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 1,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": [
            "grasshopper_branches missing branch groups: graphs, metrics"
        ],
    }


def test_validate_adapter_payload_json_rejects_record_count_mismatch(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 2,
                "scene_records": [{"id": "only_record"}],
                "external_refs": {},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 2,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": ["record_count does not match scene_records length"],
    }


def test_validate_adapter_payload_json_rejects_duplicate_scene_record_ids(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 2,
                "scene_records": [{"id": "dup"}, {"id": "dup"}],
                "external_refs": {},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 2,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": ["scene_records duplicate ids: dup"],
    }


def test_validate_adapter_payload_json_rejects_orphan_external_refs(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 1,
                "scene_records": [{"id": "real_record"}],
                "external_refs": {"rhino_guid": {"rhino-missing": "missing_record"}},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 1,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": ["external_refs target ids missing: missing_record"],
    }


def test_validate_adapter_payload_json_rejects_missing_reverse_external_refs(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 1,
                "scene_records": [
                    {
                        "id": "real_record",
                        "adapter_refs": {"rhino_guid": "rhino-real"},
                    }
                ],
                "external_refs": {},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 1,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": [
            "external_refs missing reverse refs: rhino_guid:rhino-real->real_record"
        ],
    }


def test_validate_adapter_payload_json_rejects_stale_reverse_external_refs(tmp_path):
    target = tmp_path / "adapter_payload.json"
    target.write_text(
        json.dumps(
            {
                "handoff_contract": {
                    "id": "neutral_adapter_payload",
                    "version": 1,
                },
                "record_count": 1,
                "scene_records": [
                    {
                        "id": "real_record",
                        "adapter_refs": {"rhino_guid": "rhino-real"},
                    }
                ],
                "external_refs": {"rhino_guid": {"rhino-stale": "real_record"}},
                "grasshopper_branches": VALID_GRASSHOPPER_BRANCHES,
                "metric_rows": [],
                "score_matrix": {},
                "evidence_geometry": {},
                "adapter_capability_matrix": {
                    "ready_handoffs": [
                        "host_relationships",
                        "route_topology_handoff",
                        "visual_analysis_handoff",
                        "material_calibration_handoff",
                        "column_grid_handoff",
                    ]
                },
                "notebook_audit_manifest": {"status": "ordered_clean_overlay"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_adapter_payload_json(target)

    assert result == {
        "valid": False,
        "missing_keys": [],
        "contract_id": "neutral_adapter_payload",
        "contract_version": 1,
        "record_count": 1,
        "ready_handoff_count": 5,
        "notebook_status": "ordered_clean_overlay",
        "contract_errors": [
            "external_refs stale reverse refs: rhino_guid:rhino-stale->real_record",
            "external_refs missing reverse refs: rhino_guid:rhino-real->real_record",
        ],
    }


def test_evaluate_scene_reports_adapter_reference_coverage():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, adapter_refs=None, metadata=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": dict(metadata or {}),
            "adapter_refs": dict(adapter_refs or {}),
        }

    scene = {
        "source": "synthetic_adapter_refs",
        "size": (100.0, 100.0),
        "objects": [
            record(
                "table",
                "table",
                Rect(cx=25, cy=25, width=20, height=20),
                adapter_refs={"rhino_guid": "rhino-table"},
            )
        ],
        "boundaries": [
            record("wall", "boundary", Rect(cx=50, cy=0, width=100, height=0)),
        ],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    row = [
        row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "adapter_readiness"
        and row["metric"] == "adapter_reference_coverage"
    ][0]

    assert row == {
        "view_id": "adapter_readiness",
        "metric": "adapter_reference_coverage",
        "score": 0.5,
        "status": "computed",
        "method": "records_with_external_adapter_refs_over_scene_records",
        "evidence": ["table"],
        "adapter_reference_evidence": [
            {
                "id": "table",
                "role": "table",
                "adapter_refs": {"rhino_guid": "rhino-table"},
            }
        ],
        "adapter_reference_role_coverage": {
            "boundary": {
                "record_count": 1,
                "referenced_count": 0,
                "coverage": 0.0,
                "evidence": [],
                "missing_ids": ["wall"],
            },
            "table": {
                "record_count": 1,
                "referenced_count": 1,
                "coverage": 1.0,
                "evidence": ["table"],
                "missing_ids": [],
            },
        },
        "record_count": 2,
        "uncertainty": "adapter refs are traceability metadata only; they do not prove live Rhino/BIM topology",
    }


def test_evaluate_scene_exports_neutral_adapter_payload():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, adapter_refs=None, metadata=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": dict(metadata or {}),
            "adapter_refs": dict(adapter_refs or {}),
        }

    scene = {
        "source": "synthetic_adapter_payload",
        "size": (100.0, 100.0),
        "objects": [
            record(
                "table",
                "table",
                Rect(cx=25, cy=25, width=20, height=20),
                adapter_refs={"rhino_guid": "rhino-table"},
            )
        ],
        "boundaries": [
            record(
                "wall",
                "boundary",
                Rect(cx=50, cy=0, width=100, height=0),
                adapter_refs={"ifc_guid": "ifc-wall"},
            ),
            record(
                "glass",
                "boundary",
                Rect(cx=70, cy=50, width=0, height=80),
                metadata={"boundary-kind": "glass"},
            ),
            record(
                "rug",
                "boundary",
                Rect(cx=50, cy=70, width=30, height=20),
                metadata={"boundary-kind": "rug"},
            ),
            record(
                "material",
                "boundary",
                Rect(cx=50, cy=80, width=30, height=0),
                metadata={"boundary-kind": "material"},
            ),
            record(
                "visual",
                "boundary",
                Rect(cx=20, cy=80, width=10, height=0),
                metadata={"boundary-kind": "visual"},
            ),
        ],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    payload = evaluate_scene(scene)["adapter_payload"]

    assert payload["source"] == "synthetic_adapter_payload"
    assert payload["record_count"] == 6
    assert payload["external_refs"] == {
        "ifc_guid": {"ifc-wall": "wall"},
        "rhino_guid": {"rhino-table": "table"},
    }
    assert payload["scene_records"] == [
        {
            "id": "table",
            "role": "table",
            "group": "global",
            "region": "room",
            "bbox": (15.0, 15.0, 35.0, 35.0),
            "adapter_refs": {"rhino_guid": "rhino-table"},
        },
        {
            "id": "wall",
            "role": "boundary",
            "group": "global",
            "region": "room",
            "bbox": (0.0, 0.0, 100.0, 0.0),
            "adapter_refs": {"ifc_guid": "ifc-wall"},
        },
        {
            "id": "glass",
            "role": "boundary",
            "group": "global",
            "region": "room",
            "bbox": (70.0, 10.0, 70.0, 90.0),
            "adapter_refs": {},
            "metadata": {"boundary-kind": "glass"},
        },
        {
            "id": "rug",
            "role": "boundary",
            "group": "global",
            "region": "room",
            "bbox": (35.0, 60.0, 65.0, 80.0),
            "adapter_refs": {},
            "metadata": {"boundary-kind": "rug"},
        },
        {
            "id": "material",
            "role": "boundary",
            "group": "global",
            "region": "room",
            "bbox": (35.0, 80.0, 65.0, 80.0),
            "adapter_refs": {},
            "metadata": {"boundary-kind": "material"},
        },
        {
            "id": "visual",
            "role": "boundary",
            "group": "global",
            "region": "room",
            "bbox": (15.0, 80.0, 25.0, 80.0),
            "adapter_refs": {},
            "metadata": {"boundary-kind": "visual"},
        },
    ]
    assert {
        "view_id": "adapter_readiness",
        "metric": "adapter_reference_coverage",
        "score": 0.3333,
        "status": "computed",
    } in payload["metric_rows"]
    assert payload["graph_namespaces"] == {
        "walk_graph": {
            "method": "boundary_weighted_bbox_touch_graph_proxy",
            "node_count": 0,
            "edge_count": 0,
            "metrics": {
                "entry_region_reachability": 0.0,
                "component_count": 0,
                "loop_count": 0,
                "loop_ratio": 0.0,
            },
            "uncertainty": "bbox-touch modal graph for adapter handoff; not navmesh, hosted topology, or route certification",
        },
        "visibility_graph": {
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "node_count": 0,
            "edge_count": 0,
            "metrics": {
                "visible_edge_ratio": 0.0,
                "blocked_edge_ratio": 0.0,
                "blocking_boundary_count": 0,
            },
            "uncertainty": "centerline visibility graph for adapter handoff; not full VGA, isovist field, or calibrated visual integration",
        },
    }
    assert payload["grasshopper_branches"][:2] == [
        {
            "path": "{0;objects;0}",
            "kind": "object_record",
            "id": "table",
            "role": "table",
        },
        {
            "path": "{0;boundaries;0}",
            "kind": "boundary_record",
            "id": "wall",
            "role": "boundary",
        },
    ]
    assert any(
        branch["path"].startswith("{0;metrics;")
        and branch["kind"] == "metric_row"
        and branch["id"] == "adapter_readiness.adapter_reference_coverage"
        for branch in payload["grasshopper_branches"]
    )
    assert {
        "path": "{0;graphs;walk_graph}",
        "kind": "graph_namespace",
        "id": "walk_graph",
    } in payload["grasshopper_branches"]
    assert {
        "path": "{0;graphs;visibility_graph}",
        "kind": "graph_namespace",
        "id": "visibility_graph",
    } in payload["grasshopper_branches"]
    assert payload["adapter_targets"] == {
        "table": {
            "neutral_target": "FurnitureObject",
            "rhino_target": "ClosedCurve|Brep",
            "grasshopper_branch": "{0;objects;0}",
            "bim_target": "Furniture",
        },
        "wall": {
            "neutral_target": "Boundary",
            "rhino_target": "Curve|Brep",
            "grasshopper_branch": "{0;boundaries;0}",
            "bim_target": "Wall",
        },
        "glass": {
            "neutral_target": "GlassBoundary",
            "rhino_target": "Curve|Brep|GlassMaterial",
            "grasshopper_branch": "{0;boundaries;1}",
            "bim_target": "CurtainWall|Window",
        },
        "rug": {
            "neutral_target": "BoundaryCue",
            "rhino_target": "Curve|Hatch|Surface",
            "grasshopper_branch": "{0;boundaries;2}",
            "bim_target": "SurfaceFinish|Annotation",
        },
        "material": {
            "neutral_target": "BoundaryCue",
            "rhino_target": "Curve|Hatch|Surface",
            "grasshopper_branch": "{0;boundaries;3}",
            "bim_target": "SurfaceFinish|Annotation",
        },
        "visual": {
            "neutral_target": "VisualBoundaryCue",
            "rhino_target": "Curve|Annotation",
            "grasshopper_branch": "{0;boundaries;4}",
            "bim_target": "Annotation|ZoneBoundary",
        },
    }


def test_adapter_payload_exports_proxy_geometry_evidence():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
            "adapter_refs": {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_adapter_payload_geometry",
        "size": (100.0, 100.0),
        "objects": [record("center_table", "table", Rect(cx=50, cy=50, width=20, height=20))],
        "boundaries": [room],
        "entries": [record("entry", "opening", Rect(cx=0, cy=50, width=0, height=40))],
        "paths": [record("path", "path", Rect(cx=50, cy=50, width=100, height=100))],
        "regions": [record("region", "region", Rect(cx=20, cy=50, width=20, height=20))],
        "column_axes": [],
        "uncertainties": [],
    }

    payload = evaluate_scene(scene)["adapter_payload"]
    geometry = payload["evidence_geometry"]

    assert geometry["free_space_polygons"] == {
        "method": "room_polygon_rect_cell_free_space_polygons_proxy",
        "count": 8,
        "items": [
            {
                "id": "component_0_cell_0",
                "component_index": 0,
                "cell_index": 0,
                "points": ((0, 0), (40, 0), (40, 40), (0, 40)),
                "area": 1600.0,
            },
            {
                "id": "component_0_cell_1",
                "component_index": 0,
                "cell_index": 1,
                "points": ((0, 40), (40, 40), (40, 60), (0, 60)),
                "area": 800.0,
            },
            {
                "id": "component_0_cell_2",
                "component_index": 0,
                "cell_index": 2,
                "points": ((0, 60), (40, 60), (40, 100), (0, 100)),
                "area": 1600.0,
            },
        ],
    }
    assert geometry["room_minus_blocker_polygons"] == {
        "method": "rect_cell_room_minus_blocker_boundary_union_proxy",
        "count": 1,
        "items": [
            {
                "component_index": 0,
                "outer_ring": ((0, 0), (100, 0), (100, 100), (0, 100)),
                "holes": (((40, 40), (40, 60), (60, 60), (60, 40)),),
                "area": 9600.0,
                "cell_count": 8,
            }
        ],
    }
    assert geometry["cad_room_minus_blocker_polygons"] == {
        "method": "shapely_room_polygon_difference_blocker_union",
        "count": 1,
        "items": [
            {
                "component_index": 0,
                "outer_ring": ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)),
                "holes": (((40.0, 40.0), (40.0, 60.0), (60.0, 60.0), (60.0, 40.0)),),
                "area": 9600.0,
                "source": "shapely_difference",
            }
        ],
    }
    assert geometry["cad_room_minus_blocker_component_touch_evidence"] == {
        "method": "shapely_component_entry_region_touch_proxy",
        "items": [
            {
                "component_index": 0,
                "entry_ids": ["entry"],
                "region_ids": ["region"],
                "region_overlap_areas": {"region": 400.0},
            }
        ],
    }
    assert geometry["cad_room_minus_blocker_entry_connected_area"] == {
        "method": "shapely_component_entry_touched_area_ratio_proxy",
        "entry_connected_component_ids": [0],
        "non_entry_connected_component_ids": [],
        "entry_connected_component_area": 9600.0,
        "non_entry_connected_component_area": 0.0,
        "cad_room_minus_blocker_area_total": 9600.0,
        "entry_connected_area_ratio": 1.0,
    }
    assert geometry["cad_room_minus_blocker_component_graph"] == {
        "method": "shapely_component_entry_region_touch_graph_proxy",
        "node_count": 3,
        "edge_count": 2,
        "nodes": [
            {
                "id": "cad_component_0",
                "kind": "cad_free_space_component",
                "ref_id": "component_0",
            },
            {
                "id": "cad_entry_entry",
                "kind": "entry",
                "ref_id": "entry",
            },
            {
                "id": "cad_region_region",
                "kind": "region",
                "ref_id": "region",
            },
        ],
        "edges": [
            {
                "id": "cad_edge_entry_component_entry_0",
                "kind": "entry_cad_component_touch",
                "a": "cad_entry_entry",
                "b": "cad_component_0",
                "refs": {"entry": "entry", "component": 0},
            },
            {
                "id": "cad_edge_component_region_0_region",
                "kind": "cad_component_region_overlap",
                "a": "cad_component_0",
                "b": "cad_region_region",
                "refs": {"component": 0, "region": "region"},
                "overlap_area": 400.0,
            },
        ],
    }
    assert geometry["negative_space_graph"] == {
        "method": "room_polygon_rect_cell_decomposition_proxy",
        "node_count": 3,
        "edge_count": 2,
        "nodes": [
            {
                "id": "node_negative_space_component_0",
                "kind": "negative_space_component",
                "ref_id": "component_0",
                "point": (50.0, 50.0),
            },
            {
                "id": "node_entry_entry",
                "kind": "entry",
                "ref_id": "entry",
                "point": (0, 50),
            },
            {
                "id": "node_region_region",
                "kind": "region",
                "ref_id": "region",
                "point": (20, 50),
            },
        ],
        "edges": [
            {
                "id": "edge_entry_negative_space_component_entry_component_0",
                "kind": "entry_negative_space_component_touch",
                "a": "node_entry_entry",
                "b": "node_negative_space_component_0",
            },
            {
                "id": "edge_negative_space_component_region_component_0_region",
                "kind": "negative_space_component_region_touch",
                "a": "node_negative_space_component_0",
                "b": "node_region_region",
            },
        ],
    }
    assert geometry["free_space_polygon_graph"]["node_count"] == 8
    assert geometry["free_space_polygon_graph"]["edge_count"] == 8
    assert (
        geometry["uncertainty"]
        == "proxy evidence geometry for adapter handoff; not CAD boolean topology, navmesh, or live Rhino/BIM geometry"
    )
    route_handoff = payload["route_topology_handoff"]
    assert route_handoff["cad_component_graph"]["items"] == {
        "nodes": geometry["cad_room_minus_blocker_component_graph"]["nodes"],
        "edges": geometry["cad_room_minus_blocker_component_graph"]["edges"],
    }
    assert route_handoff["free_space_polygon_graph"]["items"] == {
        "nodes": geometry["free_space_polygon_graph"]["nodes"],
        "edges": geometry["free_space_polygon_graph"]["edges"],
    }
    assert route_handoff == {
        "method": "adapter_route_topology_handoff_from_existing_proxy_graphs",
        "cad_component_graph": {
            "method": "shapely_component_entry_region_touch_graph_proxy",
            "node_count": 3,
            "edge_count": 2,
            "items": {
                "nodes": geometry["cad_room_minus_blocker_component_graph"]["nodes"],
                "edges": geometry["cad_room_minus_blocker_component_graph"]["edges"],
            },
        },
        "free_space_polygon_graph": {
            "method": "room_polygon_rect_cell_shared_edge_graph_proxy",
            "node_count": 8,
            "edge_count": 8,
            "items": {
                "nodes": geometry["free_space_polygon_graph"]["nodes"],
                "edges": geometry["free_space_polygon_graph"]["edges"],
            },
        },
        "inferred_gap_paths": {
            "method": "affordance_region_bbox_axis_gap_band_proxy",
            "count": len(
                payload["evidence_geometry"]["inferred_region_gap_paths"]["items"]
            ),
            "clear_count": sum(
                1
                for item in payload["evidence_geometry"]["inferred_region_gap_paths"]["items"]
                if item.get("clear_status") == "clear_proxy"
            ),
            "occupied_count": sum(
                1
                for item in payload["evidence_geometry"]["inferred_region_gap_paths"]["items"]
                if item.get("clear_status") == "occupied_proxy"
            ),
            "items": payload["evidence_geometry"]["inferred_region_gap_paths"]["items"],
        },
        "inferred_gap_path_graph": {
            "method": "inferred_gap_path_region_adjacency_graph_proxy",
            "node_count": 0,
            "edge_count": 0,
            "clear_edge_count": 0,
            "occupied_edge_count": 0,
            "free_space_supported_edge_count": 0,
            "walkable_proxy_edge_count": 0,
            "walkable_proxy_min_thickness": None,
            "walkable_proxy_mean_thickness": None,
            "component_count": 0,
            "walkable_proxy_component_count": 0,
            "walkable_proxy_components": [],
            "walkable_proxy_edges": [],
            "walkable_proxy_edge_widths": [],
            "minimum_width": 10.0,
            "minimum_width_basis": "half_sampled_grid_resolution",
            "minimum_width_evidence": ["center_table"],
            "width_pass_edge_count": 0,
            "width_fail_edge_count": 0,
            "width_pass_edges": [],
            "width_fail_edges": [],
        },
        "host_relationships": {
            "method": "entry_boundary_associations_from_host_metadata_or_nearest_geometry",
            "hosted_entry_count": 0,
            "fallback_entry_count": 1,
        },
        "uncertainty": "route topology handoff only; replace proxy graphs with navmesh, medial-axis, skeleton, or hosted BIM topology in downstream adapters",
    }


def test_adapter_payload_exports_inferred_region_geometry_evidence():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_adapter_payload_inferred_regions",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    geometry = evaluate_scene(scene)["adapter_payload"]["evidence_geometry"]

    assert geometry["inferred_region_candidates"] == {
        "count": 2,
        "items": [
            {
                "id": "inferred_region_left",
                "region": "left",
                "bbox": (10.0, 20.0, 130.0, 140.0),
                "geometry_basis": "object_footprints_plus_affordance_zone_rects",
                "member_ids": ["left_table"],
                "affordance_zone_ids": [],
                "boundary_cue_ids": [],
                "spacing_side_margins": {
                    "left": 20.0,
                    "right": 20.0,
                    "top": 20.0,
                    "bottom": 20.0,
                },
            },
            {
                "id": "inferred_region_right",
                "region": "right",
                "bbox": (230.0, 20.0, 350.0, 140.0),
                "geometry_basis": "object_footprints_plus_affordance_zone_rects",
                "member_ids": ["right_table"],
                "affordance_zone_ids": [],
                "boundary_cue_ids": [],
                "spacing_side_margins": {
                    "left": 20.0,
                    "right": 20.0,
                    "top": 20.0,
                    "bottom": 20.0,
                },
            },
        ],
    }
    assert geometry["inferred_region_gap_paths"] == {
        "count": 1,
        "items": [
            {
                "id": "inferred_gap_path_left__right",
                "region_a": "inferred_region_left",
                "region_b": "inferred_region_right",
                "orientation": "vertical",
                "bbox": (130.0, 20.0, 230.0, 140.0),
                "thickness": 100.0,
                "overlap_span": 120.0,
                "occupied": False,
                "occupancy_ratio": 0.0,
                "occupied_area": 0,
                "clear_status": "clear_proxy",
                "free_space_overlap_ratio": 1.0,
                "free_space_overlap_area": 12000.0,
            }
        ],
    }


def test_boundary_metrics_report_weight_metadata_coverage():
    from features.affordance.models import Rect

    def record(record_id, *, metadata, weights):
        return {
            "id": record_id,
            "role": "boundary",
            "group": "global",
            "region": "room",
            "rect": Rect(cx=50, cy=50, width=100, height=10),
            "points": [],
            "weights": weights,
            "metadata": metadata,
            "adapter_refs": {},
        }

    scene = {
        "source": "synthetic_weight_metadata_coverage",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "authored_glass",
                metadata={
                    "boundary-kind": "glass",
                    "walk-block": "1.0",
                    "see-block": "0.15",
                    "grouping-strength": "0.9",
                },
                weights={
                    "walk_block": 1.0,
                    "see_block": 0.15,
                    "grouping_strength": 0.9,
                },
            ),
            record(
                "default_wall",
                metadata={"boundary-kind": "wall"},
                weights={
                    "walk_block": 1.0,
                    "see_block": 1.0,
                    "grouping_strength": 1.0,
                },
            ),
        ],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    row = [
        row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "boundary_metrics"
        and row["metric"] == "boundary_weight_metadata_coverage"
    ][0]

    assert row == {
        "view_id": "boundary_metrics",
        "metric": "boundary_weight_metadata_coverage",
        "score": 0.5,
        "status": "computed",
        "method": "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records",
        "evidence": ["authored_glass"],
        "weight_metadata_evidence": [
            {
                "id": "authored_glass",
                "role": "boundary",
                "kind": "glass",
                "explicit_channels": [
                    "grouping_strength",
                    "see_block",
                    "walk_block",
                ],
                "missing_channels": [],
                "has_complete_weight_metadata": True,
            },
            {
                "id": "default_wall",
                "role": "boundary",
                "kind": "wall",
                "explicit_channels": [],
                "missing_channels": [
                    "grouping_strength",
                    "see_block",
                    "walk_block",
                ],
                "has_complete_weight_metadata": False,
            },
        ],
        "missing_weight_metadata_ids": ["default_wall"],
        "uncertainty": "explicit weight metadata coverage only; authored weights are not material or perception calibration",
    }


def test_region_membership_coverage_scores_objects_against_authored_and_inferred_regions():
    from features.affordance.models import Rect

    def record(record_id, role, region, rect):
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": region},
        }

    scene = {
        "source": "synthetic_region_membership",
        "size": (300.0, 100.0),
        "objects": [
            record("inside_table", "table", "zone_a", Rect(cx=25, cy=25, width=50, height=50)),
            record("half_table", "table", "zone_a", Rect(cx=100, cy=25, width=100, height=50)),
            record("missing_region_table", "table", "zone_missing", Rect(cx=250, cy=25, width=50, height=50)),
        ],
        "regions": [
            record("region_zone_a", "region", "zone_a", Rect(cx=50, cy=25, width=100, height=50)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "object_region_membership_coverage"
    ][0]

    assert row["score"] == 0.8333
    assert row["method"] == "object_region_rect_or_polygon_overlap_area_ratio"
    assert row["object_region_membership_evidence"] == [
        {
            "object_id": "inside_table",
            "region_id": "region_zone_a",
            "overlap_area": 2500,
            "object_area": 2500,
            "score": 1.0,
        },
        {
            "object_id": "half_table",
            "region_id": "region_zone_a",
            "overlap_area": 2500.0,
            "object_area": 5000,
            "score": 0.5,
        },
        {
            "object_id": "missing_region_table",
            "region_id": "inferred_region_zone_missing",
            "overlap_area": 2500,
            "object_area": 2500,
            "score": 1.0,
        },
    ]
    assert row["missing_region_evidence"] == []
    assignment = [
        row
        for row in matrix["rows"]
        if row["metric"] == "object_region_assignment_coverage"
    ][0]
    assert assignment["score"] == 1.0
    assert assignment["method"] == "objects_with_matching_region_records_ratio"
    assert assignment["matched_object_count"] == 3
    assert assignment["total_object_count"] == 3
    assert assignment["missing_region_evidence"] == []


def test_evaluate_scene_infers_regions_from_affordance_expanded_group_bounds():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None, region=None):
        metadata = {"role": role, "region": group}
        if affordance:
            metadata.update(
                {
                    "affordance-left": str(affordance.get("left", 0.0)),
                    "affordance-right": str(affordance.get("right", 0.0)),
                    "affordance-top": str(affordance.get("top", 0.0)),
                    "affordance-bottom": str(affordance.get("bottom", 0.0)),
                }
            )
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": region or group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_affordance_inferred_regions",
        "size": (420.0, 180.0),
        "objects": [
            record(
                "west_table",
                "table",
                "west_lounge",
                Rect(cx=70, cy=80, width=80, height=50),
            ),
            record(
                "west_chair",
                "chair",
                "west_lounge",
                Rect(cx=70, cy=135, width=40, height=30),
                affordance={"bottom": 25},
            ),
            record(
                "east_table",
                "table",
                "east_lounge",
                Rect(cx=310, cy=80, width=80, height=50),
            ),
            record(
                "east_chair",
                "chair",
                "east_lounge",
                Rect(cx=310, cy=135, width=40, height=30),
                affordance={"bottom": 25},
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    inferred = {region["region"]: region for region in matrix["inferred_regions"]}
    for region_name, expected_rect in {
        "east_lounge": Rect(cx=310.0, cy=102.5, width=140.0, height=155.0),
        "west_lounge": Rect(cx=70.0, cy=102.5, width=140.0, height=155.0),
    }.items():
        region = inferred[region_name]
        assert region["rect"] == expected_rect
        assert len(region["points"]) == 5
        assert region["metadata"]["geometry_basis"] == "object_footprints_plus_affordance_zone_rects"
        assert region["metadata"]["axis-basis"] == "furniture_group_frame_mean"
        assert region["metadata"]["spacing_margin"] == "30.0"

    inference_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_count"
    ][0]
    assert inference_row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_count",
        "score": 2,
        "status": "computed",
        "method": "affordance_zone_boundary_cue_expanded_group_bounds",
        "evidence": [
            "inferred_region_east_lounge",
            "inferred_region_west_lounge",
        ],
        "inferred_region_evidence": [
            {
                "region": "east_lounge",
                "geometry_basis": "object_footprints_plus_affordance_zone_rects",
                "member_ids": ["east_chair", "east_table"],
                "affordance_zone_ids": ["affordance_zone_east_chair_bottom"],
                "boundary_cue_ids": [],
                "spacing_side_margins": {
                    "left": 30.0,
                    "right": 30.0,
                    "top": 30.0,
                    "bottom": 5.0,
                },
                "bbox": (240.0, 25.0, 380.0, 180.0),
            },
            {
                "region": "west_lounge",
                "geometry_basis": "object_footprints_plus_affordance_zone_rects",
                "member_ids": ["west_chair", "west_table"],
                "affordance_zone_ids": ["affordance_zone_west_chair_bottom"],
                "boundary_cue_ids": [],
                "spacing_side_margins": {
                    "left": 30.0,
                    "right": 30.0,
                    "top": 30.0,
                    "bottom": 5.0,
                },
                "bbox": (0.0, 25.0, 140.0, 180.0),
            },
        ],
        "uncertainty": "candidate regions inferred from furniture footprint, affordance extents, and same-region boundary cues; bbox proxy, not alpha-shape or perception-calibrated region discovery",
    }

    membership = [
        row
        for row in matrix["rows"]
        if row["metric"] == "object_region_membership_coverage"
    ][0]
    assert membership["score"] == 1.0
    assert membership["missing_region_evidence"] == []


def test_evaluate_scene_exposes_affordance_use_zones_separate_from_footprints():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None, region=None):
        metadata = {"role": role, "region": group}
        if affordance:
            for side, value in affordance.items():
                metadata[f"affordance-{side}"] = str(value)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": region or group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_affordance_use_zones",
        "size": (160.0, 180.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=80, cy=115, width=40, height=30),
                affordance={"bottom": 25},
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "affordance_use_zone_count"
    ][0]

    assert matrix["affordance_zones"] == [
        {
            "id": "affordance_zone_chair_bottom",
            "object_id": "chair",
            "region": "lounge",
            "side": "bottom",
            "depth": 25.0,
            "source": "explicit_affordance_metadata",
            "rect": Rect(cx=80.0, cy=142.5, width=40.0, height=25.0),
            "footprint_rect": Rect(cx=80, cy=115, width=40, height=30),
        }
    ]
    candidate = matrix["inferred_region_candidates"][0]
    assert candidate["metadata"]["affordance_zone_ids"] == "affordance_zone_chair_bottom"
    assert candidate["metadata"]["source"] == "affordance_zone_boundary_cue_expanded_group_bounds"
    assert candidate["metadata"]["geometry_basis"] == "object_footprints_plus_affordance_zone_rects"
    assert row == {
        "view_id": "region_alignment",
        "metric": "affordance_use_zone_count",
        "score": 1,
        "status": "computed",
        "method": "object_footprint_adjacent_affordance_rect_zones",
        "evidence": ["affordance_zone_chair_bottom"],
        "affordance_use_zone_evidence": [
            {
                "id": "affordance_zone_chair_bottom",
                "object_id": "chair",
                "region": "lounge",
                "side": "bottom",
                "depth": 25.0,
                "source": "explicit_affordance_metadata",
                "zone_bbox": (60.0, 130.0, 100.0, 155.0),
                "footprint_bbox": (60, 100, 100, 130),
            }
        ],
        "uncertainty": "axis-aligned affordance use zones separate furniture footprints from occupied/use space; proxy, not posture simulation or swept human motion",
    }
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    assert geometry["affordance_zones"] == {
        "count": 1,
        "items": [
            {
                "id": "affordance_zone_chair_bottom",
                "object_id": "chair",
                "region": "lounge",
                "side": "bottom",
                "depth": 25.0,
                "source": "explicit_affordance_metadata",
                "zone_bbox": (60.0, 130.0, 100.0, 155.0),
                "footprint_bbox": (60, 100, 100, 130),
            }
        ],
    }
    svg = scene_metric_overlay_svg(scene, matrix)
    assert 'data-layer="affordance-use-zone"' in svg
    assert 'data-affordance-zone="affordance_zone_chair_bottom"' in svg
    assert 'data-object="chair"' in svg


def test_evaluate_scene_exposes_furniture_affordance_extents_to_matrix_payload_and_overlay():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None):
        metadata = {"role": role, "region": group}
        if affordance:
            metadata.update(affordance)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_furniture_extent_outputs",
        "size": (160.0, 180.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=80, cy=115, width=40, height=30),
                affordance={"affordance-bottom": "25"},
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "furniture_affordance_extent_count"
    ][0]
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    svg = scene_metric_overlay_svg(scene, matrix)

    assert matrix["furniture_affordance_extents"][0]["id"] == (
        "furniture_affordance_extent_chair"
    )
    assert row["furniture_affordance_extent_evidence"][0] == {
        "id": "furniture_affordance_extent_chair",
        "object_id": "chair",
        "region": "lounge",
        "bbox": (60.0, 100, 100.0, 155.0),
        "footprint_bbox": (60, 100, 100, 130),
        "affordance_zone_ids": ["affordance_zone_chair_bottom"],
    }
    assert geometry["furniture_affordance_extents"]["items"][0] == (
        row["furniture_affordance_extent_evidence"][0]
    )
    assert 'data-layer="furniture-affordance-extent"' in svg
    assert 'data-extent="furniture_affordance_extent_chair"' in svg
    assert 'data-object="chair"' in svg


def test_evaluate_scene_requires_explicit_affordance_for_inferred_regions():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, type_id=None, affordance_bottom=None):
        """Build one neutral scene object with optional explicit affordance input."""
        metadata = {"role": role, "region": group}
        if type_id:
            metadata["type_id"] = type_id
        if affordance_bottom is not None:
            metadata["affordance-bottom"] = str(affordance_bottom)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    base_scene = {
        "source": "synthetic_profile_affordance_inferred_region",
        "size": (180.0, 200.0),
        "objects": [
            record("table", "table", "dining", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "dining",
                Rect(cx=80, cy=115, width=40, height=30),
                type_id="chair.default",
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(base_scene)

    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=80.0,
        cy=85.0,
        width=80.0,
        height=90.0,
    )
    assert matrix["affordance_zones"] == []

    override_scene = {
        **base_scene,
        "objects": [
            base_scene["objects"][0],
            record(
                "chair",
                "chair",
                "dining",
                Rect(cx=80, cy=115, width=40, height=30),
                type_id="chair.default",
                affordance_bottom=20,
            ),
        ],
    }
    matrix = evaluate_scene(override_scene)

    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=80.0,
        cy=95.0,
        width=80.0,
        height=110.0,
    )


def test_evaluate_scene_orients_explicit_chair_affordance_for_inferred_regions():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, orientation=0.0):
        """Build one oriented object with an explicit front affordance depth."""
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {
                "role": role,
                "region": group,
                "type_id": "chair.default" if role == "chair" else "furniture.default",
                "orientation": str(orientation),
                "affordance-front": "40",
            },
        }

    scene = {
        "source": "synthetic_oriented_profile_affordance_inferred_region",
        "size": (220.0, 180.0),
        "objects": [
            record("chair", "chair", "reading", Rect(cx=80, cy=80, width=40, height=30), orientation=90),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=100.0,
        cy=80.0,
        width=80.0,
        height=30.0,
    )


def test_evaluate_scene_uses_armchair_profile_for_armchair_regions():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_armchair_profile_affordance_inferred_region",
        "size": (180.0, 180.0),
        "objects": [
            {
                "id": "armchair",
                "role": "armchair",
                "group": "reading",
                "region": "reading",
                "rect": Rect(cx=80, cy=80, width=50, height=40),
                "points": [],
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {
                    "role": "armchair",
                    "region": "reading",
                    "affordance-left": "15",
                    "affordance-right": "15",
                    "affordance-top": "15",
                    "affordance-bottom": "15",
                },
            }
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    assert [
        (zone["id"], zone["side"], zone["depth"], zone["source"])
        for zone in matrix["affordance_zones"]
    ] == [
        ("affordance_zone_armchair_left", "left", 15.0, "explicit_affordance_metadata"),
        ("affordance_zone_armchair_right", "right", 15.0, "explicit_affordance_metadata"),
        ("affordance_zone_armchair_top", "top", 15.0, "explicit_affordance_metadata"),
        ("affordance_zone_armchair_bottom", "bottom", 15.0, "explicit_affordance_metadata"),
    ]
    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=80.0,
        cy=80.0,
        width=80.0,
        height=70.0,
    )


def test_evaluate_scene_uses_podium_profile_for_work_regions():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_podium_profile_affordance_inferred_region",
        "size": (240.0, 260.0),
        "objects": [
            {
                "id": "podium",
                "role": "podium",
                "group": "work",
                "region": "work",
                "rect": Rect(cx=120, cy=120, width=100, height=50),
                "points": [],
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {
                    "role": "podium",
                    "region": "work",
                    "affordance-front": "80",
                },
            }
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    assert matrix["affordance_zones"] == [
        {
            "id": "affordance_zone_podium_bottom",
            "object_id": "podium",
            "region": "work",
            "side": "bottom",
            "depth": 80.0,
            "source": "explicit_affordance_metadata",
            "rect": Rect(cx=120.0, cy=185.0, width=100.0, height=80.0),
            "footprint_rect": Rect(cx=120, cy=120, width=100, height=50),
        }
    ]
    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=120.0,
        cy=160.0,
        width=100.0,
        height=130.0,
    )


def test_evaluate_scene_expands_inferred_region_with_same_region_boundary_cues():
    from features.affordance.models import Rect

    def record(record_id, role, region, rect, *, affordance_bottom=0.0, grouping_strength=0.0):
        metadata = {"role": role, "region": region}
        if affordance_bottom:
            metadata["affordance-bottom"] = str(affordance_bottom)
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": grouping_strength,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_boundary_cue_inferred_region",
        "size": (220.0, 220.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=100, cy=80, width=60, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=100, cy=130, width=40, height=30),
                affordance_bottom=20,
            ),
        ],
        "regions": [],
        "boundaries": [
            record(
                "rug_edge",
                "boundary",
                "lounge",
                Rect(cx=100, cy=105, width=120, height=140),
                grouping_strength=0.8,
            ),
            record(
                "room_edge",
                "boundary",
                "room",
                Rect(cx=110, cy=110, width=220, height=220),
                grouping_strength=1.0,
            ),
        ],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    assert matrix["inferred_regions"][0]["rect"] == Rect(
        cx=100.0,
        cy=105.0,
        width=120.0,
        height=140.0,
    )
    assert matrix["inferred_regions"][0]["metadata"]["boundary_cue_ids"] == "rug_edge"
    inference_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_count"
    ][0]
    assert inference_row["inferred_region_evidence"] == [
        {
            "region": "lounge",
            "geometry_basis": "object_footprints_plus_affordance_zone_rects",
            "member_ids": ["chair", "table"],
            "affordance_zone_ids": ["affordance_zone_chair_bottom"],
            "boundary_cue_ids": ["rug_edge"],
            "bbox": (40.0, 35.0, 160.0, 175.0),
        }
    ]


def test_evaluate_scene_adds_no_cue_spacing_margin_without_swallowing_gap_path():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_spacing_margin_inferred_regions",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    inferred = {region["region"]: region for region in matrix["inferred_regions"]}

    assert inferred["left"]["rect"] == Rect(cx=70.0, cy=80.0, width=120.0, height=120.0)
    assert inferred["left"]["metadata"]["spacing_margin"] == "20.0"
    assert inferred["left"]["metadata"]["spacing_side_margins"] == (
        "left:20.0,right:20.0,top:20.0,bottom:20.0"
    )
    assert inferred["right"]["rect"] == Rect(cx=290.0, cy=80.0, width=120.0, height=120.0)
    assert inferred["right"]["metadata"]["spacing_margin"] == "20.0"
    assert inferred["right"]["metadata"]["spacing_side_margins"] == (
        "left:20.0,right:20.0,top:20.0,bottom:20.0"
    )

    gap_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_count"
    ][0]
    assert gap_row["inferred_region_gap_path_evidence"] == [
        {
            "id": "inferred_gap_path_left__right",
            "region_a": "inferred_region_left",
            "region_b": "inferred_region_right",
            "orientation": "vertical",
            "bbox": (130.0, 20.0, 230.0, 140.0),
            "thickness": 100.0,
            "overlap_span": 120.0,
        }
    ]


def test_evaluate_scene_uses_member_spacing_margin_for_large_repeated_groups():
    from features.affordance.models import Rect

    def record(record_id, group, rect):
        return {
            "id": record_id,
            "role": "table",
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": "table", "region": group},
        }

    scene = {
        "source": "synthetic_large_repeated_group_spacing_margin",
        "size": (1000.0, 700.0),
        "objects": [
            record("r1_c1", "north_tables", Rect(cx=185, cy=215, width=150, height=56)),
            record("r1_c2", "north_tables", Rect(cx=500, cy=215, width=150, height=56)),
            record("r1_c3", "north_tables", Rect(cx=815, cy=215, width=150, height=56)),
            record("r2_c1", "north_tables", Rect(cx=185, cy=465, width=150, height=56)),
            record("r2_c2", "north_tables", Rect(cx=500, cy=465, width=150, height=56)),
            record("r2_c3", "north_tables", Rect(cx=815, cy=465, width=150, height=56)),
            record("south_table", "south", Rect(cx=950, cy=650, width=40, height=40)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    region = {item["region"]: item for item in matrix["inferred_regions"]}["north_tables"]

    assert region["metadata"]["spacing_margin"] == "41.25"
    assert region["metadata"]["spacing_side_margins"] == (
        "left:41.25,right:41.25,top:41.25,bottom:41.25"
    )
    assert region["rect"] == Rect(cx=500.0, cy=340.0, width=862.5, height=388.5)


def test_evaluate_scene_uses_oriented_rectangle_for_regular_region_shape():
    from features.affordance.models import Rect
    from features.scene_evaluator import evaluate_scene

    def record(record_id, rect):
        """Build one regular test furniture record."""
        return {
            "id": record_id,
            "role": "table",
            "group": "regular",
            "region": "regular",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": "table", "region": "regular"},
        }

    scene = {
        "source": "synthetic_regular_region_shape",
        "size": (400.0, 240.0),
        "objects": [
            record("left_table", Rect(cx=120, cy=120, width=80, height=40)),
            record("right_table", Rect(cx=240, cy=120, width=80, height=40)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    region = evaluate_scene(scene)["inferred_regions"][0]

    assert region["metadata"]["region-shape-basis"] == "oriented_rectangle"
    assert region["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert region["metadata"]["shape-axis-basis"] == "region_polygon_pca"
    assert "frame-delta" in region["metadata"]


def test_evaluate_scene_uses_regularized_hull_for_complex_region_shape():
    from features.affordance.models import Rect
    from features.scene_evaluator import evaluate_scene

    def record(record_id, rect):
        """Build one irregular test furniture record."""
        return {
            "id": record_id,
            "role": "table",
            "group": "irregular",
            "region": "irregular",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": "table", "region": "irregular"},
        }

    scene = {
        "source": "synthetic_regularized_hull_region_shape",
        "size": (500.0, 420.0),
        "objects": [
            record("a", Rect(cx=110, cy=90, width=42, height=34)),
            record("b", Rect(cx=230, cy=65, width=38, height=32)),
            record("c", Rect(cx=350, cy=130, width=44, height=30)),
            record("d", Rect(cx=380, cy=255, width=40, height=36)),
            record("e", Rect(cx=285, cy=345, width=36, height=34)),
            record("f", Rect(cx=150, cy=320, width=42, height=30)),
            record("g", Rect(cx=70, cy=210, width=38, height=36)),
            record("h", Rect(cx=170, cy=180, width=34, height=34)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    region = evaluate_scene(scene)["inferred_regions"][0]

    assert region["metadata"]["region-shape-basis"] == "regularized_convex_hull"
    assert int(region["metadata"]["region-shape-vertex-count"]) >= 8
    assert region["metadata"]["axis-basis"] == "furniture_group_frame_mean"
    assert region["metadata"]["shape-axis-basis"] == "region_polygon_pca"
    assert "shape-axis-angle" in region["metadata"]
    assert "frame-delta" in region["metadata"]


def test_evaluate_scene_excludes_decorative_objects_from_region_inference():
    from features.affordance.models import Rect
    from features.scene_evaluator import evaluate_scene

    def record(record_id, role, rect):
        """Build one test object with a role-specific inference expectation."""
        return {
            "id": record_id,
            "role": role,
            "group": "lounge",
            "region": "lounge",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": "lounge"},
        }

    scene = {
        "source": "synthetic_decorative_object_region_filter",
        "size": (360.0, 260.0),
        "objects": [
            record("sofa", "sofa", Rect(cx=120, cy=180, width=120, height=40)),
            record("table", "table", Rect(cx=120, cy=130, width=70, height=36)),
            record("plant", "plant", Rect(cx=120, cy=40, width=44, height=44)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    region = evaluate_scene(scene)["inferred_regions"][0]

    assert region["metadata"]["member_ids"] == "sofa,table"
    assert "plant" not in region["metadata"]["child_extent_ids"]
    assert region["rect"].top > 80.0


def test_evaluate_scene_allows_decorative_region_shape_anchor_override():
    from features.affordance.models import Rect
    from features.scene_evaluator import evaluate_scene

    def record(record_id, role, rect, *, anchor=False):
        """Build one test object with optional region-shape anchor metadata."""
        metadata = {"role": role, "region": "lounge"}
        if anchor:
            metadata["region-shape-anchor"] = "true"
        return {
            "id": record_id,
            "role": role,
            "group": "lounge",
            "region": "lounge",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_decorative_object_region_anchor",
        "size": (360.0, 260.0),
        "objects": [
            record("sofa", "sofa", Rect(cx=120, cy=180, width=120, height=40)),
            record("table", "table", Rect(cx=120, cy=130, width=70, height=36)),
            record("plant", "plant", Rect(cx=120, cy=40, width=44, height=44), anchor=True),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    region = evaluate_scene(scene)["inferred_regions"][0]

    assert region["metadata"]["member_ids"] == "plant,sofa,table"
    assert "furniture_affordance_extent_plant" in region["metadata"]["child_extent_ids"]
    assert region["rect"].top <= 18.0


def test_svg_baseline_center_lounge_regularized_hull_stays_rectangular():
    from features.scene_loader import load_structured_svg_scene
    from features.scene_inference import infer_scene_evidence

    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    evidence = infer_scene_evidence(scene)
    region = {
        item["region"]: item
        for item in evidence["inferred_region_candidates"]
    }["center_lounge"]

    assert region["metadata"]["region-shape-vertex-count"] == "8"
    assert region["metadata"]["region-shape-aligned-edge-ratio"] == "0.75"
    assert region["metadata"]["region-shape-basis"] == "oriented_rectangle"


def test_center_lounge_trend_metadata_separates_alignment_clarity_and_strength():
    from features.scene_loader import load_structured_svg_scene
    from features.scene_inference import infer_scene_evidence

    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    evidence = infer_scene_evidence(scene)
    region = {
        item["region"]: item
        for item in evidence["inferred_region_candidates"]
    }["center_lounge"]

    assert region["metadata"]["axis-member-alignment"] == "1.0"
    assert region["metadata"]["axis-shape-clarity"] == region["metadata"]["axis-clarity"]
    assert region["metadata"]["axis-trend-strength"] == region["metadata"]["axis-strength"]


def test_region_frame_explainability_selects_only_better_orthogonal_frames():
    """Frame diagnostics should correct only orthogonal frames that explain data better."""
    from features.scene_loader import load_structured_svg_scene
    from features.scene_inference import infer_scene_evidence

    oblique_scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    oblique_evidence = infer_scene_evidence(oblique_scene)
    oblique_regions = {
        item["region"]: item for item in oblique_evidence["inferred_region_candidates"]
    }
    center = oblique_regions["center_lounge"]
    west = oblique_regions["west_lounge"]
    north = oblique_regions["north_tables"]

    assert float(center["metadata"]["axis-angle"]) == 0.0
    assert center["metadata"]["region-shape-basis"] == "oriented_rectangle"
    assert center["metadata"]["frame-explainability-basis"] == (
        "pca_vs_nearest_orthogonal_frame"
    )
    assert center["metadata"]["frame-snap-candidate"] == "false"
    assert center["metadata"]["axis-explainability-correction"] == "none"
    assert center["metadata"]["axis-original-angle"] == "0.0"
    assert float(center["metadata"]["frame-pca-area"]) > 0.0
    assert float(center["metadata"]["frame-orthogonal-area"]) > 0.0
    assert float(center["metadata"]["frame-orthogonal-area-ratio"]) > 0.0
    assert 0.0 <= float(center["metadata"]["frame-pca-member-alignment"]) <= 1.0
    assert 0.0 <= float(center["metadata"]["frame-orthogonal-member-alignment"]) <= 1.0
    assert float(west["metadata"]["axis-angle"]) > 15.0
    assert west["metadata"]["frame-snap-candidate"] == "false"
    assert float(west["metadata"]["frame-member-alignment-ratio"]) < 0.5
    assert 80.0 <= float(north["metadata"]["axis-angle"]) <= 90.0
    assert north["metadata"]["frame-snap-candidate"] == "false"

    chaotic_scene = load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg"))
    chaotic_evidence = infer_scene_evidence(chaotic_scene)
    chaotic_regions = {
        item["region"]: item for item in chaotic_evidence["inferred_region_candidates"]
    }
    chaotic_center = chaotic_regions["center_lounge"]

    assert chaotic_center["metadata"]["frame-snap-candidate"] == "false"
    assert 80.0 <= float(chaotic_center["metadata"]["axis-angle"]) <= 90.0


def test_region_frame_extents_match_final_axis_angle():
    """Region trend extent metadata should match the final drawn frame angle."""
    from features.scene_loader import load_structured_svg_scene
    from features.scene_inference import infer_scene_evidence

    scene = load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg"))
    evidence = infer_scene_evidence(scene)
    north_tables = {
        item["region"]: item for item in evidence["inferred_region_candidates"]
    }["north_tables"]
    metadata = north_tables["metadata"]

    # A near-vertical final frame must not keep the near-horizontal PCA long
    # extent as its primary visual length.
    assert float(metadata["axis-angle"]) > 80.0
    assert float(metadata["axis-primary-extent"]) < float(
        metadata["axis-secondary-extent"]
    )


def test_evaluate_scene_clamps_spacing_margin_to_scene_bounds():
    from features.affordance.models import Rect

    def record(record_id, group, rect):
        return {
            "id": record_id,
            "role": "table",
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": "table", "region": group},
        }

    scene = {
        "source": "synthetic_spacing_margin_scene_bounds",
        "size": (200.0, 100.0),
        "objects": [
            record("left_table", "left", Rect(cx=20, cy=50, width=40, height=40)),
            record("right_table", "right", Rect(cx=160, cy=50, width=40, height=40)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    inferred = {region["region"]: region for region in matrix["inferred_regions"]}

    assert inferred["left"]["rect"].left == 0.0
    assert inferred["left"]["metadata"]["spacing_side_margins"] == (
        "left:0.0,right:10.0,top:10.0,bottom:10.0"
    )
    assert inferred["right"]["rect"].right == 190.0
    assert inferred["right"]["metadata"]["spacing_side_margins"] == (
        "left:10.0,right:10.0,top:10.0,bottom:10.0"
    )


def test_evaluate_scene_keeps_base_candidate_when_spacing_margin_worsens_explicit_iou():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_spacing_margin_iou_guard",
        "size": (240.0, 120.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=60, cy=60, width=60, height=60)),
            record("right_table", "table", "right", Rect(cx=180, cy=60, width=60, height=60)),
        ],
        "regions": [
            record("region_left", "region", "left", Rect(cx=60, cy=60, width=60, height=60)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    candidates = {region["region"]: region for region in matrix["inferred_region_candidates"]}

    assert candidates["left"]["rect"] == Rect(cx=60.0, cy=60.0, width=60.0, height=60.0)
    assert "spacing_margin" not in candidates["left"]["metadata"]
    assert candidates["right"]["rect"] == Rect(cx=180.0, cy=60.0, width=90.0, height=90.0)


def test_evaluate_scene_compares_inferred_region_candidates_to_explicit_regions():
    from features.affordance.models import Rect

    def record(record_id, role, region, rect, *, affordance_bottom=0.0):
        metadata = {"role": role, "region": region}
        if affordance_bottom:
            metadata["affordance-bottom"] = str(affordance_bottom)
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_explicit_region_alignment",
        "size": (160.0, 160.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=80, cy=115, width=40, height=30),
                affordance_bottom=25,
            ),
        ],
        "regions": [
            record("region_lounge", "region", "lounge", Rect(cx=80, cy=97.5, width=80, height=115)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    alignment = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_explicit_iou_mean"
    ][0]
    assert alignment == {
        "view_id": "region_alignment",
        "metric": "inferred_region_explicit_iou_mean",
        "score": 1.0,
        "status": "computed",
        "method": "affordance_expanded_candidate_region_to_explicit_region_iou",
        "evidence": ["lounge"],
        "inferred_region_explicit_iou_evidence": [
            {
                "region": "lounge",
                "explicit_region_id": "region_lounge",
                "candidate_bbox": (40.0, 40.0, 120.0, 155.0),
                "explicit_bbox": (40.0, 40.0, 120.0, 155.0),
                "candidate_boundary_cue_ids": [],
                "candidate_has_boundary_cue": False,
                "candidate_area": 9200.0,
                "explicit_area": 9200.0,
                "intersection_area": 9200.0,
                "union_area": 9200.0,
                "iou": 1.0,
                "missing_explicit_area": 0.0,
                "overflow_candidate_area": 0.0,
                "missing_explicit_area_ratio": 0.0,
                "overflow_candidate_area_ratio": 0.0,
                "dominant_mismatch": "aligned",
            }
        ],
        "uncertainty": "compares affordance-expanded candidate bbox with explicit region geometry; bbox IoU proxy, not semantic region validation",
    }


def test_evaluate_scene_explains_inferred_region_explicit_mismatch():
    from features.affordance.models import Rect

    def record(record_id, role, region, rect, *, affordance_bottom=0.0):
        metadata = {"role": role, "region": region}
        if affordance_bottom:
            metadata["affordance-bottom"] = str(affordance_bottom)
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_explicit_region_mismatch",
        "size": (180.0, 180.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=80, cy=115, width=40, height=30),
                affordance_bottom=25,
            ),
        ],
        "regions": [
            record("region_lounge", "region", "lounge", Rect(cx=80, cy=100, width=120, height=140)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    alignment = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_explicit_iou_mean"
    ][0]
    assert alignment["score"] == 0.5476
    assert alignment["inferred_region_explicit_iou_evidence"] == [
        {
            "region": "lounge",
            "explicit_region_id": "region_lounge",
            "candidate_bbox": (40.0, 40.0, 120.0, 155.0),
            "explicit_bbox": (20.0, 30.0, 140.0, 170.0),
            "candidate_boundary_cue_ids": [],
            "candidate_has_boundary_cue": False,
            "candidate_area": 9200.0,
            "explicit_area": 16800.0,
            "intersection_area": 9200.0,
            "union_area": 16800.0,
            "iou": 0.5476,
            "missing_explicit_area": 7600.0,
            "overflow_candidate_area": 0.0,
            "missing_explicit_area_ratio": 0.4524,
            "overflow_candidate_area_ratio": 0.0,
            "dominant_mismatch": "candidate_underfills_explicit",
        }
    ]


def test_scene_metric_overlay_marks_objects_with_missing_region_records():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_missing_region_overlay",
        "size": (100.0, 100.0),
        "objects": [
            {
                "id": "orphan_table",
                "role": "table",
                "group": "orphan",
                "region": "",
                "rect": Rect(cx=25, cy=25, width=20, height=20),
                "points": [],
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {"role": "table", "region": ""},
            }
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="object-missing-region"' in svg
    assert 'data-object="orphan_table"' in svg
    assert 'data-region-key=""' in svg


def test_scene_metric_overlay_draws_inferred_regions():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_inferred_region_overlay",
        "size": (120.0, 100.0),
        "objects": [
            {
                "id": "chair",
                "role": "chair",
                "group": "lounge",
                "region": "lounge",
                "rect": Rect(cx=50, cy=50, width=20, height=20),
                "points": [],
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {
                    "region": "lounge",
                    "affordance-bottom": "20",
                },
            }
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="inferred-region"' in svg
    assert 'data-region="lounge"' in svg
    assert 'data-source="affordance_zone_boundary_cue_expanded_group_bounds"' in svg


def test_scene_metric_overlay_draws_inferred_region_candidates_with_explicit_regions():
    from features.affordance.models import Rect

    def record(record_id, role, region, rect, *, affordance_bottom=0.0):
        metadata = {"role": role, "region": region}
        if affordance_bottom:
            metadata["affordance-bottom"] = str(affordance_bottom)
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_inferred_region_candidate_overlay",
        "size": (160.0, 160.0),
        "objects": [
            record("table", "table", "lounge", Rect(cx=80, cy=60, width=80, height=40)),
            record(
                "chair",
                "chair",
                "lounge",
                Rect(cx=80, cy=115, width=40, height=30),
                affordance_bottom=25,
            ),
        ],
        "regions": [
            record("region_lounge", "region", "lounge", Rect(cx=80, cy=97.5, width=80, height=115)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert matrix["inferred_regions"] == []
    candidate_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_candidate_count"
    ][0]
    assert candidate_row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_candidate_count",
        "score": 1,
        "status": "computed",
        "method": "affordance_zone_boundary_cue_expanded_group_candidate_bounds",
        "evidence": ["inferred_region_lounge"],
        "inferred_region_candidate_evidence": [
            {
                "region": "lounge",
                "geometry_basis": "object_footprints_plus_affordance_zone_rects",
                "member_ids": ["chair", "table"],
                "affordance_zone_ids": ["affordance_zone_chair_bottom"],
                "boundary_cue_ids": [],
                "bbox": (40.0, 40.0, 120.0, 155.0),
            }
        ],
        "uncertainty": "candidate regions inferred from furniture footprint, affordance extents, same-region boundary cues, and spacing margins; bbox proxy, not alpha-shape or perception-calibrated region discovery",
    }
    assert 'data-layer="inferred-region-candidate"' in svg
    assert 'data-region="lounge"' in svg
    assert 'data-candidate="inferred_region_lounge"' in svg


def test_evaluate_scene_infers_thick_gap_path_between_affordance_regions():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None):
        metadata = {"role": role, "region": group}
        if affordance:
            for side, value in affordance.items():
                metadata[f"affordance-{side}"] = str(value)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_affordance_gap_path",
        "size": (260.0, 180.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=60, cy=70, width=60, height=40)),
            record(
                "left_chair",
                "chair",
                "left",
                Rect(cx=60, cy=120, width=40, height=30),
                affordance={"bottom": 20},
            ),
            record("right_table", "table", "right", Rect(cx=200, cy=70, width=60, height=40)),
            record(
                "right_chair",
                "chair",
                "right",
                Rect(cx=200, cy=120, width=40, height=30),
                affordance={"bottom": 20},
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    gap_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_count"
    ][0]
    assert gap_row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_count",
        "score": 1,
        "status": "computed",
        "method": "affordance_region_bbox_axis_gap_band_proxy",
        "evidence": ["inferred_gap_path_left__right"],
        "inferred_region_gap_path_evidence": [
                {
                    "id": "inferred_gap_path_left__right",
                    "region_a": "inferred_region_left",
                    "region_b": "inferred_region_right",
                    "orientation": "vertical",
                    "bbox": (110.0, 23.75, 150.0, 180.0),
                    "thickness": 40.0,
                    "overlap_span": 156.25,
                }
            ],
            "uncertainty": "candidate path bands inferred from gaps between affordance-expanded region bboxes; proxy, not navmesh, medial axis, or route certification",
        }

    svg = scene_metric_overlay_svg(scene, matrix)
    assert 'data-layer="inferred-gap-path"' in svg
    assert 'data-gap-path="inferred_gap_path_left__right"' in svg
    assert 'data-thickness="40.0000"' in svg


def test_evaluate_scene_exposes_furniture_groups_from_furniture_affordance_extents():
    """Furniture groups expose union envelopes plus separate overlap evidence."""
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None):
        """Create a minimal neutral object record for furniture group tests."""
        metadata = {"role": role, "region": group}
        if affordance:
            for side, value in affordance.items():
                metadata[f"affordance-{side}"] = str(value)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_furniture_group_skeleton",
        "size": (220.0, 180.0),
        "objects": [
            record("table", "table", "dining", Rect(cx=90, cy=70, width=80, height=40)),
            record(
                "chair",
                "chair",
                "dining",
                Rect(cx=90, cy=115, width=40, height=30),
                affordance={"bottom": 20},
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
    }

    matrix = evaluate_scene(scene)
    furniture_groups = matrix["adapter_payload"]["evidence_geometry"]["furniture_groups"]["items"]

    expected_groups = [
        {
            "id": "furniture_group_dining",
            "activity_region_id": "dining",
            "region": "dining",
            "member_ids": ["chair", "table"],
            "furniture_affordance_extent_ids": [
                "furniture_affordance_extent_chair",
                "furniture_affordance_extent_table",
            ],
            "bbox": (50.0, 50.0, 130.0, 150.0),
            "overlap_evidence": [
                {
                    "a": "furniture_affordance_extent_chair",
                    "b": "furniture_affordance_extent_table",
                    "overlap_area": 0.0,
                }
            ],
        }
    ]
    comparable_groups = [
        {key: value for key, value in group.items() if key != "metadata"}
        for group in furniture_groups
    ]
    assert comparable_groups == expected_groups
    metadata = furniture_groups[0]["metadata"]
    assert metadata["level"] == "furniture_group"
    assert metadata["source"] == "semantic_region_grouped_furniture_affordance_extents"
    assert metadata["geometry_basis"] == "union_envelope_of_member_furniture_affordance_extents"
    assert metadata["group-axis-basis"] == "member_frame_consensus"
    assert float(metadata["group-axis-member-alignment"]) > 0.0
    assert float(metadata["group-axis-primary-extent"]) > 0.0
    assert matrix["adapter_payload"]["evidence_geometry"]["furniture_groups"] == {
        "count": 1,
        "items": furniture_groups,
    }


def test_position_grammar_line_fit_drops_for_shifted_member():
    """Line grammar should penalize a shifted member while keeping one public fit."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_row",
        "activity_region_id": "row",
        "rect": Rect(cx=100, cy=50, width=200, height=40),
        "furniture_affordance_extent_ids": ["a", "b", "c"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-strength": "1.0",
            "group-axis-basis": "test",
        },
    }
    regular = [
        {"id": "a", "rect": Rect(cx=0, cy=50, width=20, height=20)},
        {"id": "b", "rect": Rect(cx=100, cy=50, width=20, height=20)},
        {"id": "c", "rect": Rect(cx=200, cy=50, width=20, height=20)},
    ]
    shifted = [
        {"id": "a", "rect": Rect(cx=0, cy=50, width=20, height=20)},
        {"id": "b", "rect": Rect(cx=100, cy=75, width=20, height=20)},
        {"id": "c", "rect": Rect(cx=200, cy=50, width=20, height=20)},
    ]

    regular_fit = position_grammar_evidence([group], regular)["items"][0]
    shifted_fit = position_grammar_evidence([group], shifted)["items"][0]

    assert regular_fit["position-grammar-type"] == "line"
    assert regular_fit["position-fit"] > shifted_fit["position-fit"]
    assert shifted_fit["position-residual-mean"] > 0


def test_region_position_grammar_scores_furniture_groups_not_extents():
    """Public position evidence should assign one slot per furniture group."""
    from features.position_grammar import region_position_grammar_evidence

    groups = [
        {
            "id": "furniture_group_a",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=0, cy=0, width=20, height=20),
            "member_ids": ["a_table", "a_chair"],
            "furniture_affordance_extent_ids": ["a_table_extent", "a_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
        {
            "id": "furniture_group_b",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=100, cy=0, width=20, height=20),
            "member_ids": ["b_table", "b_chair"],
            "furniture_affordance_extent_ids": ["b_table_extent", "b_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
        {
            "id": "furniture_group_c",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=200, cy=0, width=20, height=20),
            "member_ids": ["c_table", "c_chair"],
            "furniture_affordance_extent_ids": ["c_table_extent", "c_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
    ]

    evidence = region_position_grammar_evidence(groups)
    item = evidence["items"][0]

    assert item["subject_kind"] in {"activity_region", "room_scope"}
    assert item["position-member-count"] == 3
    assert item["position-slot-count"] == 3
    assert item["assignments"] == [
        "furniture_group_a",
        "furniture_group_b",
        "furniture_group_c",
    ]
    assert all("extent" not in assignment for assignment in item["assignments"])


def test_position_grammar_grid_uses_local_frame_not_global_xy():
    """Rotated grids should fit in local u/v coordinates."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_rotated_grid",
        "activity_region_id": "rotated_grid",
        "rect": Rect(cx=100, cy=100, width=160, height=160),
        "furniture_affordance_extent_ids": ["a", "b", "c", "d"],
        "metadata": {
            "group-axis-angle": "45",
            "group-axis-strength": "1.0",
            "group-axis-basis": "test",
        },
    }
    extents = [
        {"id": "a", "rect": Rect(cx=100, cy=57.57, width=12, height=12)},
        {"id": "b", "rect": Rect(cx=142.43, cy=100, width=12, height=12)},
        {"id": "c", "rect": Rect(cx=57.57, cy=100, width=12, height=12)},
        {"id": "d", "rect": Rect(cx=100, cy=142.43, width=12, height=12)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "grid"
    assert item["position-fit"] > 0.95
    assert item["position-frame-angle"] == 45.0


def test_position_grammar_uses_authored_slots_when_available():
    """Authored slots should win over inferred grammar when complete."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_authored",
        "activity_region_id": "authored",
        "rect": Rect(cx=50, cy=50, width=100, height=100),
        "furniture_affordance_extent_ids": ["a", "b"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-basis": "test",
            "position-slots": "a:0,0;b:50,0",
        },
    }
    extents = [
        {"id": "a", "rect": Rect(cx=50, cy=50, width=10, height=10)},
        {"id": "b", "rect": Rect(cx=100, cy=50, width=10, height=10)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "authored"
    assert item["position-fit"] == 1.0
    assert item["position-confidence"] > 0.9


def test_position_grammar_pair_scores_matched_offsets():
    """Pair grammar should explain two symmetric members around the local center."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_pair",
        "activity_region_id": "pair",
        "rect": Rect(cx=100, cy=100, width=120, height=60),
        "furniture_affordance_extent_ids": ["left", "right"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-basis": "test",
        },
    }
    extents = [
        {"id": "left", "rect": Rect(cx=70, cy=100, width=20, height=20)},
        {"id": "right", "rect": Rect(cx=130, cy=100, width=20, height=20)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "pair"
    assert item["position-fit"] > 0.95


def test_evaluator_emits_position_grammar_rows():
    """Matrix should expose only fit and confidence as public position variables."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}

    assert rows["P_position_fit"]["view_id"] == "internal_order"
    assert rows["P_position_fit"]["status"] == "computed"
    assert rows["P_position_confidence"]["view_id"] == "internal_order"
    assert rows["P_position_confidence"]["status"] == "computed"
    assert "region_position_grammar_evidence" in rows["P_position_fit"]
    assert "position_grammar_evidence" not in rows["P_position_fit"]
    assert "position_grammar" not in matrix
    assert "position_grammar" not in matrix["adapter_payload"]["evidence_geometry"]
    assert "region_position_grammar" in matrix
    assert "group_assembly_grammar" in matrix
    assert "line_fit" not in rows
    assert "grid_fit" not in rows
    assert "pair_fit" not in rows


def test_evaluator_position_rows_use_region_position_evidence():
    """Public P_position rows should expose region-level group assignments."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    evidence = rows["P_position_fit"]["region_position_grammar_evidence"]

    assert evidence
    assert "position_grammar_evidence" not in rows["P_position_fit"]
    assert all(item["subject_kind"] in {"activity_region", "room_scope"} for item in evidence)
    assert all(
        assignment.startswith("furniture_group_")
        for item in evidence
        for assignment in item["assignments"]
    )


def test_overlay_draws_position_grammar_residuals():
    """Overlay should expose selected position grammar residual vectors."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-residual"' in svg
    assert 'data-layer="position-grammar-slot"' in svg


def test_position_grammar_overlay_hides_unrelated_metric_layers():
    """Focused overlay should draw only the position grammar proxy evidence."""
    from features.scene_evaluator import scene_position_grammar_overlay_svg

    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_position_grammar_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-slot"' in svg
    assert 'data-layer="position-grammar-residual"' in svg
    assert 'data-layer="region-axis"' not in svg
    assert 'data-layer="inferred-region"' not in svg
    assert 'data-layer="column-axis"' not in svg
    assert 'data-layer="path-graph-edge"' not in svg


def test_position_grammar_overlay_draws_group_slots_not_extent_slots():
    """Focused position overlay should show furniture-group assignments only."""
    from features.scene_evaluator import scene_position_grammar_overlay_svg

    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_position_grammar_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-slot"' in svg
    assert 'data-member="furniture_group_north_table_group_r1_c1"' in svg
    assert "furniture_affordance_extent_" not in svg


def test_position_grammar_overlay_draws_group_proxy_outlines():
    """Focused overlay should draw furniture-group proxies, not object extents."""
    from features.scene_evaluator import scene_position_grammar_overlay_svg

    scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_position_grammar_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-group"' in svg
    assert 'data-group="furniture_group_north_table_group_r1_c1"' in svg
    assert 'data-group="furniture_group_north_tables"' not in svg
    assert 'data-layer="position-grammar-extent"' not in svg


def test_position_no_rotation_fixture_scores_position_without_rotation_signal():
    """Position fixture should produce group-level evidence with zero rotations."""
    scene = load_structured_svg_scene(Path("test/SVG_potionNoRotation.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    evidence = rows["P_position_fit"]["region_position_grammar_evidence"]

    assert rows["P_position_fit"]["status"] == "computed"
    assert evidence
    assert all(item["position-member-count"] >= 2 for item in evidence)
    assert all(
        assignment.startswith("furniture_group_")
        for item in evidence
        for assignment in item["assignments"]
    )


def test_evaluate_scene_exposes_shared_spatial_network_schema():
    """Internal and inter-region networks use one shared evidence schema."""
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        """Create a minimal neutral object record for spatial network tests."""
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_spatial_network_skeleton",
        "size": (260.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=60, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=200, cy=80, width=80, height=80)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
    }

    matrix = evaluate_scene(scene)
    networks = matrix["spatial_networks"]
    schema_keys = {"id", "scope", "nodes", "edges", "components", "metadata"}

    assert [network["scope"] for network in networks] == [
        "region_internal",
        "region_internal",
        "inter_region",
    ]
    assert all(set(network) == schema_keys for network in networks)
    assert networks[-1]["edges"] == [
        {
            "id": "inferred_gap_path_left__right",
            "a": "inferred_region_left",
            "b": "inferred_region_right",
            "kind": "gap_path",
            "thickness": 30.0,
        }
    ]
    assert matrix["adapter_payload"]["evidence_geometry"]["spatial_networks"] == {
        "count": 3,
        "items": networks,
    }


def test_evaluate_scene_exposes_boundary_semantic_profiles():
    """Boundary semantics normalize walk, visibility, thickness, and openings."""
    from features.affordance.models import Rect

    def boundary(record_id, kind, rect, *, walk, see, grouping, thickness):
        """Create a minimal neutral boundary record for semantic profile tests."""
        return {
            "id": record_id,
            "role": "boundary",
            "group": "global",
            "region": "global",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk,
                "see_block": see,
                "grouping_strength": grouping,
            },
            "metadata": {
                "role": "boundary",
                "boundary-kind": kind,
                "thickness": str(thickness),
            },
        }

    scene = {
        "source": "synthetic_boundary_semantics",
        "size": (220.0, 140.0),
        "objects": [],
        "regions": [],
        "boundaries": [
            boundary("rug_edge", "rug", Rect(cx=60, cy=60, width=80, height=0), walk=0.0, see=0.0, grouping=0.85, thickness=0),
            boundary("low_cabinet", "cabinet", Rect(cx=120, cy=60, width=80, height=20), walk=1.0, see=0.35, grouping=0.65, thickness=20),
            boundary("glass_wall", "glass", Rect(cx=180, cy=60, width=80, height=3), walk=1.0, see=0.15, grouping=0.4, thickness=3),
        ],
        "entries": [
            {
                "id": "cabinet_opening",
                "role": "opening",
                "group": "global",
                "region": "global",
                "rect": Rect(cx=120, cy=60, width=30, height=20),
                "points": [],
                "weights": {
                    "walk_block": 0.0,
                    "see_block": 0.0,
                    "grouping_strength": 0.0,
                },
                "metadata": {
                    "role": "opening",
                    "host-boundary": "low_cabinet",
                },
            }
        ],
        "paths": [],
        "column_axes": [],
    }

    matrix = evaluate_scene(scene)
    semantics = {item["id"]: item for item in matrix["boundary_semantics"]}

    assert semantics["rug_edge"] == {
        "id": "rug_edge",
        "kind": "rug",
        "walk_passable": True,
        "see_passable": True,
        "thickness": 0.0,
        "grouping_strength": 0.85,
        "opening_ids": [],
        "surface_identity": True,
        "metadata": {
            "source": "authored_boundary_weights_and_metadata",
        },
    }
    assert semantics["low_cabinet"]["walk_passable"] is False
    assert semantics["low_cabinet"]["see_passable"] is True
    assert semantics["low_cabinet"]["opening_ids"] == ["cabinet_opening"]
    assert semantics["glass_wall"]["walk_passable"] is False
    assert semantics["glass_wall"]["see_passable"] is True
    assert matrix["adapter_payload"]["evidence_geometry"]["boundary_semantics"] == {
        "count": 3,
        "items": matrix["boundary_semantics"],
    }


def test_evaluate_scene_infers_gap_paths_from_candidates_with_explicit_regions():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_candidate_gap_path_with_explicit_regions",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [
            record("region_left", "region", "left", Rect(cx=70, cy=80, width=120, height=120)),
            record("region_right", "region", "right", Rect(cx=290, cy=80, width=120, height=120)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    gap_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_count"
    ][0]

    assert matrix["inferred_regions"] == []
    assert gap_row["score"] == 1
    assert gap_row["inferred_region_gap_path_evidence"] == [
        {
            "id": "inferred_gap_path_left__right",
            "region_a": "inferred_region_left",
            "region_b": "inferred_region_right",
            "orientation": "vertical",
            "bbox": (130.0, 20.0, 230.0, 140.0),
            "thickness": 100.0,
            "overlap_span": 120.0,
        }
    ]


def test_evaluate_scene_filters_gap_paths_blocked_by_intermediate_regions():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_intermediate_region_gap_filter",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=50, cy=80, width=80, height=80)),
            record("middle_table", "table", "middle", Rect(cx=170, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [
            record("region_left", "region", "left", Rect(cx=50, cy=80, width=80, height=80)),
            record("region_middle", "region", "middle", Rect(cx=170, cy=80, width=80, height=80)),
            record("region_right", "region", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    gap_ids = [path["id"] for path in matrix["inferred_region_gap_paths"]]

    assert gap_ids == [
        "inferred_gap_path_left__middle",
        "inferred_gap_path_middle__right",
    ]
    assert matrix["inferred_region_gap_path_graph"] == {
        "method": "inferred_gap_path_region_adjacency_graph_proxy",
        "node_count": 3,
        "edge_count": 2,
        "clear_edge_count": 2,
        "occupied_edge_count": 0,
        "free_space_supported_edge_count": 2,
        "walkable_proxy_edge_count": 2,
        "walkable_proxy_min_thickness": 40.0,
        "walkable_proxy_mean_thickness": 40.0,
        "component_count": 1,
        "walkable_proxy_component_count": 1,
        "components": [
            [
                "inferred_region_left",
                "inferred_region_middle",
                "inferred_region_right",
            ]
        ],
        "walkable_proxy_components": [
            [
                "inferred_region_left",
                "inferred_region_middle",
                "inferred_region_right",
            ]
        ],
        "nodes": [
            {"id": "inferred_region_left", "region": "left"},
            {"id": "inferred_region_middle", "region": "middle"},
            {"id": "inferred_region_right", "region": "right"},
        ],
        "edges": [
            {
                "id": "inferred_gap_path_left__middle",
                "a": "inferred_region_left",
                "b": "inferred_region_middle",
                "orientation": "vertical",
                "thickness": 40.0,
                "overlap_span": 80.0,
                "clear_status": "clear_proxy",
                "occupancy_ratio": 0.0,
                "free_space_overlap_ratio": 1.0,
            },
            {
                "id": "inferred_gap_path_middle__right",
                "a": "inferred_region_middle",
                "b": "inferred_region_right",
                "orientation": "vertical",
                "thickness": 40.0,
                "overlap_span": 80.0,
                "clear_status": "clear_proxy",
                "occupancy_ratio": 0.0,
                "free_space_overlap_ratio": 1.0,
            },
        ],
        "walkable_proxy_edges": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "walkable_proxy_edge_widths": [
            {
                "id": "inferred_gap_path_left__middle",
                "thickness": 40.0,
                "overlap_span": 80.0,
            },
            {
                "id": "inferred_gap_path_middle__right",
                "thickness": 40.0,
                "overlap_span": 80.0,
            },
        ],
        "minimum_width": 40.0,
        "minimum_width_basis": "half_sampled_grid_resolution",
        "minimum_width_evidence": ["left_table", "middle_table", "right_table"],
        "width_pass_edge_count": 2,
        "width_fail_edge_count": 0,
        "width_pass_edges": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "width_fail_edges": [],
        "width_evidence": [
            {
                "id": "inferred_gap_path_left__middle",
                "thickness": 40.0,
                "minimum_width": 40.0,
                "passes": True,
            },
            {
                "id": "inferred_gap_path_middle__right",
                "thickness": 40.0,
                "minimum_width": 40.0,
                "passes": True,
            },
        ],
    }
    assert (
        matrix["adapter_payload"]["route_topology_handoff"][
            "inferred_gap_path_graph"
        ]
        == {
            "method": "inferred_gap_path_region_adjacency_graph_proxy",
            "node_count": 3,
            "edge_count": 2,
            "clear_edge_count": 2,
            "occupied_edge_count": 0,
            "free_space_supported_edge_count": 2,
            "walkable_proxy_edge_count": 2,
            "walkable_proxy_min_thickness": 40.0,
            "walkable_proxy_mean_thickness": 40.0,
            "component_count": 1,
            "walkable_proxy_component_count": 1,
            "walkable_proxy_components": [
                [
                    "inferred_region_left",
                    "inferred_region_middle",
                    "inferred_region_right",
                ]
            ],
            "walkable_proxy_edges": [
                "inferred_gap_path_left__middle",
                "inferred_gap_path_middle__right",
            ],
            "walkable_proxy_edge_widths": [
                {
                    "id": "inferred_gap_path_left__middle",
                    "thickness": 40.0,
                    "overlap_span": 80.0,
                },
                {
                    "id": "inferred_gap_path_middle__right",
                    "thickness": 40.0,
                    "overlap_span": 80.0,
                },
            ],
            "minimum_width": 40.0,
            "minimum_width_basis": "half_sampled_grid_resolution",
            "minimum_width_evidence": ["left_table", "middle_table", "right_table"],
            "width_pass_edge_count": 2,
            "width_fail_edge_count": 0,
            "width_pass_edges": [
                "inferred_gap_path_left__middle",
                "inferred_gap_path_middle__right",
            ],
            "width_fail_edges": [],
        }
    )
    walkable_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_walkable_proxy_ratio"
    ][0]
    assert walkable_row == {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_walkable_proxy_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "clear_and_free_space_supported_inferred_gap_path_edges",
        "evidence": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "walkable_proxy_edge_count": 2,
        "walkable_proxy_component_count": 1,
        "walkable_proxy_min_thickness": 40.0,
        "walkable_proxy_mean_thickness": 40.0,
        "total_gap_path_edge_count": 2,
        "walkable_proxy_edges": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "walkable_proxy_components": [
            [
                "inferred_region_left",
                "inferred_region_middle",
                "inferred_region_right",
            ]
        ],
        "walkable_proxy_edge_widths": [
            {
                "id": "inferred_gap_path_left__middle",
                "thickness": 40.0,
                "overlap_span": 80.0,
            },
            {
                "id": "inferred_gap_path_middle__right",
                "thickness": 40.0,
                "overlap_span": 80.0,
            },
        ],
        "uncertainty": "clear inferred gap bands with positive free-space overlap; proxy, not navmesh route certification or minimum-width guarantee",
    }
    width_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_min_width_pass_ratio"
    ][0]
    assert width_row == {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_min_width_pass_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "walkable_gap_band_thickness_over_half_sampled_grid_resolution",
        "evidence": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "minimum_width": 40.0,
        "minimum_width_basis": "half_sampled_grid_resolution",
        "minimum_width_evidence": ["left_table", "middle_table", "right_table"],
        "passing_edge_count": 2,
        "walkable_proxy_edge_count": 2,
        "width_pass_edges": [
            "inferred_gap_path_left__middle",
            "inferred_gap_path_middle__right",
        ],
        "width_fail_edges": [],
        "width_evidence": [
            {
                "id": "inferred_gap_path_left__middle",
                "thickness": 40.0,
                "minimum_width": 40.0,
                "passes": True,
            },
            {
                "id": "inferred_gap_path_middle__right",
                "thickness": 40.0,
                "minimum_width": 40.0,
                "passes": True,
            },
        ],
        "uncertainty": "minimum width uses half the sampled grid resolution as a scene-scale proxy; not code-compliant egress width, human-body calibration, or navmesh clearance",
    }
    consistency_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_gap_path_width_free_space_clearance_ratio"
    ][0]
    assert consistency_row == {
        "view_id": "path_connectivity",
        "metric": "inferred_gap_path_width_free_space_clearance_ratio",
        "score": 0.9,
        "status": "computed",
        "method": "free_space_edge_clearance_width_over_inferred_gap_band_width",
        "evidence": {
            "free_space_mean_edge_clearance_width": 36.0,
            "walkable_proxy_mean_thickness": 40.0,
            "walkable_proxy_min_thickness": 40.0,
            "walkable_proxy_edge_count": 2,
        },
        "uncertainty": "ratio between rect-cell free-space shared-edge width and inferred gap-band width; proxy consistency check, not route certification",
    }


def test_evaluate_scene_uses_manual_required_path_width_for_inferred_gap_paths():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_manual_required_path_width",
        "size": (360.0, 160.0),
        "settings": {"required_path_width": 45.0},
        "objects": [
            record("left_table", "table", "left", Rect(cx=50, cy=80, width=80, height=80)),
            record("middle_table", "table", "middle", Rect(cx=170, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [
            record("region_left", "region", "left", Rect(cx=50, cy=80, width=80, height=80)),
            record("region_middle", "region", "middle", Rect(cx=170, cy=80, width=80, height=80)),
            record("region_right", "region", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    width_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_min_width_pass_ratio"
    ][0]

    assert width_row["score"] == 0.0
    assert width_row["method"] == "walkable_gap_band_thickness_over_manual_required_path_width"
    assert width_row["minimum_width"] == 45.0
    assert width_row["minimum_width_basis"] == "manual_required_path_width"
    assert width_row["minimum_width_evidence"] == ["scene.settings.required_path_width"]
    assert width_row["width_pass_edges"] == []
    assert width_row["width_fail_edges"] == [
        "inferred_gap_path_left__middle",
        "inferred_gap_path_middle__right",
    ]
    assert matrix["adapter_payload"]["route_topology_handoff"]["inferred_gap_path_graph"][
        "minimum_width_basis"
    ] == "manual_required_path_width"


def test_scene_inference_layer_derives_evidence_from_neutral_scene_not_svg():
    from features.affordance.models import Rect
    from features.scene_inference import infer_scene_evidence

    def record(record_id, role, group, rect, *, affordance=None):
        metadata = {"role": role, "region": group}
        if affordance:
            metadata.update(affordance)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "neutral_dict_not_svg",
        "size": (260.0, 140.0),
        "settings": {"required_path_width": 45.0},
        "objects": [
            record(
                "left_chair",
                "chair",
                "left",
                Rect(cx=50, cy=70, width=40, height=40),
                affordance={"affordance-right": "20"},
            ),
            record("right_table", "table", "right", Rect(cx=190, cy=70, width=40, height=40)),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    evidence = infer_scene_evidence(scene)
    matrix = evaluate_scene(scene)

    assert evidence["affordance_zones"][0]["id"] == "affordance_zone_left_chair_right"
    assert evidence["inferred_region_candidates"][0]["metadata"]["member_ids"] == "left_chair"
    assert evidence["inferred_region_gap_paths"][0]["id"] == "inferred_gap_path_left__right"
    assert evidence["inferred_region_gap_path_graph"]["minimum_width_basis"] == (
        "manual_required_path_width"
    )
    assert matrix["inferred_region_gap_paths"] == evidence["inferred_region_gap_paths"]


def test_scene_inference_builds_furniture_extents_before_group_regions():
    from features.affordance.models import Rect
    from features.scene_inference import infer_scene_evidence

    def record(record_id, role, group, rect, *, affordance=None):
        metadata = {"role": role, "region": group}
        if affordance:
            metadata.update(affordance)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_hierarchical_region_inference",
        "size": (260, 160),
        "settings": {"required_path_width": 30},
        "objects": [
            record(
                "north_table",
                "table",
                "north_repeated_tables",
                Rect(cx=70, cy=60, width=40, height=30),
            ),
            record(
                "north_chair",
                "chair",
                "north_repeated_tables",
                Rect(cx=70, cy=110, width=30, height=30),
                affordance={"affordance-top": "20"},
            ),
            record(
                "south_table",
                "table",
                "south_repeated_tables",
                Rect(cx=190, cy=60, width=40, height=30),
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    evidence = infer_scene_evidence(scene)

    assert evidence["furniture_affordance_extents"][0] == {
        "id": "furniture_affordance_extent_north_chair",
        "object_id": "north_chair",
        "region": "north_repeated_tables",
        "rect": Rect(cx=70, cy=100, width=30, height=50),
        "footprint_rect": Rect(cx=70, cy=110, width=30, height=30),
        "affordance_zone_ids": ["affordance_zone_north_chair_top"],
        "metadata": {
            "level": "furniture_affordance_extent",
            "source": "object_footprint_plus_affordance_zones",
            "geometry_basis": "object_footprint_plus_own_affordance_zone_rects",
        },
    }
    north_region = [
        item
        for item in evidence["inferred_region_candidates"]
        if item["region"] == "north_repeated_tables"
    ][0]
    assert north_region["metadata"]["level"] == "activity_region_candidate"
    assert north_region["metadata"]["child_extent_ids"] == (
        "furniture_affordance_extent_north_chair,"
        "furniture_affordance_extent_north_table"
    )
    assert evidence["inferred_region_gap_paths"][0]["metadata"]["path_between"] == (
        "activity_region_candidate"
    )


def test_evaluator_entrypoint_uses_scene_inference_layer():
    source = Path("features/scene_evaluator.py").read_text(encoding="utf-8")
    inference_source = Path("features/scene_inference.py").read_text(encoding="utf-8")
    entrypoint = source[source.index("def evaluate_scene"):source.index("def export_adapter_payload_json")]

    assert "infer_scene_evidence(scene)" in entrypoint
    assert "_inferred_region_candidates(scene)" not in entrypoint
    assert "_inferred_region_gap_paths(" not in entrypoint
    assert "_affordance_zones(scene)" not in entrypoint
    assert "def _inferred_region_candidates" not in source
    assert "def _inferred_region_gap_path_graph" not in source
    assert "def _affordance_margins" not in source
    assert "scene_loader" not in inference_source
    assert "scene_evaluator" not in inference_source
    assert "xml.etree" not in inference_source


def test_architecture_memory_records_svg_as_base_map_not_matrix_framework():
    memory = Path(
        "docs/indoor_layout_evaluation_matrix_architecture_memory.md"
    ).read_text(encoding="utf-8")
    status = Path("docs/indoor_layout_evaluation_matrix_task_status.md").read_text(
        encoding="utf-8"
    )

    assert "SVG is a neutral BIM proxy/base map" in memory
    assert "SVG does not define the evaluation matrix" in memory
    assert "Neutral Scene" in memory
    assert "Inference / Evidence Layer" in memory
    assert "Evaluation Matrix" in memory
    assert "matrix consumes neutral scene plus inference evidence" in memory
    assert "User-authored semantic attributes are the primary input" in memory
    assert "bbox, rect-cell, or geometric fallback algorithms are secondary" in memory
    assert "object footprint -> furniture affordance extent" in memory
    assert "activity region candidate -> inter-region gap path" in memory
    assert "required width read from scene settings" in memory
    assert "All new or modified project-owned code should follow this rule" in memory
    assert "Vendored OCTA toolbox code is exempt unless it is edited" in memory
    assert "Every function should have a docstring" in memory
    assert "Important computation steps should have comments" in memory
    assert "scene_inference.py" in status
    assert "SVG is a neutral BIM proxy/base map" in status
    assert "User-authored semantic attributes are the primary input" in status


def test_scene_inference_functions_have_docstrings_and_key_step_comments():
    source = Path("features/scene_inference.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    functions = [
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    missing_docstrings = [
        node.name for node in functions if not ast.get_docstring(node)
    ]

    assert missing_docstrings == []
    assert "# Group objects by neutral region keys" in source
    assert "# Expand candidates just enough to represent repeated-group spacing" in source
    assert "# A gap band is usable only when it is clear and supported by free space" in source
    assert "# Manual path width is a demand parameter, not an inferred SVG feature" in source
    assert "# Explicit front affordance is still authored input" in source


def test_evaluate_scene_reports_inferred_gap_path_occupancy_by_objects_and_affordances():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, affordance=None, region=None):
        metadata = {"role": role, "region": group}
        if affordance:
            for side, value in affordance.items():
                metadata[f"affordance-{side}"] = str(value)
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": region or group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": metadata,
        }

    scene = {
        "source": "synthetic_inferred_gap_path_occupancy",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
            record(
                "center_stool",
                "stool",
                "misc",
                Rect(cx=180, cy=80, width=20, height=40),
                affordance={"left": 10},
                region="room",
            ),
        ],
        "regions": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_occupancy_ratio"
    ][0]

    assert row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_occupancy_ratio",
        "score": 0.1,
        "status": "computed",
        "method": "inferred_gap_band_overlap_with_object_footprints_and_affordance_zones",
        "evidence": ["inferred_gap_path_left__right"],
        "inferred_region_gap_path_occupancy_evidence": [
            {
                "gap_path_id": "inferred_gap_path_left__right",
                "gap_bbox": (130.0, 20.0, 230.0, 140.0),
                "gap_area": 12000.0,
                "occupied_area": 1200,
                "occupancy_ratio": 0.1,
                "occupiers": [
                    {
                        "id": "center_stool",
                        "kind": "object_footprint",
                        "overlap_area": 800,
                    },
                    {
                        "id": "affordance_zone_center_stool_left",
                        "kind": "affordance_zone",
                        "object_id": "center_stool",
                        "overlap_area": 400,
                    },
                ],
            }
        ],
        "uncertainty": "overlap of inferred gap bands with object footprints and affordance zones; bbox union proxy, not navmesh clearance certification",
    }
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    assert geometry["inferred_region_gap_path_occupancy"] == {
        "count": 1,
        "items": row["inferred_region_gap_path_occupancy_evidence"],
    }
    assert geometry["inferred_region_gap_paths"]["items"] == [
        {
            "id": "inferred_gap_path_left__right",
            "region_a": "inferred_region_left",
            "region_b": "inferred_region_right",
            "orientation": "vertical",
            "bbox": (130.0, 20.0, 230.0, 140.0),
            "thickness": 100.0,
            "overlap_span": 120.0,
            "occupied": True,
            "occupancy_ratio": 0.1,
            "occupied_area": 1200,
            "clear_status": "occupied_proxy",
            "free_space_overlap_ratio": 0.9333,
            "free_space_overlap_area": 11200.0,
        }
    ]
    svg = scene_metric_overlay_svg(scene, matrix)
    assert 'data-layer="inferred-gap-path-occupancy"' in svg
    assert 'data-gap-path="inferred_gap_path_left__right"' in svg
    assert 'data-occupier="center_stool"' in svg
    assert 'data-occupancy-ratio="0.1000"' in svg
    root = ET.fromstring(svg)
    gap_rect = next(
        element
        for element in root.iter()
        if element.attrib.get("data-layer") == "inferred-gap-path"
        and element.attrib.get("data-gap-path") == "inferred_gap_path_left__right"
    )
    assert gap_rect.attrib["data-occupied"] == "true"
    assert gap_rect.attrib["data-occupancy-ratio"] == "0.1000"
    assert gap_rect.attrib["data-clear-status"] == "occupied_proxy"
    assert matrix["inferred_region_gap_path_graph"]["walkable_proxy_edge_count"] == 0
    assert matrix["inferred_region_gap_path_graph"]["walkable_proxy_edges"] == []
    assert matrix["inferred_region_gap_path_graph"]["walkable_proxy_component_count"] == 2
    assert matrix["inferred_region_gap_path_graph"]["walkable_proxy_components"] == [
        ["inferred_region_left"],
        ["inferred_region_right"],
    ]
    walkable_row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_walkable_proxy_ratio"
    ][0]
    assert walkable_row["score"] == 0.0
    assert walkable_row["walkable_proxy_edge_count"] == 0
    assert walkable_row["walkable_proxy_component_count"] == 2
    assert walkable_row["total_gap_path_edge_count"] == 1


def test_evaluate_scene_reports_inferred_gap_path_free_space_overlap():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": 0.0,
            },
            "metadata": {"boundary-kind": kind} if kind else {"role": role, "region": group},
        }

    room = record(
        "room_boundary",
        "boundary",
        "room",
        Rect(cx=180, cy=80, width=360, height=160),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (360, 0), (360, 160), (0, 160), (0, 0)]
    scene = {
        "source": "synthetic_gap_path_free_space_overlap",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [],
        "boundaries": [room],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_free_space_overlap_ratio"
    ][0]

    assert row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_free_space_overlap_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "inferred_gap_band_overlap_with_rect_cell_free_space_polygons",
        "evidence": ["inferred_gap_path_left__right"],
        "inferred_region_gap_path_free_space_overlap_evidence": [
            {
                "gap_path_id": "inferred_gap_path_left__right",
                "gap_bbox": (130.0, 20.0, 230.0, 140.0),
                "gap_area": 12000.0,
                "free_space_overlap_area": 12000.0,
                "free_space_overlap_ratio": 1.0,
                "overlap_cell_ids": [
                    "component_0_cell_5",
                    "component_0_cell_6",
                    "component_0_cell_7",
                ],
            }
        ],
        "uncertainty": "overlap of inferred gap bands with rect-cell free-space polygons; proxy, not navmesh or route certification",
    }
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    assert geometry["inferred_region_gap_path_free_space_overlap"] == {
        "count": 1,
        "items": row["inferred_region_gap_path_free_space_overlap_evidence"],
    }
    assert geometry["inferred_region_gap_paths"]["items"][0][
        "free_space_overlap_ratio"
    ] == 1.0


def test_evaluate_scene_reports_inferred_gap_path_cad_free_space_overlap():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": 0.0,
            },
            "metadata": {"boundary-kind": kind} if kind else {"role": role, "region": group},
        }

    room = record(
        "room_boundary",
        "boundary",
        "room",
        Rect(cx=180, cy=80, width=360, height=160),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (360, 0), (360, 160), (0, 160), (0, 0)]
    blocker = record(
        "middle_partition",
        "boundary",
        "room",
        Rect(cx=180, cy=80, width=20, height=120),
        kind="wall",
        walk_block=1.0,
    )
    scene = {
        "source": "synthetic_gap_path_cad_free_space_overlap",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [],
        "boundaries": [room, blocker],
        "entries": [],
        "paths": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_cad_free_space_overlap_ratio"
    ][0]

    assert row == {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_cad_free_space_overlap_ratio",
        "score": 0.8,
        "status": "computed",
        "method": "inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons",
        "evidence": ["inferred_gap_path_left__right"],
        "inferred_region_gap_path_cad_free_space_overlap_evidence": [
            {
                "gap_path_id": "inferred_gap_path_left__right",
                "gap_bbox": (130.0, 20.0, 230.0, 140.0),
                "gap_area": 12000.0,
                "cad_free_space_overlap_area": 9600.0,
                "cad_free_space_overlap_ratio": 0.8,
                "overlap_component_ids": ["component_0"],
            }
        ],
        "uncertainty": "overlap of inferred gap bands with Shapely room-minus-blocker polygons; stronger than rect-cell proxy but still not navmesh route certification",
    }
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    assert geometry["inferred_region_gap_path_cad_free_space_overlap"] == {
        "count": 1,
        "items": row["inferred_region_gap_path_cad_free_space_overlap_evidence"],
    }
    assert geometry["inferred_region_gap_paths"]["items"][0][
        "cad_free_space_overlap_ratio"
    ] == 0.8
    graph = matrix["inferred_region_gap_path_graph"]
    assert graph["cad_free_space_supported_edge_count"] == 1
    assert graph["cad_free_space_supported_edges"] == ["inferred_gap_path_left__right"]
    assert graph["edges"][0]["cad_free_space_overlap_ratio"] == 0.8
    handoff_graph = matrix["adapter_payload"]["route_topology_handoff"][
        "inferred_gap_path_graph"
    ]
    assert handoff_graph["cad_free_space_supported_edge_count"] == 1
    assert handoff_graph["cad_free_space_supported_edges"] == [
        "inferred_gap_path_left__right"
    ]


def test_evaluate_scene_compares_inferred_gap_paths_to_explicit_paths():
    from features.affordance.models import Rect

    def record(record_id, role, group, rect):
        return {
            "id": record_id,
            "role": role,
            "group": group,
            "region": group,
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"role": role, "region": group},
        }

    scene = {
        "source": "synthetic_gap_path_explicit_path_iou",
        "size": (360.0, 160.0),
        "objects": [
            record("left_table", "table", "left", Rect(cx=70, cy=80, width=80, height=80)),
            record("right_table", "table", "right", Rect(cx=290, cy=80, width=80, height=80)),
        ],
        "regions": [
            record("region_left", "region", "left", Rect(cx=70, cy=80, width=120, height=120)),
            record("region_right", "region", "right", Rect(cx=290, cy=80, width=120, height=120)),
        ],
        "paths": [
            record("middle_path", "path", "circulation", Rect(cx=180, cy=80, width=100, height=120)),
        ],
        "boundaries": [],
        "entries": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_explicit_path_iou_mean"
    ][0]

    assert row == {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_explicit_path_iou_mean",
        "score": 1.0,
        "status": "computed",
        "method": "affordance_gap_band_to_explicit_path_bbox_iou",
        "evidence": ["inferred_gap_path_left__right"],
        "inferred_region_gap_path_explicit_path_iou_evidence": [
            {
                "gap_path_id": "inferred_gap_path_left__right",
                "best_path_id": "middle_path",
                "gap_bbox": (130.0, 20.0, 230.0, 140.0),
                "path_bbox": (130.0, 20.0, 230.0, 140.0),
                "iou": 1.0,
            }
        ],
        "uncertainty": "compares inferred gap bands with authored path bboxes; bbox IoU proxy, not route validation or navmesh alignment",
    }


def test_sampled_path_reachable_region_ratio_requires_path_contact():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [],
        "entries": [
            {
                "id": "entry",
                "role": "opening",
                "group": "global",
                "region": "room",
                "rect": Rect(cx=0, cy=25, width=0, height=50),
                "points": [],
                "weights": {"walk_block": 0.0, "see_block": 0.0, "grouping_strength": 0.0},
                "metadata": {},
            }
        ],
        "paths": [
            {
                "id": "path",
                "role": "path",
                "group": "global",
                "region": "room",
                "rect": Rect(cx=50, cy=25, width=100, height=50),
                "points": [(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)],
                "weights": {"walk_block": 0.0, "see_block": 0.0, "grouping_strength": 0.0},
                "metadata": {},
            }
        ],
        "regions": [
            {
                "id": "on_path_region",
                "role": "region",
                "group": "global",
                "region": "on_path",
                "rect": Rect(cx=75, cy=25, width=50, height=50),
                "points": [],
                "weights": {"walk_block": 0.0, "see_block": 0.0, "grouping_strength": 0.0},
                "metadata": {},
            },
            {
                "id": "off_path_region",
                "role": "region",
                "group": "global",
                "region": "off_path",
                "rect": Rect(cx=175, cy=25, width=50, height=50),
                "points": [],
                "weights": {"walk_block": 0.0, "see_block": 0.0, "grouping_strength": 0.0},
                "metadata": {},
            },
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["entry_reachable_region_ratio"] == 1.0
    assert descriptor["path_reachable_region_ratio"] == 0.5

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_path_reachable_region_ratio"]["score"] == 0.5


def test_sampled_walkable_space_uses_room_boundary_domain():
    from features.affordance.models import Rect

    room = {
        "id": "room_boundary",
        "role": "boundary",
        "group": "global",
        "region": "room",
        "rect": Rect(cx=50, cy=50, width=100, height=100),
        "points": [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
        "weights": {"walk_block": 1.0, "see_block": 1.0, "grouping_strength": 1.0},
        "metadata": {"boundary-kind": "room"},
    }
    scene = {
        "source": "synthetic_room_domain",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [room],
        "entries": [
            {
                "id": "entry",
                "role": "opening",
                "group": "global",
                "region": "room",
                "rect": Rect(cx=0, cy=25, width=0, height=50),
                "points": [],
                "weights": {"walk_block": 0.0, "see_block": 0.0, "grouping_strength": 0.0},
                "metadata": {},
            }
        ],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["sampled_walkable_space"]

    assert descriptor["domain_cells"] == 4
    assert descriptor["total_cells"] == 8
    assert descriptor["outside_domain_cells"] == 4
    assert descriptor["walkable_cell_ratio"] == 1.0
    assert descriptor["entry_reachable_cell_ratio"] == 1.0


def test_negative_space_area_ratio_proxy_uses_room_minus_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_area",
        "size": (100.0, 100.0),
        "objects": [
            record("table", "table", Rect(cx=20, cy=25, width=20, height=50)),
        ],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["negative_space"]

    assert descriptor["room_area"] == 10000.0
    assert descriptor["blocker_overlap_area"] == 1000.0
    assert descriptor["negative_space_area"] == 9000.0
    assert descriptor["negative_space_area_ratio_proxy"] == 0.9
    assert descriptor["blocker_evidence"] == ["table"]
    assert "not CAD boolean negative space" in descriptor["uncertainty"]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_area_ratio_proxy"]["score"] == 0.9
    assert (
        path_rows["negative_space_area_ratio_proxy"]["method"]
        == "room_polygon_minus_blocker_union_area_proxy"
    )


def test_negative_space_area_proxy_deduplicates_overlapping_rect_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_overlapping_blockers",
        "size": (100.0, 100.0),
        "objects": [
            record("left_table", "table", Rect(cx=40, cy=50, width=60, height=60)),
            record("right_table", "table", Rect(cx=60, cy=50, width=60, height=60)),
        ],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["blocker_overlap_area"] == 4800.0
    assert descriptor["summed_blocker_overlap_area"] == 7200.0
    assert descriptor["negative_space_area"] == 5200.0
    assert descriptor["negative_space_area_ratio_proxy"] == 0.52
    assert descriptor["component_areas"] == [5200.0]
    assert descriptor["method"] == "room_polygon_minus_blocker_union_area_proxy"


def test_negative_space_free_polygon_adjacency_exposes_shared_edges():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_polygon_adjacency",
        "size": (100.0, 100.0),
        "objects": [
            record("table", "table", Rect(cx=50, cy=50, width=20, height=20)),
        ],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["negative_space"]

    assert len(descriptor["free_space_polygons"]) == 8
    assert descriptor["free_space_polygon_adjacency"] == [
        {
            "component_index": 0,
            "from_cell": 0,
            "to_cell": 1,
            "shared_edge": ((0.0, 40.0), (40.0, 40.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 0,
            "to_cell": 3,
            "shared_edge": ((40.0, 0.0), (40.0, 40.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 1,
            "to_cell": 2,
            "shared_edge": ((0.0, 60.0), (40.0, 60.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 2,
            "to_cell": 4,
            "shared_edge": ((40.0, 60.0), (40.0, 100.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 3,
            "to_cell": 5,
            "shared_edge": ((60.0, 0.0), (60.0, 40.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 4,
            "to_cell": 7,
            "shared_edge": ((60.0, 60.0), (60.0, 100.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 5,
            "to_cell": 6,
            "shared_edge": ((60.0, 40.0), (100.0, 40.0)),
            "length": 40.0,
        },
        {
            "component_index": 0,
            "from_cell": 6,
            "to_cell": 7,
            "shared_edge": ((60.0, 60.0), (100.0, 60.0)),
            "length": 40.0,
        },
    ]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_free_polygon_adjacency_count"]["score"] == 8
    assert (
        path_rows["negative_space_free_polygon_adjacency_count"]["method"]
        == "room_polygon_rect_cell_shared_edge_adjacency_proxy"
    )


def test_negative_space_exports_free_space_polygon_graph():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_free_space_polygon_graph",
        "size": (100.0, 100.0),
        "objects": [record("center_table", "table", Rect(cx=50, cy=50, width=20, height=20))],
        "boundaries": [room],
        "entries": [record("entry", "opening", Rect(cx=0, cy=50, width=0, height=40))],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [record("region", "region", Rect(cx=80, cy=50, width=20, height=20))],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph = matrix["negative_space"]["free_space_polygon_graph"]

    assert graph["method"] == "room_polygon_rect_cell_shared_edge_graph_proxy"
    assert graph["node_count"] == 8
    assert graph["edge_count"] == 8
    assert graph["metrics"] == {
        "component_count": 1,
        "cycle_rank": 1,
        "dead_end_node_count": 0,
        "dead_end_nodes": [],
    }
    assert graph["anchors"] == {
        "entries": [
            {
                "entry_id": "entry",
                "component_index": 0,
                "cell_ids": [
                    "component_0_cell_0",
                    "component_0_cell_1",
                    "component_0_cell_2",
                ],
            }
        ],
        "regions": [
            {
                "region_id": "region",
                "component_index": 0,
                "cell_ids": ["component_0_cell_6"],
            }
        ],
    }
    assert graph["entry_region_distance_evidence"] == [
        {
            "entry_id": "entry",
            "region_id": "region",
            "component_index": 0,
            "entry_cell_id": "component_0_cell_0",
            "region_cell_id": "component_0_cell_6",
            "distance_edges": 3,
            "distance": 90.0,
                        "path_cell_ids": [
                            "component_0_cell_0",
                            "component_0_cell_3",
                            "component_0_cell_5",
                            "component_0_cell_6",
                        ],
                        "path_edge_ids": [
                            "edge_component_0_cell_0_component_0_cell_3",
                            "edge_component_0_cell_3_component_0_cell_5",
                            "edge_component_0_cell_5_component_0_cell_6",
                        ],
                        "min_clearance_width": 40.0,
                    }
                ]
    assert graph["nodes"] == [
        {
            "id": "component_0_cell_0",
            "component_index": 0,
            "cell_index": 0,
            "point": (20.0, 20.0),
            "area": 1600.0,
        },
        {
            "id": "component_0_cell_1",
            "component_index": 0,
            "cell_index": 1,
            "point": (20.0, 50.0),
            "area": 800.0,
        },
        {
            "id": "component_0_cell_2",
            "component_index": 0,
            "cell_index": 2,
            "point": (20.0, 80.0),
            "area": 1600.0,
        },
        {
            "id": "component_0_cell_3",
            "component_index": 0,
            "cell_index": 3,
            "point": (50.0, 20.0),
            "area": 800.0,
        },
        {
            "id": "component_0_cell_4",
            "component_index": 0,
            "cell_index": 4,
            "point": (50.0, 80.0),
            "area": 800.0,
        },
        {
            "id": "component_0_cell_5",
            "component_index": 0,
            "cell_index": 5,
            "point": (80.0, 20.0),
            "area": 1600.0,
        },
        {
            "id": "component_0_cell_6",
            "component_index": 0,
            "cell_index": 6,
            "point": (80.0, 50.0),
            "area": 800.0,
        },
        {
            "id": "component_0_cell_7",
            "component_index": 0,
            "cell_index": 7,
            "point": (80.0, 80.0),
            "area": 1600.0,
        },
    ]
    assert graph["edges"][:2] == [
        {
            "id": "edge_component_0_cell_0_component_0_cell_1",
            "component_index": 0,
            "a": "component_0_cell_0",
            "b": "component_0_cell_1",
            "shared_edge": ((0, 40), (40, 40)),
            "length": 40.0,
            "clearance_width": 40.0,
            "weight": 30.0,
            "distance": 30.0,
        },
        {
            "id": "edge_component_0_cell_0_component_0_cell_3",
            "component_index": 0,
            "a": "component_0_cell_0",
            "b": "component_0_cell_3",
            "shared_edge": ((40, 0), (40, 40)),
            "length": 40.0,
            "clearance_width": 40.0,
            "weight": 30.0,
            "distance": 30.0,
        },
    ]
    assert (
        graph["uncertainty"]
        == "shared-edge graph over rect-cell free-space polygons; proxy, not navmesh or medial-axis topology"
    )
    assert (
        matrix["adapter_payload"]["evidence_geometry"]["free_space_polygon_graph"]
        == graph
    )
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["free_space_polygon_graph_cycle_rank"] == {
        "view_id": "path_connectivity",
        "metric": "free_space_polygon_graph_cycle_rank",
        "score": 1,
        "status": "computed",
        "method": "room_polygon_rect_cell_shared_edge_graph_proxy",
        "evidence": {
            "node_count": 8,
            "edge_count": 8,
            "component_count": 1,
            "dead_end_nodes": [],
        },
        "uncertainty": "cycle rank over rect-cell free-space graph; proxy, not navmesh loop topology or medial-axis routing",
    }
    assert path_rows["free_space_polygon_graph_mean_entry_region_distance"] == {
        "view_id": "path_connectivity",
        "metric": "free_space_polygon_graph_mean_entry_region_distance",
        "score": 90.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_shared_edge_graph_distance_proxy",
        "evidence": graph["entry_region_distance_evidence"],
        "uncertainty": "shortest center-to-center distance over rect-cell free-space graph; proxy, not navmesh, medial-axis, or certified route distance",
    }
    assert path_rows["free_space_polygon_graph_mean_edge_clearance_width"] == {
        "view_id": "path_connectivity",
        "metric": "free_space_polygon_graph_mean_edge_clearance_width",
        "score": 40.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_shared_edge_width_proxy",
        "evidence": [
            {
                "edge_id": edge["id"],
                "a": edge["a"],
                "b": edge["b"],
                "clearance_width": edge["clearance_width"],
                "weight": edge["weight"],
            }
            for edge in graph["edges"]
        ],
        "uncertainty": "shared-edge length over rect-cell free-space graph; proxy, not medial-axis clearance, navmesh portal width, or code-compliant passage width",
    }
    assert path_rows["free_space_polygon_graph_mean_entry_region_min_clearance_width"] == {
        "view_id": "path_connectivity",
        "metric": "free_space_polygon_graph_mean_entry_region_min_clearance_width",
        "score": 40.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_shared_edge_path_bottleneck_width_proxy",
        "evidence": graph["entry_region_distance_evidence"],
        "uncertainty": "minimum shared-edge width along rect-cell entry-region paths; proxy, not medial-axis clearance, navmesh portal bottleneck, or egress capacity",
    }
    assert path_rows["inferred_gap_path_width_free_space_clearance_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "inferred_gap_path_width_free_space_clearance_ratio",
        "score": None,
        "status": "not_available",
        "method": "free_space_edge_clearance_width_over_inferred_gap_band_width",
        "evidence": {
            "free_space_mean_edge_clearance_width": 40.0,
            "walkable_proxy_mean_thickness": None,
            "walkable_proxy_min_thickness": None,
            "walkable_proxy_edge_count": 0,
        },
        "uncertainty": "ratio between rect-cell free-space shared-edge width and inferred gap-band width; proxy consistency check, not route certification",
    }


def test_free_space_polygon_graph_reports_widest_entry_region_path():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_free_space_widest_path",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "upper_wall",
                "boundary",
                Rect(cx=50, cy=22.5, width=10, height=45),
                kind="wall",
                walk_block=1.0,
            ),
            record(
                "middle_wall",
                "boundary",
                Rect(cx=50, cy=57.5, width=10, height=5),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=10)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [
            record("region", "region", Rect(cx=95, cy=50, width=10, height=10)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph = matrix["negative_space"]["free_space_polygon_graph"]

    assert graph["entry_region_distance_evidence"][0]["min_clearance_width"] == 10.0
    assert graph["entry_region_widest_path_evidence"] == [
        {
            "entry_id": "entry",
            "region_id": "region",
            "component_index": 0,
            "entry_cell_id": "component_0_cell_2",
            "region_cell_id": "component_0_cell_7",
            "widest_clearance_width": 40.0,
            "path_cell_ids": [
                "component_0_cell_2",
                "component_0_cell_3",
                "component_0_cell_5",
                "component_0_cell_9",
                "component_0_cell_8",
                "component_0_cell_7",
            ],
            "path_edge_ids": [
                "edge_component_0_cell_2_component_0_cell_3",
                "edge_component_0_cell_3_component_0_cell_5",
                "edge_component_0_cell_5_component_0_cell_9",
                "edge_component_0_cell_8_component_0_cell_9",
                "edge_component_0_cell_7_component_0_cell_8",
            ],
        }
    ]
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["free_space_polygon_graph_mean_entry_region_widest_clearance_width"] == {
        "view_id": "path_connectivity",
        "metric": "free_space_polygon_graph_mean_entry_region_widest_clearance_width",
        "score": 40.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_shared_edge_widest_path_width_proxy",
        "evidence": graph["entry_region_widest_path_evidence"],
        "uncertainty": "max-min shared-edge width over rect-cell entry-region paths; proxy, not medial-axis clearance, navmesh routing, or egress capacity",
    }


def test_free_space_polygon_graph_widest_path_ignores_zero_edge_paths():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_free_space_zero_edge_widest_path",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [room],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [
            record("region", "region", Rect(cx=50, cy=50, width=20, height=20)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph = matrix["negative_space"]["free_space_polygon_graph"]
    widest = graph["entry_region_widest_path_evidence"][0]

    assert widest["path_edge_ids"] == []
    assert widest["widest_clearance_width"] is None
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert (
        path_rows[
            "free_space_polygon_graph_mean_entry_region_widest_clearance_width"
        ]["status"]
        == "not_available"
    )


def test_negative_space_component_proxy_splits_room_by_full_height_blocker():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    path = record("path", "path", Rect(cx=100, cy=50, width=200, height=100))
    path["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_components",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [],
        "paths": [path],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["negative_space"]

    assert descriptor["negative_space_area"] == 18000.0
    assert descriptor["component_count"] == 2
    assert descriptor["component_areas"] == [9000.0, 9000.0]
    assert descriptor["component_area_total"] == 18000.0
    assert descriptor["component_cell_count_total"] == 2
    assert descriptor["component_cell_area_sum_total"] == 18000.0
    assert descriptor["negative_space_component_area_residual"] == 0.0
    assert descriptor["negative_space_component_area_residual_ratio"] == 0.0
    assert descriptor["component_rects"] == [
        {
            "component_index": 0,
            "bbox": (0.0, 0.0, 90.0, 100.0),
            "cell_count": 1,
            "area": 9000.0,
            "cell_rects": [
                {
                    "bbox": (0.0, 0.0, 90.0, 100.0),
                    "area": 9000.0,
                },
            ],
        },
        {
            "component_index": 1,
            "bbox": (110.0, 0.0, 200.0, 100.0),
            "cell_count": 1,
            "area": 9000.0,
            "cell_rects": [
                {
                    "bbox": (110.0, 0.0, 200.0, 100.0),
                    "area": 9000.0,
                },
            ],
        },
    ]
    assert descriptor["free_space_polygons"] == [
        {
            "component_index": 0,
            "cell_index": 0,
            "points": ((0.0, 0.0), (90.0, 0.0), (90.0, 100.0), (0.0, 100.0)),
            "area": 9000.0,
        },
        {
            "component_index": 1,
            "cell_index": 0,
            "points": (
                (110.0, 0.0),
                (200.0, 0.0),
                (200.0, 100.0),
                (110.0, 100.0),
            ),
            "area": 9000.0,
        },
    ]
    assert descriptor["largest_component_area_ratio"] == 0.5
    assert descriptor["component_method"] == "room_polygon_rect_cell_decomposition_proxy"

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_component_count"]["score"] == 2
    assert path_rows["negative_space_component_count"]["component_rects"] == descriptor[
        "component_rects"
    ]
    assert path_rows["negative_space_component_count"]["component_area_total"] == 18000.0
    assert (
        path_rows["negative_space_free_polygon_count"]["score"]
        == len(descriptor["free_space_polygons"])
    )
    assert path_rows["negative_space_free_polygon_count"]["free_space_polygons"] == descriptor[
        "free_space_polygons"
    ]
    assert (
        path_rows["negative_space_free_polygon_count"]["method"]
        == "room_polygon_rect_cell_free_space_polygons_proxy"
    )
    assert (
        path_rows["negative_space_room_minus_blocker_polygon_count"]["score"]
        == len(descriptor["room_minus_blocker_polygons"])
    )
    assert (
        path_rows["negative_space_room_minus_blocker_polygon_count"][
            "room_minus_blocker_polygons"
        ]
        == descriptor["room_minus_blocker_polygons"]
    )
    assert (
        path_rows["negative_space_room_minus_blocker_polygon_count"]["method"]
        == "rect_cell_room_minus_blocker_boundary_union_proxy"
    )
    assert (
        path_rows["negative_space_component_count"]["component_cell_area_sum_total"]
        == 18000.0
    )
    assert (
        path_rows["negative_space_component_count"][
            "negative_space_component_area_residual"
        ]
        == 0.0
    )
    assert path_rows["negative_space_component_area_residual_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_component_area_residual_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_decomposition_proxy",
        "evidence": {
            "negative_space_area": 18000.0,
            "component_area_total": 18000.0,
            "component_cell_area_sum_total": 18000.0,
            "negative_space_component_area_residual": 0.0,
        },
        "uncertainty": "descriptor-level closure check between negative-space area and rect-cell components; not CAD boolean validation",
    }
    assert path_rows["negative_space_largest_component_area_ratio"]["score"] == 0.5


def test_negative_space_component_proxy_marks_entry_connected_components():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    path = record("path", "path", Rect(cx=100, cy=50, width=200, height=100))
    path["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_entry_components",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [path],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["negative_space"]

    assert descriptor["entry_connected_component_count"] == 1
    assert descriptor["entry_connected_component_area"] == 9000.0
    assert descriptor["entry_connected_area_ratio"] == 0.5
    assert descriptor["non_entry_connected_component_area"] == 9000.0
    assert descriptor["non_entry_connected_area_ratio"] == 0.5
    assert descriptor["entry_component_evidence"] == [
        {
            "component_index": 0,
            "area": 9000.0,
            "entry_ids": ["left_entry"],
        },
        {
            "component_index": 1,
            "area": 9000.0,
            "entry_ids": [],
        },
    ]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_entry_connected_component_count"]["score"] == 1
    assert path_rows["negative_space_entry_connected_area_ratio"]["score"] == 0.5
    assert path_rows["negative_space_non_entry_connected_area_ratio"]["score"] == 0.5
    assert (
        path_rows["negative_space_non_entry_connected_area_ratio"]["method"]
        == "room_polygon_rect_cell_decomposition_proxy"
    )
    assert path_rows["candidate_path_area_ratio_proxy"]["score"] == 0.5
    assert path_rows["candidate_path_area_ratio_proxy"]["candidate_path_inputs"] == {
        "negative_space_entry_connected_area_ratio": 0.5,
        "path_width_continuity": 1.0,
    }


def test_negative_space_graph_exposes_entry_component_edges():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_graph",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=200, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph = matrix["negative_space_graph"]

    assert [node["kind"] for node in graph["nodes"]] == [
        "negative_space_component",
        "negative_space_component",
        "entry",
    ]
    component_nodes = [
        node for node in graph["nodes"]
        if node["kind"] == "negative_space_component"
    ]
    assert component_nodes == [
        {
            "id": "node_negative_space_component_0",
            "kind": "negative_space_component",
            "ref_id": "component_0",
            "component_index": 0,
            "area": 9000.0,
            "point": (45.0, 50.0),
            "bbox": (0.0, 0.0, 90.0, 100.0),
            "cell_count": 1,
            "cell_rects": [
                {
                    "bbox": (0.0, 0.0, 90.0, 100.0),
                    "area": 9000.0,
                },
            ],
        },
        {
            "id": "node_negative_space_component_1",
            "kind": "negative_space_component",
            "ref_id": "component_1",
            "component_index": 1,
            "area": 9000.0,
            "point": (155.0, 50.0),
            "bbox": (110.0, 0.0, 200.0, 100.0),
            "cell_count": 1,
            "cell_rects": [
                {
                    "bbox": (110.0, 0.0, 200.0, 100.0),
                    "area": 9000.0,
                },
            ],
        },
    ]
    assert graph["edges"] == [
        {
            "id": "edge_entry_negative_space_component_left_entry_component_0",
            "kind": "entry_negative_space_component_touch",
            "a": "node_entry_left_entry",
            "b": "node_negative_space_component_0",
            "refs": {"entry": "left_entry", "component": 0},
        }
    ]
    assert graph["metrics"] == {
        "node_count": 3,
        "edge_count": 1,
        "component_node_count": 2,
        "entry_node_count": 1,
        "region_node_count": 0,
        "entry_component_edge_count": 1,
        "region_component_edge_count": 0,
        "entry_connected_component_ids": [0],
        "non_entry_connected_component_ids": [1],
        "entry_connected_component_ratio": 0.5,
        "component_area": 18000.0,
        "entry_connected_component_area": 9000.0,
        "non_entry_connected_component_area": 9000.0,
        "entry_connected_area_ratio": 0.5,
        "non_entry_connected_area_ratio": 0.5,
        "entry_connected_region_ids": [],
        "non_entry_connected_region_ids": [],
        "entry_connected_region_ratio": 0.0,
        "entry_connected_region_pair_count": 0,
        "total_region_pair_count": 0,
        "entry_connected_region_pair_ratio": 0.0,
        "entry_connected_region_pair_evidence": [],
        "unconnected_region_pair_evidence": [],
        "component_cell_counts": {0: 1, 1: 1},
        "component_cell_area_sums": {0: 9000.0, 1: 9000.0},
        "component_cell_area_residuals": {0: 0.0, 1: 0.0},
        "max_component_cell_area_residual_ratio": 0.0,
        "entry_region_free_polygon_distance_evidence": [],
        "mean_entry_region_free_polygon_distance": None,
        "mean_entry_region_free_polygon_path_length": None,
    }

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_entry_connected_component_count"]["evidence"] == [
        "edge_entry_negative_space_component_left_entry_component_0"
    ]
    assert path_rows["negative_space_component_cell_area_residual_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_component_cell_area_residual_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "room_polygon_rect_cell_decomposition_proxy",
        "evidence": {0: 0.0, 1: 0.0},
        "component_cell_counts": {0: 1, 1: 1},
        "component_cell_area_sums": {0: 9000.0, 1: 9000.0},
        "uncertainty": "internal rect-cell area closure check for negative-space component evidence; not CAD boolean validation",
    }
    assert path_rows["negative_space_entry_connected_component_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_entry_connected_component_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "room_polygon_rect_cell_decomposition_proxy",
        "evidence": [
            "edge_entry_negative_space_component_left_entry_component_0"
        ],
        "entry_connected_component_ids": [0],
        "non_entry_connected_component_ids": [1],
        "uncertainty": "share of decomposed negative-space components touching entries; rect-touch proxy, not navmesh component reachability",
    }


def test_negative_space_graph_reports_entry_connected_region_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_region_graph",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=200, height=100)),
        ],
        "regions": [
            record("left_region", "region", Rect(cx=45, cy=50, width=90, height=100)),
            record("right_region", "region", Rect(cx=155, cy=50, width=90, height=100)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph = matrix["negative_space_graph"]
    component_region_edges = [
        edge for edge in graph["edges"]
        if edge["kind"] == "negative_space_component_region_touch"
    ]

    assert component_region_edges == [
        {
            "id": "edge_negative_space_component_region_component_0_left_region",
            "kind": "negative_space_component_region_touch",
            "a": "node_negative_space_component_0",
            "b": "node_region_left_region",
            "refs": {"component": 0, "region": "left_region"},
            "overlap_area": 9000.0,
            "region_area_ratio": 1.0,
        },
        {
            "id": "edge_negative_space_component_region_component_1_right_region",
            "kind": "negative_space_component_region_touch",
            "a": "node_negative_space_component_1",
            "b": "node_region_right_region",
            "refs": {"component": 1, "region": "right_region"},
            "overlap_area": 9000.0,
            "region_area_ratio": 1.0,
        },
    ]
    assert graph["metrics"]["entry_connected_region_ids"] == ["left_region"]
    assert graph["metrics"]["non_entry_connected_region_ids"] == ["right_region"]
    assert graph["metrics"]["entry_connected_region_ratio"] == 0.5

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_entry_connected_region_ratio"]["score"] == 0.5
    assert path_rows["negative_space_entry_connected_region_ratio"]["evidence"] == [
        "edge_negative_space_component_region_component_0_left_region"
    ]
    assert path_rows["negative_space_entry_connected_region_ratio"][
        "entry_connected_region_ids"
    ] == ["left_region"]
    assert path_rows["negative_space_entry_connected_region_ratio"][
        "non_entry_connected_region_ids"
    ] == ["right_region"]


def test_negative_space_graph_reports_entry_to_region_free_polygon_distance():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_region_cell_distance",
        "size": (100.0, 100.0),
        "objects": [
            record("table", "table", Rect(cx=50, cy=50, width=20, height=20)),
        ],
        "boundaries": [room],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=20, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [
            record("near_region", "region", Rect(cx=20, cy=20, width=20, height=20)),
            record("far_region", "region", Rect(cx=80, cy=80, width=20, height=20)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    metrics = matrix["negative_space_graph"]["metrics"]

    assert metrics["entry_region_free_polygon_distance_evidence"] == [
        {
            "region_id": "far_region",
            "component_index": 0,
            "entry_cell": 0,
            "region_cell": 7,
            "distance_edges": 4,
            "path_cells": [0, 1, 2, 4, 7],
            "distance": 120.0,
        },
        {
            "region_id": "near_region",
            "component_index": 0,
            "entry_cell": 0,
            "region_cell": 0,
            "distance_edges": 0,
            "path_cells": [0],
            "distance": 0.0,
        },
    ]
    assert metrics["mean_entry_region_free_polygon_distance"] == 2.0
    assert metrics["mean_entry_region_free_polygon_path_length"] == 60.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_mean_entry_region_free_polygon_distance"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_mean_entry_region_free_polygon_distance",
        "score": 2.0,
        "status": "computed",
        "method": "entry_to_region_rect_cell_adjacency_shortest_path_proxy",
        "evidence": ["far_region", "near_region"],
        "entry_region_free_polygon_distance_evidence": metrics[
            "entry_region_free_polygon_distance_evidence"
        ],
        "uncertainty": "shortest edge count over rect-cell free-space adjacency; proxy, not navmesh, medial-axis, or route-quality distance",
    }
    assert path_rows["negative_space_mean_entry_region_free_polygon_path_length"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_mean_entry_region_free_polygon_path_length",
        "score": 60.0,
        "status": "computed",
        "method": "entry_to_region_rect_cell_centerline_length_proxy",
        "evidence": ["far_region", "near_region"],
        "entry_region_free_polygon_distance_evidence": metrics[
            "entry_region_free_polygon_distance_evidence"
        ],
        "uncertainty": "center-to-center length over rect-cell free-space path_cells; proxy, not navmesh polyline, medial-axis path, or route-quality distance",
    }


def test_negative_space_graph_reports_entry_connected_region_pair_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    path = record("path", "path", Rect(cx=100, cy=50, width=200, height=100))
    path["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_region_pairs",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [path],
        "regions": [
            record("left_upper_region", "region", Rect(cx=45, cy=25, width=90, height=50)),
            record("left_lower_region", "region", Rect(cx=45, cy=75, width=90, height=50)),
            record("right_region", "region", Rect(cx=155, cy=50, width=90, height=100)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    graph_metrics = matrix["negative_space_graph"]["metrics"]
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    assert graph_metrics["entry_connected_region_pair_count"] == 1
    assert graph_metrics["total_region_pair_count"] == 3
    assert graph_metrics["entry_connected_region_pair_ratio"] == 0.3333
    assert graph_metrics["entry_connected_region_pair_evidence"] == [
        {
            "component": 0,
            "region_a": "left_lower_region",
            "region_b": "left_upper_region",
        }
    ]
    assert graph_metrics["unconnected_region_pair_evidence"] == [
        {
            "region_a": "left_lower_region",
            "region_b": "right_region",
        },
        {
            "region_a": "left_upper_region",
            "region_b": "right_region",
        },
    ]
    assert path_rows["negative_space_entry_connected_region_ratio"]["score"] == 0.6667
    assert path_rows["negative_space_entry_connected_region_pair_ratio"]["score"] == 0.3333
    assert (
        path_rows["negative_space_entry_connected_region_pair_ratio"][
            "region_pair_evidence"
        ]
        == graph_metrics["entry_connected_region_pair_evidence"]
    )
    assert (
        path_rows["negative_space_entry_connected_region_pair_ratio"][
            "entry_connected_region_pair_count"
        ]
        == 1
    )
    assert (
        path_rows["negative_space_entry_connected_region_pair_ratio"][
            "total_region_pair_count"
        ]
        == 3
    )
    assert (
        path_rows["negative_space_entry_connected_region_pair_ratio"][
            "unconnected_region_pair_evidence"
        ]
        == graph_metrics["unconnected_region_pair_evidence"]
    )
    assert path_rows["candidate_path_region_pair_ratio_proxy"]["score"] == 0.1667
    assert path_rows["candidate_path_region_pair_ratio_proxy"]["candidate_path_pair_inputs"] == {
        "candidate_path_area_ratio_proxy": 0.5,
        "negative_space_entry_connected_region_pair_ratio": 0.3333,
        "entry_connected_region_pair_count": 1,
        "total_region_pair_count": 3,
    }


def test_negative_space_graph_reports_entry_connected_region_area_coverage():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_negative_space_region_area",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=200, height=100)),
        ],
        "regions": [
            record("spanning_region", "region", Rect(cx=90, cy=50, width=180, height=100)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    assert (
        path_rows["negative_space_entry_connected_region_area_coverage_ratio"]["score"]
        == 0.5
    )
    assert path_rows["negative_space_entry_connected_region_area_coverage_ratio"][
        "region_area_coverage_evidence"
    ] == [
        {
            "region": "spanning_region",
            "entry_connected_area": 9000.0,
            "region_area": 18000,
            "coverage_ratio": 0.5,
            "components": [0],
            "edge_ids": [
                "edge_negative_space_component_region_component_0_spanning_region"
            ],
        }
    ]


def test_negative_space_component_proxy_clips_area_to_room_polygon():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_triangular_room_components",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["room_area"] == 5000.0
    assert descriptor["negative_space_area"] == 5000.0
    assert descriptor["component_count"] == 1
    assert descriptor["component_areas"] == [5000.0]
    assert descriptor["largest_component_area_ratio"] == 1.0
    assert descriptor["component_method"] == "room_polygon_rect_cell_decomposition_proxy"


def test_negative_space_proxy_uses_polygon_blocker_area_when_available():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    blocker = record(
        "triangle_fixture",
        "fixture",
        Rect(cx=50, cy=50, width=100, height=100),
    )
    blocker["points"] = [(0, 0), (100, 0), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_polygon_blocker",
        "size": (100.0, 100.0),
        "objects": [blocker],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["room_area"] == 10000.0
    assert descriptor["blocker_overlap_area"] == 5000.0
    assert descriptor["negative_space_area"] == 5000.0
    assert descriptor["component_areas"] == [5000.0]
    assert descriptor["blocker_overlap_samples"] == [
        {
            "target_id": "triangle_fixture",
            "target_role": "fixture",
            "area": 5000.0,
        }
    ]


def test_negative_space_union_area_sums_separate_polygon_blockers_in_same_cell():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    left = record("left_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    left["points"] = [(0, 0), (50, 0), (0, 100), (0, 0)]
    right = record("right_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    right["points"] = [(100, 0), (100, 100), (50, 100), (100, 0)]
    scene = {
        "source": "synthetic_separate_polygon_blockers",
        "size": (100.0, 100.0),
        "objects": [left, right],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["blocker_overlap_area"] == 5000.0
    assert descriptor["summed_blocker_overlap_area"] == 5000.0
    assert descriptor["negative_space_area"] == 5000.0
    assert descriptor["component_areas"] == [5000.0]


def test_negative_space_union_area_deduplicates_identical_polygon_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    first = record("first_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    first["points"] = [(0, 0), (100, 0), (0, 100), (0, 0)]
    second = record("second_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    second["points"] = [(0, 0), (100, 0), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_duplicate_polygon_blockers",
        "size": (100.0, 100.0),
        "objects": [first, second],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["blocker_overlap_area"] == 5000.0
    assert descriptor["summed_blocker_overlap_area"] == 10000.0
    assert descriptor["negative_space_area"] == 5000.0
    assert descriptor["component_areas"] == [5000.0]


def test_negative_space_proxy_flags_overlapping_nonidentical_polygon_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    first = record("first_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    first["points"] = [(0, 0), (100, 0), (0, 100), (0, 0)]
    second = record("second_triangle", "fixture", Rect(cx=50, cy=50, width=100, height=100))
    second["points"] = [(100, 0), (100, 100), (0, 0), (100, 0)]
    scene = {
        "source": "synthetic_overlapping_polygon_blockers",
        "size": (100.0, 100.0),
        "objects": [first, second],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["negative_space"]

    assert descriptor["polygon_blocker_overlap_risk_evidence"] == [
        {
            "blocker_a": "first_triangle",
            "blocker_b": "second_triangle",
            "reason": "nonidentical_polygon_blockers_overlap",
        }
    ]
    path_rows = {
        row["metric"]: row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_polygon_overlap_risk_count"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_polygon_overlap_risk_count",
        "score": 1,
        "status": "computed",
        "method": "nonidentical_polygon_blocker_overlap_detection",
        "evidence": [
            {
                "blocker_a": "first_triangle",
                "blocker_b": "second_triangle",
                "reason": "nonidentical_polygon_blockers_overlap",
            }
        ],
        "uncertainty": "overlapping nonidentical polygon blockers exceed the current rect-cell union proxy; use CAD boolean geometry before treating area/topology as final",
    }


def test_negative_space_exports_room_minus_blocker_boundary_polygons_with_holes():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    table = record("center_table", "table", Rect(cx=50, cy=50, width=20, height=20))
    scene = {
        "source": "synthetic_room_minus_blocker_polygons",
        "size": (100.0, 100.0),
        "objects": [table],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["negative_space"]

    assert descriptor["room_minus_blocker_polygons"] == [
        {
            "component_index": 0,
            "outer_ring": ((0, 0), (100, 0), (100, 100), (0, 100)),
            "holes": (((40, 40), (40, 60), (60, 60), (60, 40)),),
            "area": 9600.0,
            "cell_count": 8,
        }
    ]
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["negative_space_room_minus_blocker_polygon_count"] == {
        "view_id": "path_connectivity",
        "metric": "negative_space_room_minus_blocker_polygon_count",
        "score": 1,
        "status": "computed",
        "method": "rect_cell_room_minus_blocker_boundary_union_proxy",
        "evidence": ["component_0"],
        "room_minus_blocker_polygons": descriptor["room_minus_blocker_polygons"],
        "uncertainty": "merged boundary loops over rect-cell negative-space components; proxy, not CAD boolean room-minus-blocker topology",
    }


def test_negative_space_exports_shapely_room_minus_blocker_polygons():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_shapely_room_minus_blocker",
        "size": (100.0, 100.0),
        "objects": [
            record("center_table", "table", Rect(cx=50, cy=50, width=20, height=20)),
        ],
        "boundaries": [room],
        "entries": [],
        "paths": [record("path", "path", Rect(cx=50, cy=50, width=100, height=100))],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    cad_polygons = matrix["negative_space"]["cad_room_minus_blocker_polygons"]

    assert cad_polygons == [
        {
            "component_index": 0,
            "outer_ring": ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)),
            "holes": (((40.0, 40.0), (40.0, 60.0), (60.0, 60.0), (60.0, 40.0)),),
            "area": 9600.0,
            "source": "shapely_difference",
        }
    ]
    assert matrix["negative_space"]["cad_room_minus_blocker_area_total"] == 9600.0
    assert matrix["negative_space"]["cad_room_minus_blocker_area_residual"] == 0.0
    assert matrix["negative_space"]["cad_room_minus_blocker_area_residual_ratio"] == 0.0
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["cad_room_minus_blocker_polygon_count"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_polygon_count",
        "score": 1,
        "status": "computed",
        "method": "shapely_room_polygon_difference_blocker_union",
        "evidence": ["component_0"],
        "cad_room_minus_blocker_polygons": cad_polygons,
        "uncertainty": "Shapely polygon difference over current authored room/blocker polygons; still not Rhino/VisualARQ hosted topology or navmesh faces",
    }
    assert path_rows["cad_room_minus_blocker_area_residual_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_area_residual_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "shapely_room_minus_blocker_area_minus_negative_space_area",
        "evidence": {
            "cad_room_minus_blocker_area_total": 9600.0,
            "negative_space_area": 9600.0,
            "cad_room_minus_blocker_area_residual": 0.0,
        },
        "uncertainty": "area closure check between Shapely polygon difference and current negative-space area proxy; flags disagreement but is not Rhino/BIM/navmesh validation",
    }
    assert path_rows["cad_room_minus_blocker_largest_component_area_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_largest_component_area_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "shapely_largest_component_area_over_total_free_area",
        "evidence": {
            "largest_component_area": 9600.0,
            "cad_room_minus_blocker_area_total": 9600.0,
            "component_areas": [9600.0],
        },
        "uncertainty": "largest Shapely free-space component area share; fragmentation severity only, not route reachability or route quality",
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_area_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_area_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "shapely_component_entry_touched_area_ratio_proxy",
        "evidence": {
            "entry_connected_component_ids": [],
            "non_entry_connected_component_ids": [0],
            "entry_connected_component_area": 0,
            "non_entry_connected_component_area": 9600.0,
            "cad_room_minus_blocker_area_total": 9600.0,
        },
        "uncertainty": "entry-touched Shapely component area share; component-level evidence only, not route reachability or route quality",
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_component_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_component_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "shapely_component_entry_touched_component_count_proxy",
        "evidence": {
            "entry_connected_component_ids": [],
            "non_entry_connected_component_ids": [0],
            "component_count": 1,
        },
        "uncertainty": "entry-touched Shapely component count share; component-level evidence only, not route reachability or route quality",
    }


def test_cad_room_minus_blocker_components_report_entry_region_touches():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=100, cy=50, width=200, height=100),
        kind="room",
        walk_block=1.0,
    )
    room["points"] = [(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)]
    scene = {
        "source": "synthetic_cad_room_minus_blocker_touches",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            room,
            record(
                "split_wall",
                "boundary",
                Rect(cx=100, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=200, height=100)),
        ],
        "regions": [
            record("left_region", "region", Rect(cx=45, cy=50, width=90, height=100)),
            record("right_region", "region", Rect(cx=155, cy=50, width=90, height=100)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    touch_evidence = matrix["negative_space"][
        "cad_room_minus_blocker_component_touch_evidence"
    ]

    assert touch_evidence == [
        {
            "component_index": 0,
            "entry_ids": ["left_entry"],
            "region_ids": ["left_region"],
            "region_overlap_areas": {"left_region": 9000.0},
        },
        {
            "component_index": 1,
            "entry_ids": [],
            "region_ids": ["right_region"],
            "region_overlap_areas": {"right_region": 9000.0},
        },
    ]
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_region_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_region_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "shapely_component_entry_region_touch_proxy",
        "evidence": ["left_region"],
        "entry_connected_region_ids": ["left_region"],
        "non_entry_connected_region_ids": ["right_region"],
        "cad_room_minus_blocker_component_touch_evidence": touch_evidence,
        "uncertainty": "Shapely component touch/overlap evidence over current authored polygons; not hosted doorway topology, navmesh reachability, or route quality",
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_area_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_area_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "shapely_component_entry_touched_area_ratio_proxy",
        "evidence": {
            "entry_connected_component_ids": [0],
            "non_entry_connected_component_ids": [1],
            "entry_connected_component_area": 9000.0,
            "non_entry_connected_component_area": 9000.0,
            "cad_room_minus_blocker_area_total": 18000.0,
        },
        "uncertainty": "entry-touched Shapely component area share; component-level evidence only, not route reachability or route quality",
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_component_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_component_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "shapely_component_entry_touched_component_count_proxy",
        "evidence": {
            "entry_connected_component_ids": [0],
            "non_entry_connected_component_ids": [1],
            "component_count": 2,
        },
        "uncertainty": "entry-touched Shapely component count share; component-level evidence only, not route reachability or route quality",
    }
    assert path_rows["cad_room_minus_blocker_largest_component_area_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_largest_component_area_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "shapely_largest_component_area_over_total_free_area",
        "evidence": {
            "largest_component_area": 9000.0,
            "cad_room_minus_blocker_area_total": 18000.0,
            "component_areas": [9000.0, 9000.0],
        },
        "uncertainty": "largest Shapely free-space component area share; fragmentation severity only, not route reachability or route quality",
    }
    assert path_rows["cad_room_minus_blocker_entry_connected_region_pair_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_entry_connected_region_pair_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "shapely_component_entry_connected_region_pair_proxy",
        "evidence": [],
        "region_pair_evidence": [],
        "entry_connected_region_pair_count": 0,
        "total_region_pair_count": 1,
        "uncertainty": "region pairs sharing an entry-touched Shapely component; component-level evidence only, not route reachability or route quality",
    }


def test_sampled_walkable_space_reports_component_fragmentation():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_components",
        "size": (150.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=50, width=150, height=100),
                kind="room",
                walk_block=1.0,
            ),
            record(
                "split_wall",
                "boundary",
                Rect(cx=75, cy=50, width=50, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    descriptor = evaluate_scene(scene)["sampled_walkable_space"]

    assert descriptor["walkable_cells"] == 4
    assert descriptor["component_count"] == 2
    assert descriptor["largest_component_cell_ratio"] == 0.5
    assert descriptor["entry_reachable_component_ratio"] == 0.5


def test_sampled_walkable_space_reports_clearance_to_walk_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_sampled_clearance",
        "size": (100.0, 100.0),
        "objects": [
            record(
                "central_blocker",
                "fixture",
                Rect(cx=50, cy=50, width=20, height=20),
                walk_block=1.0,
            ),
        ],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=50, cy=50, width=100, height=100),
                kind="room",
                walk_block=1.0,
            )
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=90, width=80, height=10)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["sampled_clearance_to_walk_blockers"] == {
        "method": "sampled_free_cell_center_to_nearest_walk_blocker_gap",
        "min_clearance": 10.0,
        "mean_clearance": 26.6357,
        "sample_count": 24,
        "zero_clearance_sample_count": 0,
        "min_clearance_samples": [
            {
                "cell": (1, 2),
                "point": (50.0, 30.0),
                "blocker_id": "central_blocker",
                "distance": 10.0,
            },
            {
                "cell": (2, 1),
                "point": (30.0, 50.0),
                "blocker_id": "central_blocker",
                "distance": 10.0,
            },
            {
                "cell": (2, 3),
                "point": (70.0, 50.0),
                "blocker_id": "central_blocker",
                "distance": 10.0,
            },
            {
                "cell": (3, 2),
                "point": (50.0, 70.0),
                "blocker_id": "central_blocker",
                "distance": 10.0,
            },
        ],
        "blocker_evidence": ["central_blocker"],
    }

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_min_clearance_to_walk_blocker"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_min_clearance_to_walk_blocker",
        "score": 10.0,
        "status": "computed",
        "method": "sampled_free_cell_center_to_nearest_walk_blocker_gap",
        "evidence": ["central_blocker"],
        "clearance": descriptor["sampled_clearance_to_walk_blockers"],
        "uncertainty": "sampled free-cell center clearance to walk blockers; proxy, not medial-axis width field or navmesh clearance",
    }
    assert path_rows["sampled_zero_clearance_cell_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_zero_clearance_cell_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "sampled_zero_clearance_cells_over_clearance_samples",
        "evidence": descriptor["sampled_clearance_to_walk_blockers"]["min_clearance_samples"],
        "clearance": descriptor["sampled_clearance_to_walk_blockers"],
        "uncertainty": "share of sampled free cells whose center has zero clearance to a walk blocker; flags occupancy-threshold disagreement, not final geometry truth",
    }


def test_sampled_walkable_space_reports_entry_reachable_clearance_only():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_entry_reachable_clearance",
        "size": (100.0, 100.0),
        "objects": [
            record(
                "right_blocker",
                "fixture",
                Rect(cx=90, cy=50, width=20, height=20),
                walk_block=1.0,
            ),
        ],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=50, cy=50, width=100, height=100),
                kind="room",
                walk_block=1.0,
            ),
            record(
                "split_wall",
                "boundary",
                Rect(cx=50, cy=50, width=20, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=20, cy=90, width=20, height=10)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["entry_reachable_clearance_to_walk_blockers"] == {
        "method": "sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap",
        "min_clearance": 10.0,
        "mean_clearance": 20.0,
        "sample_count": 10,
        "zero_clearance_sample_count": 0,
        "min_clearance_samples": [
            {
                "cell": (0, 1),
                "point": (30.0, 10.0),
                "blocker_id": "split_wall",
                "distance": 10.0,
            },
            {
                "cell": (1, 1),
                "point": (30.0, 30.0),
                "blocker_id": "split_wall",
                "distance": 10.0,
            },
            {
                "cell": (2, 1),
                "point": (30.0, 50.0),
                "blocker_id": "split_wall",
                "distance": 10.0,
            },
            {
                "cell": (3, 1),
                "point": (30.0, 70.0),
                "blocker_id": "split_wall",
                "distance": 10.0,
            },
            {
                "cell": (4, 1),
                "point": (30.0, 90.0),
                "blocker_id": "split_wall",
                "distance": 10.0,
            },
        ],
        "blocker_evidence": ["right_blocker", "split_wall"],
    }

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_entry_reachable_min_clearance_to_walk_blocker"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_entry_reachable_min_clearance_to_walk_blocker",
        "score": 10.0,
        "status": "computed",
        "method": "sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap",
        "evidence": ["right_blocker", "split_wall"],
        "clearance": descriptor["entry_reachable_clearance_to_walk_blockers"],
        "uncertainty": "entry-reachable sampled free-cell center clearance to walk blockers; proxy, not route-width field or navmesh clearance",
    }


def test_sampled_walkable_space_reports_entry_reachable_region_pair_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_sampled_region_pairs",
        "size": (150.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=50, width=150, height=100),
                kind="room",
                walk_block=1.0,
            ),
            record(
                "split_wall",
                "boundary",
                Rect(cx=75, cy=50, width=50, height=100),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=25, cy=50, width=50, height=100)),
        ],
        "regions": [
            record("left_upper_region", "region", Rect(cx=25, cy=25, width=50, height=50)),
            record("left_lower_region", "region", Rect(cx=25, cy=75, width=50, height=50)),
            record("right_region", "region", Rect(cx=125, cy=50, width=50, height=100)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["sampled_entry_reachable_region_pair_ratio"] == 0.3333
    assert descriptor["sampled_entry_reachable_region_pair_evidence"] == [
        {
            "components": [0],
            "region_a": "left_lower_region",
            "region_b": "left_upper_region",
        }
    ]
    assert descriptor["sampled_unreachable_region_pair_evidence"] == [
        {
            "region_a": "left_lower_region",
            "region_b": "right_region",
        },
        {
            "region_a": "left_upper_region",
            "region_b": "right_region",
        },
    ]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_entry_reachable_region_pair_ratio"]["score"] == 0.3333
    assert (
        path_rows["sampled_entry_reachable_region_pair_ratio"][
            "entry_reachable_region_pair_count"
        ]
        == 1
    )
    assert (
        path_rows["sampled_entry_reachable_region_pair_ratio"][
            "total_region_pair_count"
        ]
        == 3
    )


def test_sampled_walkable_space_reports_entry_region_grid_distance():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_distance",
        "size": (200.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=25, width=200, height=50),
                kind="room",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=200, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=175, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["entry_seed_cells"] == [(0, 0)]
    assert descriptor["entry_region_grid_distances"] == [
        {
            "region_id": "far_region",
            "distance_steps": 3,
            "distance": 150.0,
        }
    ]
    assert descriptor["mean_entry_region_grid_steps"] == 3.0
    assert descriptor["mean_entry_region_grid_distance"] == 150.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_mean_entry_region_grid_distance"]["score"] == 150.0
    assert (
        path_rows["sampled_mean_entry_region_grid_distance"]["method"]
        == "sampled_occupancy_grid_bfs_distance_proxy"
    )


def test_sampled_walkable_space_reports_entry_region_widest_clearance():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_widest_clearance",
        "size": (200.0, 50.0),
        "objects": [
            record(
                "near_path_blocker",
                "fixture",
                Rect(cx=100, cy=0, width=50, height=10),
                walk_block=1.0,
            ),
        ],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=25, width=200, height=50),
                kind="room",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=200, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=175, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["entry_region_widest_clearance_paths"] == [
        {
            "region_id": "far_region",
            "widest_clearance": 40.0,
            "distance_steps": 15,
            "distance": 150.0,
            "path_cells": [
                (2, 0),
                (3, 0),
                (4, 0),
                (4, 1),
                (4, 2),
                (4, 3),
                (4, 4),
                (4, 5),
                (4, 6),
                (4, 7),
                (4, 8),
                (4, 9),
                (4, 10),
                (4, 11),
                (4, 12),
                (4, 13),
                (4, 14),
                (4, 15),
                (3, 15),
                (3, 16),
                (2, 16),
                (1, 16),
                (0, 16),
            ],
        }
    ]
    assert descriptor["mean_entry_region_widest_clearance"] == 40.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_mean_entry_region_widest_clearance"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_mean_entry_region_widest_clearance",
        "score": 40.0,
        "status": "computed",
        "method": "sampled_grid_widest_path_clearance_proxy",
        "evidence": descriptor["entry_region_widest_clearance_paths"],
        "uncertainty": "max-min clearance over sampled entry-to-region grid paths; proxy, not medial-axis width field or navmesh routing",
    }
    assert path_rows["sampled_mean_entry_region_clearance_per_distance"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_mean_entry_region_clearance_per_distance",
        "score": 0.2667,
        "status": "computed",
        "method": "sampled_widest_clearance_over_entry_region_distance_proxy",
        "evidence": descriptor["entry_region_widest_clearance_paths"],
        "uncertainty": "widest sampled path clearance divided by sampled entry-region distance; proxy for route capacity density, not code-compliant egress capacity",
    }


def test_sampled_walkable_space_reports_region_pair_grid_distance():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_region_pair_distance",
        "size": (200.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=25, width=200, height=50),
                kind="room",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=200, height=50)),
        ],
        "regions": [
            record("left_region", "region", Rect(cx=25, cy=25, width=50, height=50)),
            record("right_region", "region", Rect(cx=175, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["region_pair_grid_distances"] == [
        {
            "region_a": "left_region",
            "region_b": "right_region",
            "distance_steps": 3,
            "distance": 150.0,
        }
    ]
    assert descriptor["mean_region_pair_grid_steps"] == 3.0
    assert descriptor["mean_region_pair_grid_distance"] == 150.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_mean_region_pair_grid_distance"]["score"] == 150.0
    assert (
        path_rows["sampled_mean_region_pair_grid_distance"]["method"]
        == "sampled_region_pair_grid_bfs_distance_proxy"
    )


def test_sampled_walkable_space_default_resolution_uses_layout_scale():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_adaptive_resolution",
        "size": (100.0, 100.0),
        "objects": [
            record("small_table", "table", Rect(cx=50, cy=50, width=20, height=20)),
        ],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=50, cy=50, width=100, height=100),
                kind="room",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    assert matrix["sampled_walkable_space"]["resolution"] == 20.0
    assert (
        matrix["sampled_walkable_space"]["resolution_basis"]
        == "median_shortest_furniture_side"
    )
    assert matrix["sampled_walkable_space"]["resolution_evidence"] == ["small_table"]
    assert matrix["sampled_walkable_space"]["resolution_sensitivity"] == {
        "tested_resolutions": [10.0, 20.0, 40.0],
        "entry_reachable_cell_ratio_range": 0.04,
        "entry_reachable_region_ratio_range": 0.0,
        "path_reachable_region_ratio_range": 0.0,
    }
    assert path_rows["sampled_grid_resolution"]["score"] == 20.0
    assert path_rows["sampled_grid_resolution"]["evidence"] == ["small_table"]
    assert path_rows["sampled_resolution_sensitivity"]["score"] == 0.04
    assert (
        path_rows["sampled_resolution_sensitivity"]["method"]
        == "half_base_double_resolution_sampled_metric_range"
    )


def test_sampled_entry_region_grid_distance_reports_unreachable_regions():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_disconnected_distance",
        "size": (150.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=25, width=150, height=50),
                kind="room",
                walk_block=1.0,
            ),
            record(
                "split_wall",
                "boundary",
                Rect(cx=75, cy=25, width=50, height=50),
                kind="wall",
                walk_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=100, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=125, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["entry_reachable_region_ratio"] == 0.0
    assert descriptor["entry_region_grid_distances"] == [
        {
            "region_id": "far_region",
            "distance_steps": None,
            "distance": None,
        }
    ]
    assert descriptor["mean_entry_region_grid_steps"] is None
    assert descriptor["mean_entry_region_grid_distance"] is None

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_mean_entry_region_grid_distance"]["status"] == "not_available"
    assert path_rows["sampled_mean_entry_region_grid_distance"]["score"] is None


def test_path_connectivity_reports_disconnected_entry_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 1.0 if role == "boundary" else 0.0,
                "see_block": 1.0 if role == "boundary" else 0.0,
                "grouping_strength": 1.0 if role == "boundary" else 0.0,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_disconnected_entry_ratio",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=50, width=200, height=100),
                kind="room",
            ),
        ],
        "entries": [
            record("connected_entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
            record("disconnected_entry", "opening", Rect(cx=200, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("left_path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    assert path_rows["entry_touch_ratio"]["score"] == 0.5
    assert path_rows["disconnected_entry_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "disconnected_entry_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "openings_without_path_touch_over_openings",
        "evidence": ["disconnected_entry"],
        "entry_touch_evidence": [
            {
                "id": "connected_entry",
                "edge": None,
                "width": 20,
                "boundary_id": "room_boundary",
                "boundary_gap": 0.0,
                "touched_path_ids": ["left_path"],
            },
            {
                "id": "disconnected_entry",
                "edge": None,
                "width": 20,
                "boundary_id": "room_boundary",
                "boundary_gap": 0.0,
                "touched_path_ids": [],
            },
        ],
        "uncertainty": "bbox path contact proxy; replace with hosted doorway-to-negative-space graph later",
    }


def test_path_connectivity_reports_disconnected_path_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": 1.0 if role == "boundary" else 0.0,
                "see_block": 1.0 if role == "boundary" else 0.0,
                "grouping_strength": 1.0 if role == "boundary" else 0.0,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_disconnected_path_ratio",
        "size": (300.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=150, cy=50, width=300, height=100),
                kind="room",
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("connected_path", "path", Rect(cx=50, cy=50, width=100, height=100)),
            record("floating_path", "path", Rect(cx=250, cy=50, width=80, height=80)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    assert path_rows["disconnected_path_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "disconnected_path_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "paths_without_entry_touch_over_paths",
        "evidence": ["floating_path"],
        "path_entry_touch_evidence": [
            {
                "id": "connected_path",
                "touched_entry_ids": ["entry"],
            },
            {
                "id": "floating_path",
                "touched_entry_ids": [],
            },
        ],
        "uncertainty": "bbox path-entry contact proxy; replace with negative-space graph routing later",
    }


def test_boundary_metrics_reports_closed_blocking_boundary_ratio():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        walk_block=0.0,
        see_block=0.0,
        grouping_strength=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": grouping_strength,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_closed_boundary_ratio",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=50, width=200, height=100),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
                grouping_strength=1.0,
            ),
            record(
                "solid_wall",
                "boundary",
                Rect(cx=100, cy=50, width=10, height=100),
                kind="wall",
                walk_block=1.0,
                see_block=1.0,
                grouping_strength=1.0,
            ),
            record(
                "visual_screen",
                "boundary",
                Rect(cx=150, cy=50, width=10, height=100),
                kind="screen",
                walk_block=0.0,
                see_block=1.0,
                grouping_strength=1.0,
            ),
        ],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    boundary_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "boundary_metrics"
    }

    assert boundary_rows["closed_blocking_boundary_ratio"] == {
        "view_id": "boundary_metrics",
        "metric": "closed_blocking_boundary_ratio",
        "score": 0.6667,
        "status": "computed",
        "method": "walk_and_see_blocking_boundaries_over_boundaries",
        "evidence": ["room_boundary", "solid_wall"],
        "closed_boundary_evidence": [
            {
                "id": "room_boundary",
                "kind": "room",
                "walk_block": 1.0,
                "see_block": 1.0,
            },
            {
                "id": "solid_wall",
                "kind": "wall",
                "walk_block": 1.0,
                "see_block": 1.0,
            },
        ],
        "uncertainty": "authored walk/see weights; not wall topology or fire-code closure",
    }


def test_boundary_metrics_prefers_hosted_entry_boundary_metadata():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, metadata=None):
        weights = {
            "walk_block": 1.0 if kind else 0.0,
            "see_block": 1.0 if kind else 0.0,
            "grouping_strength": 1.0 if kind else 0.0,
        }
        data = {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": weights,
            "metadata": dict(metadata or {}),
        }
        if kind:
            data["metadata"]["boundary-kind"] = kind
        return data

    hosted_wall = record(
        "hosted_wall",
        "boundary",
        Rect(cx=100, cy=0, width=200, height=0),
        kind="wall",
    )
    nearby_wall = record(
        "nearby_wall",
        "boundary",
        Rect(cx=10, cy=10, width=20, height=0),
        kind="wall",
    )
    door = record(
        "door",
        "opening",
        Rect(cx=10, cy=10, width=20, height=0),
        metadata={"host-boundary": "hosted_wall"},
    )
    scene = {
        "source": "synthetic_hosted_entry",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [hosted_wall, nearby_wall],
        "entries": [door],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    boundary_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "boundary_metrics"
    }

    assert boundary_rows["entry_nearest_boundary_gap_mean"]["entry_boundary_associations"] == [
        {
            "id": "door",
            "edge": None,
            "width": 20,
            "center": (10, 10),
            "width_source": "opening_bbox_max_dimension",
            "boundary_id": "hosted_wall",
            "boundary_kind": "wall",
            "gap": 10.0,
            "projected_point": (10.0, 0.0),
            "association_method": "host_boundary_metadata",
        }
    ]
    assert boundary_rows["hosted_entry_boundary_ratio"] == {
        "view_id": "boundary_metrics",
        "metric": "hosted_entry_boundary_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "entries_with_explicit_host_boundary_over_entries",
        "evidence": ["door"],
        "entry_boundary_associations": boundary_rows["entry_nearest_boundary_gap_mean"]["entry_boundary_associations"],
        "uncertainty": "explicit host-boundary metadata is the preferred Rhino/BIM doorway association; missing hosts still fall back to nearest geometry",
    }


def test_boundary_metrics_reports_fallback_entry_boundary_ratio():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, metadata=None):
        weights = {
            "walk_block": 1.0 if kind else 0.0,
            "see_block": 1.0 if kind else 0.0,
            "grouping_strength": 1.0 if kind else 0.0,
        }
        data = {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": weights,
            "metadata": dict(metadata or {}),
        }
        if kind:
            data["metadata"]["boundary-kind"] = kind
        return data

    hosted_wall = record(
        "hosted_wall",
        "boundary",
        Rect(cx=50, cy=0, width=100, height=0),
        kind="wall",
    )
    fallback_wall = record(
        "fallback_wall",
        "boundary",
        Rect(cx=50, cy=100, width=100, height=0),
        kind="wall",
    )
    hosted_door = record(
        "hosted_door",
        "opening",
        Rect(cx=10, cy=10, width=10, height=0),
        metadata={"host-boundary": "hosted_wall"},
    )
    fallback_door = record(
        "fallback_door",
        "opening",
        Rect(cx=80, cy=95, width=10, height=0),
    )
    scene = {
        "source": "synthetic_fallback_entry_boundary_ratio",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [hosted_wall, fallback_wall],
        "entries": [hosted_door, fallback_door],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    boundary_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "boundary_metrics"
    }

    assert boundary_rows["fallback_entry_boundary_ratio"] == {
        "view_id": "boundary_metrics",
        "metric": "fallback_entry_boundary_ratio",
        "score": 0.5,
        "status": "computed",
        "method": "entries_with_nearest_geometry_boundary_over_entries",
        "evidence": ["fallback_door"],
        "entry_boundary_associations": boundary_rows["entry_nearest_boundary_gap_mean"]["entry_boundary_associations"],
        "uncertainty": "nearest-geometry opening association is an SVG fallback; Rhino/BIM adapters should prefer hosted opening topology",
    }
    assert matrix["adapter_payload"]["host_relationships"] == {
        "method": "entry_boundary_associations_from_host_metadata_or_nearest_geometry",
        "entry_boundary_hosts": boundary_rows["entry_nearest_boundary_gap_mean"]["entry_boundary_associations"],
        "hosted_entry_count": 1,
        "fallback_entry_count": 1,
        "uncertainty": "neutral host relationship export only; Rhino/VisualARQ/BIM adapters must replace fallback geometry with live hosted topology",
    }


def test_boundary_metrics_prefers_explicit_opening_width_metadata():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, metadata=None):
        weights = {
            "walk_block": 1.0 if kind else 0.0,
            "see_block": 1.0 if kind else 0.0,
            "grouping_strength": 1.0 if kind else 0.0,
        }
        data = {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": weights,
            "metadata": dict(metadata or {}),
        }
        if kind:
            data["metadata"]["boundary-kind"] = kind
        return data

    wall = record(
        "wall",
        "boundary",
        Rect(cx=50, cy=0, width=100, height=0),
        kind="wall",
    )
    door = record(
        "door",
        "opening",
        Rect(cx=10, cy=0, width=10, height=0),
        metadata={"opening-width": "90", "host-boundary": "wall"},
    )
    scene = {
        "source": "synthetic_explicit_opening_width",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [wall],
        "entries": [door],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    boundary_rows = {
        row["metric"]: row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "boundary_metrics"
    }

    assert boundary_rows["entry_width_mean"]["score"] == 90.0
    assert boundary_rows["entry_width_mean"]["entry_widths"] == [
        {
            "id": "door",
            "edge": None,
            "width": 90.0,
            "center": (10, 0),
            "width_source": "opening_width_metadata",
        }
    ]
    assert boundary_rows["boundary_opening_width_ratio_max"]["boundary_opening_evidence"] == [
        {
            "id": "wall",
            "kind": "wall",
            "length": 100,
            "opening_width": 90.0,
            "opening_ratio": 0.9,
            "opening_ids": ["door"],
        }
    ]


def test_sampled_visibility_region_ratio_ignores_walk_only_glass_blockers():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_glass_visibility",
        "size": (150.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=25, width=150, height=50),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "glass_split",
                "boundary",
                Rect(cx=75, cy=25, width=50, height=50),
                kind="glass",
                walk_block=1.0,
                see_block=0.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=100, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=125, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["entry_reachable_region_ratio"] == 0.0
    assert descriptor["mean_entry_region_grid_distance"] is None
    assert descriptor["visibility_reachable_region_ratio"] == 1.0
    assert descriptor["visibility_only_region_ratio"] == 1.0
    assert descriptor["walk_visibility_disagreement_region_ratio"] == 1.0
    assert descriptor["visibility_region_grid_distances"] == [
        {
            "region_id": "far_region",
            "distance_steps": 2,
            "distance": 100.0,
        }
    ]
    assert descriptor["mean_visibility_region_grid_steps"] == 2.0
    assert descriptor["mean_visibility_region_grid_distance"] == 100.0
    assert descriptor["visibility_blocker_evidence"] == []

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_visibility_reachable_region_ratio"]["score"] == 1.0
    assert path_rows["sampled_visibility_only_region_ratio"]["score"] == 1.0
    assert path_rows["sampled_walk_visibility_disagreement_region_ratio"]["score"] == 1.0
    assert (
        path_rows["sampled_visibility_reachable_region_ratio"]["method"]
        == "sampled_visibility_grid_bfs_proxy"
    )
    assert (
        path_rows["sampled_visibility_only_region_ratio"]["method"]
        == "sampled_visibility_only_minus_walk_reachability_proxy"
    )
    assert (
        path_rows["sampled_walk_visibility_disagreement_region_ratio"]["method"]
        == "sampled_walk_visibility_reachability_xor_proxy"
    )
    assert path_rows["sampled_mean_visibility_region_grid_distance"]["score"] == 100.0
    assert (
        path_rows["sampled_mean_visibility_region_grid_distance"]["method"]
        == "sampled_visibility_grid_bfs_distance_proxy"
    )


def test_sampled_visibility_region_pair_ratio_ignores_walk_only_glass_blockers():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_glass_visibility_pairs",
        "size": (150.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=25, width=150, height=50),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "glass_split",
                "boundary",
                Rect(cx=75, cy=25, width=50, height=50),
                kind="glass",
                walk_block=1.0,
                see_block=0.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=75, cy=25, width=150, height=50)),
        ],
        "regions": [
            record("near_region", "region", Rect(cx=25, cy=25, width=50, height=50)),
            record("far_region", "region", Rect(cx=125, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    descriptor = matrix["sampled_walkable_space"]

    assert descriptor["sampled_entry_reachable_region_pair_ratio"] == 0.0
    assert descriptor["sampled_visibility_reachable_region_pair_ratio"] == 1.0
    assert descriptor["sampled_visibility_only_region_pair_ratio"] == 1.0
    assert descriptor["sampled_walk_only_region_pair_ratio"] == 0.0
    assert descriptor["sampled_walk_visibility_disagreement_region_pair_ratio"] == 1.0
    assert descriptor["sampled_visibility_reachable_region_pair_evidence"] == [
        {
            "regions": ["far_region", "near_region"],
        }
    ]
    assert descriptor["sampled_visibility_unreachable_region_pair_evidence"] == []
    assert descriptor["sampled_visibility_only_region_pair_evidence"] == [
        {
            "region_a": "far_region",
            "region_b": "near_region",
        }
    ]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_entry_reachable_region_pair_ratio"]["score"] == 0.0
    assert path_rows["sampled_visibility_reachable_region_pair_ratio"]["score"] == 1.0
    assert path_rows["sampled_visibility_only_region_pair_ratio"]["score"] == 1.0
    assert path_rows["sampled_walk_only_region_pair_ratio"]["score"] == 0.0
    assert (
        path_rows["sampled_walk_visibility_disagreement_region_pair_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["sampled_visibility_reachable_region_pair_ratio"][
            "visibility_reachable_region_pair_count"
        ]
        == 1
    )
    assert (
        path_rows["sampled_visibility_reachable_region_pair_ratio"][
            "total_region_pair_count"
        ]
        == 1
    )


def test_sampled_walk_only_region_ratio_reports_walkable_visual_blockers():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_walk_only_visibility",
        "size": (150.0, 50.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=75, cy=25, width=150, height=50),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "visual_screen",
                "boundary",
                Rect(cx=75, cy=25, width=50, height=50),
                kind="screen",
                walk_block=0.0,
                see_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=0, cy=25, width=0, height=50)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=25, width=100, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=125, cy=25, width=50, height=50)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["entry_reachable_region_ratio"] == 1.0
    assert descriptor["visibility_reachable_region_ratio"] == 0.0
    assert descriptor["walk_only_region_ratio"] == 1.0
    assert descriptor["visibility_only_region_ratio"] == 0.0
    assert descriptor["walk_visibility_disagreement_region_ratio"] == 1.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_walk_only_region_ratio"]["score"] == 1.0
    assert path_rows["sampled_walk_visibility_disagreement_region_ratio"]["score"] == 1.0
    assert (
        path_rows["sampled_walk_only_region_ratio"]["method"]
        == "sampled_walk_only_minus_visibility_reachability_proxy"
    )


def test_line_of_sight_region_ratio_reports_visual_blockers():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        points=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_line_of_sight",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=50, width=200, height=100),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "visual_screen",
                "boundary",
                Rect(cx=100, cy=50, width=0, height=80),
                kind="screen",
                points=[(100.0, 10.0), (100.0, 90.0)],
                see_block=1.0,
            ),
            record(
                "entry_host_wall",
                "boundary",
                Rect(cx=20, cy=50, width=40, height=100),
                kind="wall",
                see_block=1.0,
            ),
        ],
        "entries": [
            record("entry", "opening", Rect(cx=-20, cy=50, width=40, height=0)),
        ],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=160, height=50)),
        ],
        "regions": [
            record("far_region", "region", Rect(cx=180, cy=50, width=20, height=20)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    los = path_rows["line_of_sight_entry_region_ratio"]
    assert los["score"] == 0.0
    assert los["method"] == "entry_region_centerline_see_block_intersection"
    assert los["line_of_sight_evidence"] == [
        {
            "entry_id": "entry",
            "region_id": "far_region",
            "visible": False,
            "blocking_boundary_ids": ["visual_screen"],
            "blocking_boundary_evidence": [
                {
                    "boundary_id": "visual_screen",
                    "intersection_points": [(100.0, 50.0)],
                    "intersection_distances_from_start": [120.0],
                    "intersection_distance_ratios": [0.6],
                }
            ],
        }
    ]


def test_line_of_sight_region_pair_ratio_reports_visual_blockers():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        points=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_region_pair_line_of_sight",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=50, width=200, height=100),
                kind="room",
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "visual_screen",
                "boundary",
                Rect(cx=100, cy=50, width=0, height=80),
                kind="screen",
                points=[(100.0, 10.0), (100.0, 90.0)],
                see_block=1.0,
            ),
        ],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=160, height=50)),
        ],
        "regions": [
            record("left_region", "region", Rect(cx=40, cy=50, width=20, height=20)),
            record("right_region", "region", Rect(cx=160, cy=50, width=20, height=20)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }

    los = path_rows["line_of_sight_region_pair_ratio"]
    assert los["score"] == 0.0
    assert los["method"] == "region_pair_centerline_see_block_intersection"
    assert los["line_of_sight_region_pair_evidence"] == [
        {
            "region_a": "left_region",
            "region_b": "right_region",
            "visible": False,
            "blocking_boundary_ids": ["visual_screen"],
            "blocking_boundary_evidence": [
                {
                    "boundary_id": "visual_screen",
                    "intersection_points": [(100.0, 50.0)],
                    "intersection_distances_from_start": [60.0],
                    "intersection_distance_ratios": [0.5],
                }
            ],
        }
    ]
    assert matrix["line_of_sight_graph"] == {
        "nodes": [
            {
                "id": "node_line_of_sight_region_left_region",
                "kind": "region",
                "ref_id": "left_region",
                "point": (40, 50),
            },
            {
                "id": "node_line_of_sight_region_right_region",
                "kind": "region",
                "ref_id": "right_region",
                "point": (160, 50),
            },
        ],
        "edges": [
            {
                "id": "edge_line_of_sight_region_pair_left_region_right_region",
                "kind": "region_pair_centerline_visibility",
                "a": "node_line_of_sight_region_left_region",
                "b": "node_line_of_sight_region_right_region",
                "refs": {"region_a": "left_region", "region_b": "right_region"},
                "visible": False,
                "centerline": {
                    "start": (40, 50),
                    "end": (160, 50),
                    "length": 120.0,
                },
                "blocking_boundary_ids": ["visual_screen"],
                "blocking_boundary_evidence": [
                    {
                        "boundary_id": "visual_screen",
                        "intersection_points": [(100.0, 50.0)],
                        "intersection_distances_from_start": [60.0],
                        "intersection_distance_ratios": [0.5],
                    }
                ],
            }
        ],
        "metrics": {
            "node_count": 2,
            "edge_count": 1,
            "visible_edge_count": 0,
            "blocked_edge_count": 1,
            "visible_edge_ratio": 0.0,
            "blocked_edge_ratio": 1.0,
            "visible_edge_ids": [],
            "blocked_edge_ids": [
                "edge_line_of_sight_region_pair_left_region_right_region"
            ],
            "blocking_boundary_ids": ["visual_screen"],
            "blocking_boundary_edge_evidence": [
                {
                    "boundary_id": "visual_screen",
                    "blocked_edge_ids": [
                        "edge_line_of_sight_region_pair_left_region_right_region"
                    ],
                    "blocked_edge_count": 1,
                }
            ],
            "mean_centerline_length": 120.0,
        },
    }
    assert path_rows["line_of_sight_graph_visible_edge_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "line_of_sight_graph_visible_edge_ratio",
        "score": 0.0,
        "status": "computed",
        "method": "line_of_sight_graph_edge_visibility_ratio",
        "evidence": [],
        "visible_edge_ids": [],
        "uncertainty": "centerline visibility graph proxy; not full VGA, isovist, or visual integration",
    }
    assert path_rows["line_of_sight_graph_blocked_edge_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "line_of_sight_graph_blocked_edge_ratio",
        "score": 1.0,
        "status": "computed",
        "method": "line_of_sight_graph_edge_visibility_ratio",
        "evidence": ["edge_line_of_sight_region_pair_left_region_right_region"],
        "blocked_edge_ids": [
            "edge_line_of_sight_region_pair_left_region_right_region"
        ],
        "blocking_boundary_ids": ["visual_screen"],
        "uncertainty": "centerline visibility graph proxy; blocked edges identify direct-sight obstructions, not visual-exposure fields",
    }
    assert path_rows["line_of_sight_graph_blocking_boundary_count"] == {
        "view_id": "path_connectivity",
        "metric": "line_of_sight_graph_blocking_boundary_count",
        "score": 1,
        "status": "computed",
        "method": "line_of_sight_graph_unique_blocking_boundary_count",
        "evidence": ["visual_screen"],
        "blocking_boundary_ids": ["visual_screen"],
        "blocked_edge_ids": [
            "edge_line_of_sight_region_pair_left_region_right_region"
        ],
        "blocking_boundary_edge_evidence": [
            {
                "boundary_id": "visual_screen",
                "blocked_edge_ids": [
                    "edge_line_of_sight_region_pair_left_region_right_region"
                ],
                "blocked_edge_count": 1,
            }
        ],
        "uncertainty": "unique authored see_block boundaries intersecting blocked centerline graph edges; not obstacle attribution from full VGA or isovist fields",
    }


def test_isovist_radial_proxy_reports_blocked_rays():
    from features.affordance.models import Rect

    def record(
        record_id,
        role,
        rect,
        *,
        kind=None,
        points=None,
        walk_block=0.0,
        see_block=0.0,
    ):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": walk_block,
                "see_block": see_block,
                "grouping_strength": max(walk_block, see_block),
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_isovist_radial_proxy",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=100, cy=50, width=200, height=100),
                kind="room",
                points=[(0, 0), (200, 0), (200, 100), (0, 100), (0, 0)],
                walk_block=1.0,
                see_block=1.0,
            ),
            record(
                "visual_screen",
                "boundary",
                Rect(cx=150, cy=50, width=0, height=40),
                kind="screen",
                points=[(150.0, 30.0), (150.0, 70.0)],
                see_block=1.0,
            ),
        ],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=100, cy=50, width=160, height=50)),
        ],
        "regions": [
            record("center_region", "region", Rect(cx=100, cy=50, width=20, height=20)),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    isovist = matrix["isovist_radial_proxy"]
    assert isovist["metrics"]["ray_count"] == 8
    assert isovist["metrics"]["blocked_ray_count"] == 1
    assert isovist["metrics"]["blocked_ray_ratio"] == 0.125
    assert isovist["metrics"]["mean_hit_polygon_area"] == 12500.0
    assert isovist["isovist_area_evidence"] == [
        {
            "vantage_id": "center_region",
            "vantage_kind": "region",
            "hit_polygon": (
                (150.0, 50.0),
                (150.0, 100.0),
                (100.0, 100.0),
                (50.0, 100.0),
                (0.0, 50.0),
                (50.0, -0.0),
                (100.0, -0.0),
                (150.0, -0.0),
            ),
            "hit_polygon_area": 12500.0,
            "blocked_ray_count": 1,
            "ray_count": 8,
        }
    ]

    east_ray = next(
        ray
        for ray in isovist["ray_evidence"]
        if ray["vantage_id"] == "center_region" and ray["angle_degrees"] == 0
    )
    assert east_ray == {
        "vantage_id": "center_region",
        "vantage_kind": "region",
        "angle_degrees": 0,
        "start": (100, 50),
        "hit_point": (150.0, 50.0),
        "hit_distance": 50.0,
        "hit_boundary_id": "visual_screen",
        "hit_boundary_kind": "screen",
        "blocked_by_see_block": True,
    }
    visual_handoff = matrix["adapter_payload"]["visual_analysis_handoff"]
    assert visual_handoff["visibility_graph"]["items"] == matrix["line_of_sight_graph"]["edges"]
    assert visual_handoff["isovist_radial_proxy"]["ray_items"] == isovist["ray_evidence"]
    assert visual_handoff["isovist_radial_proxy"]["area_items"] == isovist[
        "isovist_area_evidence"
    ]

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["isovist_radial_blocked_ray_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "isovist_radial_blocked_ray_ratio",
        "score": 0.125,
        "status": "computed",
        "method": "radial_isovist_see_block_ray_intersection_proxy",
        "evidence": ["center_region:0"],
        "blocked_ray_count": 1,
        "ray_count": 8,
        "isovist_ray_evidence": isovist["ray_evidence"],
        "uncertainty": "8-direction room-bounded radial ray proxy; not full isovist polygon, VGA, or calibrated visual exposure",
    }
    assert path_rows["isovist_radial_hit_polygon_area_mean"] == {
        "view_id": "path_connectivity",
        "metric": "isovist_radial_hit_polygon_area_mean",
        "score": 12500.0,
        "status": "computed",
        "method": "radial_isovist_hit_point_polygon_area_proxy",
        "evidence": ["center_region"],
        "isovist_area_evidence": isovist["isovist_area_evidence"],
        "uncertainty": "area of polygon formed by ordered radial ray hit points; proxy, not full isovist polygon, VGA, or visual integration",
    }


def test_isovist_radial_proxy_clips_boundary_vantage_outward_rays_to_room():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, points=None, see_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": see_block,
                "see_block": see_block,
                "grouping_strength": see_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    scene = {
        "source": "synthetic_boundary_vantage_isovist",
        "size": (100.0, 100.0),
        "objects": [],
        "boundaries": [
            record(
                "room_boundary",
                "boundary",
                Rect(cx=50, cy=50, width=100, height=100),
                kind="room",
                points=[(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
                see_block=1.0,
            ),
        ],
        "entries": [
            record("left_entry", "opening", Rect(cx=0, cy=50, width=0, height=20)),
        ],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    isovist = evaluate_scene(scene)["isovist_radial_proxy"]
    west_ray = next(
        ray
        for ray in isovist["ray_evidence"]
        if ray["vantage_id"] == "left_entry" and ray["angle_degrees"] == 180
    )

    assert west_ray["hit_point"] == (0.0, 50.0)
    assert west_ray["hit_distance"] == 0.0
    assert isovist["metrics"]["mean_hit_polygon_area"] <= 10000.0


def test_column_alignment_reports_object_axis_phase_score():
    from features.affordance.models import Rect

    def record(record_id, role, rect, points=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_column_phase",
        "size": (120.0, 100.0),
        "objects": [
            record("on_axis_table", "table", Rect(cx=0, cy=50, width=10, height=10)),
            record("mid_bay_table", "table", Rect(cx=50, cy=50, width=10, height=10)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [
            record(
                "column_axis_left",
                "column_axis",
                Rect(cx=0, cy=50, width=0, height=100),
                [(0, 0), (0, 100)],
            ),
            record(
                "column_axis_right",
                "column_axis",
                Rect(cx=100, cy=50, width=0, height=100),
                [(100, 0), (100, 100)],
            ),
        ],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    column_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }

    phase = column_rows["object_column_axis_phase_alignment"]
    assert phase["score"] == 0.8334
    assert phase["method"] == "object_center_to_nearest_column_axis_distance_kernel"
    assert phase["object_axis_phase_evidence"] == [
        {
            "object_id": "mid_bay_table",
            "nearest_axis_id": "column_axis_left",
            "distance": 50.0,
            "axis_spacing": 100.0,
            "score": 0.6667,
        },
        {
            "object_id": "on_axis_table",
            "nearest_axis_id": "column_axis_left",
            "distance": 0.0,
            "axis_spacing": 100.0,
            "score": 1.0,
        },
    ]


def test_region_alignment_uses_pca_axis_for_irregular_polygons():
    from features.affordance.models import Rect

    def record(record_id, points):
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return {
            "id": record_id,
            "role": "region",
            "group": "global",
            "region": record_id,
            "rect": Rect(
                cx=(min(xs) + max(xs)) / 2,
                cy=(min(ys) + max(ys)) / 2,
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            ),
            "points": points,
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_pca_region_axis",
        "size": (320.0, 160.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            record("wide_irregular_region", [(0, 40), (220, 20), (300, 60), (220, 100), (0, 80), (40, 60)]),
            record("horizontal_region", [(0, 100), (300, 100), (300, 130), (0, 130)]),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    row = [
        row
        for row in matrix["rows"]
        if row["metric"] == "region_axis_agreement"
    ][0]
    evidence = {item["id"]: item for item in row["axis_evidence"]}

    assert evidence["wide_irregular_region"]["basis"] == "polygon_pca_axis"
    assert evidence["wide_irregular_region"]["angle"] == 0.0


def test_column_alignment_reports_region_to_bay_fit():
    from features.affordance.models import Rect

    def record(record_id, role, rect, points=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": record_id,
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_column_bay_fit",
        "size": (200.0, 100.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            record("left_half_region", "region", Rect(cx=50, cy=50, width=100, height=100)),
            record("straddling_region", "region", Rect(cx=100, cy=50, width=200, height=100)),
        ],
        "column_axes": [
            record(
                "column_axis_left",
                "column_axis",
                Rect(cx=0, cy=50, width=0, height=100),
                [(0, 0), (0, 100)],
            ),
            record(
                "column_axis_right",
                "column_axis",
                Rect(cx=100, cy=50, width=0, height=100),
                [(100, 0), (100, 100)],
            ),
        ],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    column_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }

    bay_fit = column_rows["region_column_bay_fit"]
    assert bay_fit["score"] == 0.75
    assert bay_fit["method"] == "region_bbox_overlap_with_adjacent_column_axis_bay"
    assert bay_fit["region_bay_fit_evidence"] == [
        {
            "region_id": "left_half_region",
            "bay_id": "column_axis_left__column_axis_right",
            "overlap_area": 10000,
            "region_area": 10000,
            "score": 1.0,
        },
        {
            "region_id": "straddling_region",
            "bay_id": "column_axis_left__column_axis_right",
            "overlap_area": 10000,
            "region_area": 20000,
            "score": 0.5,
        },
    ]


def test_column_alignment_reports_non_orthogonal_region_to_bay_fit():
    from features.affordance.models import Rect

    def record(record_id, role, rect, points=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": record_id,
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_non_orthogonal_column_bay_fit",
        "size": (120.0, 220.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            record("slanted_bay_region", "region", Rect(cx=50, cy=100, width=100, height=200)),
        ],
        "column_axes": [
            record(
                "column_axis_diag_a",
                "column_axis",
                Rect(cx=50, cy=50, width=100, height=100),
                [(0, 0), (100, 100)],
            ),
            record(
                "column_axis_diag_b",
                "column_axis",
                Rect(cx=50, cy=150, width=100, height=100),
                [(0, 100), (100, 200)],
            ),
        ],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    column_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }

    bay_fit = column_rows["region_column_bay_fit"]
    assert bay_fit["score"] == 0.5
    assert bay_fit["region_bay_fit_evidence"] == [
        {
            "region_id": "slanted_bay_region",
            "bay_id": "column_axis_diag_a__column_axis_diag_b",
            "overlap_area": 10000.0,
            "region_area": 20000,
            "score": 0.5,
        }
    ]


def test_column_alignment_reports_object_local_position_in_slanted_bay():
    from features.affordance.models import Rect

    def record(record_id, role, rect, points=None):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": record_id,
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_column_bay_local_position",
        "size": (220.0, 140.0),
        "objects": [
            record("center_table", "table", Rect(cx=100, cy=50, width=10, height=10)),
            record("outside_table", "table", Rect(cx=200, cy=50, width=10, height=10)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [
            record(
                "column_axis_diag_a",
                "column_axis",
                Rect(cx=50, cy=50, width=100, height=100),
                [(0, 0), (100, 100)],
            ),
            record(
                "column_axis_diag_b",
                "column_axis",
                Rect(cx=150, cy=50, width=100, height=100),
                [(100, 0), (200, 100)],
            ),
        ],
        "uncertainties": [],
    }

    column_rows = {
        row["metric"]: row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "column_alignment"
    }

    local_position = column_rows["object_column_bay_local_position_coverage"]
    assert local_position == {
        "view_id": "column_alignment",
        "metric": "object_column_bay_local_position_coverage",
        "score": 0.5,
        "status": "computed",
        "method": "object_center_affine_position_in_nearest_column_bay",
        "evidence": ["center_table", "outside_table"],
        "column_axis_evidence": [
            {
                "id": "column_axis_diag_a",
                "angle": 45.0,
                "basis": "polygon_longest_edge",
            },
            {
                "id": "column_axis_diag_b",
                "angle": 45.0,
                "basis": "polygon_longest_edge",
            },
        ],
        "object_bay_local_position_evidence": [
            {
                "object_id": "center_table",
                "bay_id": "column_axis_diag_a__column_axis_diag_b",
                "local_u": 0.5,
                "local_v": 0.5,
                "inside_bay": True,
                "score": 1.0,
            },
            {
                "object_id": "outside_table",
                "bay_id": "column_axis_diag_a__column_axis_diag_b",
                "local_u": 0.5,
                "local_v": 1.5,
                "inside_bay": False,
                "score": 0.0,
            },
        ],
        "uncertainty": "object center affine coordinates inside nearest authored column bay; local-frame proxy, not full irregular grid interpolation",
    }


def test_column_grid_handoff_exports_bay_and_local_position_items():
    from features.affordance.models import Rect

    def record(record_id, role, rect, points=None):
        region = "left_region" if role != "region" else record_id
        return {
            "id": record_id,
            "role": role,
            "group": region,
            "region": region,
            "rect": rect,
            "points": points or [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_column_grid_handoff_items",
        "size": (200.0, 100.0),
        "objects": [
            record("inside_table", "table", Rect(cx=50, cy=50, width=10, height=10)),
            record("outside_table", "table", Rect(cx=150, cy=50, width=10, height=10)),
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            record("left_region", "region", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "column_axes": [
            record(
                "column_axis_left",
                "column_axis",
                Rect(cx=0, cy=50, width=0, height=100),
                [(0, 0), (0, 100)],
            ),
            record(
                "column_axis_right",
                "column_axis",
                Rect(cx=100, cy=50, width=0, height=100),
                [(100, 0), (100, 100)],
            ),
        ],
        "uncertainties": [],
    }

    handoff = evaluate_scene(scene)["adapter_payload"]["column_grid_handoff"]

    assert handoff["axes"]["items"] == [
        {"id": "column_axis_left", "angle": 90.0, "basis": "polygon_longest_edge"},
        {"id": "column_axis_right", "angle": 90.0, "basis": "polygon_longest_edge"},
    ]
    assert handoff["region_bays"]["items"] == [
        {
            "region_id": "left_region",
            "bay_id": "column_axis_left__column_axis_right",
            "overlap_area": 10000,
            "region_area": 10000,
            "score": 1.0,
        }
    ]
    assert handoff["object_bay_local_positions"]["items"] == [
        {
            "object_id": "inside_table",
            "bay_id": "column_axis_left__column_axis_right",
            "local_u": 0.5,
            "local_v": 0.5,
            "inside_bay": True,
            "score": 1.0,
        },
        {
            "object_id": "outside_table",
            "bay_id": "column_axis_left__column_axis_right",
            "local_u": 1.5,
            "local_v": 0.5,
            "inside_bay": False,
            "score": 0.0,
        },
    ]


def test_region_alignment_reports_centroid_phase_score():
    from features.affordance.models import Rect

    def region(record_id, cx):
        return {
            "id": record_id,
            "role": "region",
            "group": "global",
            "region": record_id,
            "rect": Rect(cx=cx, cy=50, width=20, height=20),
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"axis-angle": "0"},
        }

    scene = {
        "source": "synthetic_region_phase",
        "size": (400.0, 100.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            region("region_a", 0),
            region("region_b", 100),
            region("region_c", 300),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    region_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "region_alignment"
    }

    phase = region_rows["region_centroid_phase_alignment"]
    assert phase["score"] == 0.75
    assert phase["method"] == "region_centroid_projection_gap_cv_score"
    assert phase["region_centroid_phase_evidence"] == [
        {"region_id": "region_a", "projection": 0.0},
        {"region_id": "region_b", "projection": 100.0},
        {"region_id": "region_c", "projection": 300.0},
    ]


def test_trend_reports_region_centroid_trend_alignment():
    from features.affordance.models import Rect

    def region(record_id, cx, cy):
        return {
            "id": record_id,
            "role": "region",
            "group": "global",
            "region": record_id,
            "rect": Rect(cx=cx, cy=cy, width=20, height=20),
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {},
        }

    scene = {
        "source": "synthetic_region_trend",
        "size": (400.0, 220.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            region("region_a", 0, 0),
            region("region_b", 100, 100),
            region("region_c", 200, 200),
            region("region_d", 300, 230),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    rows = {
        row["metric"]: row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "trend"
    }
    trend = rows["region_centroid_trend_alignment"]

    assert trend == {
        "view_id": "trend",
        "metric": "region_centroid_trend_alignment",
        "score": 0.9652,
        "status": "computed",
        "method": "region_centroid_pca_axis_cross_deviation_score",
        "evidence": ["region_a", "region_b", "region_c", "region_d"],
        "trend_axis": {
            "angle": 38.8153,
            "basis": "region_centroid_pca_axis",
            "region_count": 4,
            "span": 377.9179,
            "mean_cross_axis_deviation": 13.6355,
        },
        "region_centroid_trend_evidence": [
            {
                "region_id": "region_a",
                "projection": -199.9282,
                "cross_axis_deviation": 9.2183,
            },
            {
                "region_id": "region_b",
                "projection": -59.3299,
                "cross_axis_deviation": 6.0176,
            },
            {
                "region_id": "region_c",
                "projection": 81.2683,
                "cross_axis_deviation": 21.2534,
            },
            {
                "region_id": "region_d",
                "projection": 177.9897,
                "cross_axis_deviation": 18.0527,
            },
        ],
        "uncertainty": "PCA trend over region bbox centers; proxy for dominant layout direction, not semantic procession, circulation intent, or time-series trend",
    }


def test_evaluate_scene_returns_score_matrix_summary():
    from features.affordance.models import Rect

    def region(record_id, cx):
        return {
            "id": record_id,
            "role": "region",
            "group": "global",
            "region": record_id,
            "rect": Rect(cx=cx, cy=50, width=20, height=20),
            "points": [],
            "weights": {
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.0,
            },
            "metadata": {"axis-angle": "0"},
        }

    scene = {
        "source": "synthetic_score_matrix",
        "size": (400.0, 120.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            region("region_a", 0),
            region("region_b", 100),
            region("region_c", 300),
        ],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)

    assert matrix["score_matrix"] == {
        "method": "computed_unit_interval_metric_mean_by_view_id",
        "overall_score": 0.4688,
        "dimension_scores": [
            {
                "view_id": "adapter_readiness",
                "score": 0.0,
                "metric_count": 1,
                "metrics": ["adapter_reference_coverage"],
            },
            {
                "view_id": "boundary_metrics",
                "score": 0.0,
                "metric_count": 2,
                "metrics": [
                    "closed_blocking_boundary_ratio",
                    "opening_ratio",
                ],
            },
            {
                "view_id": "region_alignment",
                "score": 0.875,
                "metric_count": 2,
                "metrics": [
                    "region_axis_agreement",
                    "region_centroid_phase_alignment",
                ],
            },
            {
                "view_id": "trend",
                "score": 1.0,
                "metric_count": 1,
                "metrics": ["region_centroid_trend_alignment"],
            },
        ],
        "excluded_metrics": [
            "boundary_connectivity.opening_count",
            "uncertainties.open_items",
            "uncertainties.uncertainty_routes",
        ],
        "uncertainty": "dimension scores average computed 0..1 scalar metrics only; counts, unavailable rows, and domain-specific weights are excluded until calibrated",
    }
    assert matrix["adapter_payload"]["score_matrix"] == matrix["score_matrix"]


def test_evaluate_scene_reports_matrix_completion_audit_gate():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)
    adapter_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "adapter_readiness"
    }

    audit = adapter_rows["matrix_completion_audit"]
    family_status = {
        item["family"]: item
        for item in audit["required_metric_family_status"]
    }

    assert audit["score"] is None
    assert audit["status"] == "computed"
    assert audit["method"] == "completion_gate_from_current_metric_family_status"
    assert audit["completion_ready"] is False
    assert "route_topology" in audit["open_core_families"]
    assert "visual_analysis" in audit["open_core_families"]
    assert "live_bim_rhino_adapter" not in audit["open_core_families"]
    assert family_status["route_topology"]["status"] == "prototype_proxy"
    assert family_status["visual_analysis"]["status"] == "prototype_proxy"
    assert family_status["live_bim_rhino_adapter"]["status"] == "deferred_by_user_scope"


def test_evaluate_scene_returns_stable_metric_rows():
    """Stable fixture payload should keep existing rows and required handoffs."""
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)
    row_ids = {row["view_id"] for row in matrix["rows"]}

    assert {
        "north_tables_order",
        "west_lounge_geometry",
        "center_lounge_geometry",
        "east_armchair_geometry",
        "region_alignment",
        "column_alignment",
        "whole_space_force",
        "path_connectivity",
        "boundary_metrics",
        "adapter_readiness",
        "uncertainties",
    } <= row_ids

    north = [row for row in matrix["rows"] if row["view_id"] == "north_tables_order"]
    assert any(row["method"].startswith("octa") for row in north)
    adapter_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "adapter_readiness"
    }
    assert adapter_rows["adapter_reference_coverage"]["score"] == 0.0435
    assert adapter_rows["adapter_reference_coverage"]["evidence"] == [
        "north_table_r1_c1",
        "room_boundary",
    ]
    payload = matrix["adapter_payload"]
    assert payload["record_count"] == 46
    assert payload["external_refs"]["ifc_guid"] == {
        "ifc-room-boundary": "room_boundary"
    }
    assert payload["external_refs"]["rhino_guid"] == {
        "rhino-north-table-r1-c1": "north_table_r1_c1"
    }
    assert {
        "view_id": "adapter_readiness",
        "metric": "adapter_reference_coverage",
        "score": 0.0435,
        "status": "computed",
    } in payload["metric_rows"]
    assert payload["evidence_geometry"]["free_space_polygons"]["count"] == 814
    assert (
        payload["evidence_geometry"]["free_space_polygon_graph"]["node_count"]
        == 814
    )
    assert (
        payload["evidence_geometry"]["free_space_polygon_graph"]["edge_count"]
        == 1426
    )
    assert payload["evidence_geometry"]["free_space_polygon_graph"]["metrics"] == {
        "component_count": 1,
        "cycle_rank": 613,
        "dead_end_node_count": 0,
        "dead_end_nodes": [],
    }
    assert len(
        payload["evidence_geometry"]["free_space_polygon_graph"]["anchors"]["entries"]
    ) == 4
    assert len(
        payload["evidence_geometry"]["free_space_polygon_graph"]["anchors"]["regions"]
    ) == 8
    assert len(
        payload["evidence_geometry"]["free_space_polygon_graph"][
            "entry_region_distance_evidence"
        ]
    ) == 32
    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["free_space_polygon_graph_cycle_rank"]["score"] == 613
    assert (
        path_rows["free_space_polygon_graph_mean_entry_region_distance"]["score"]
        == 349.3438
    )
    assert (
        path_rows["free_space_polygon_graph_mean_edge_clearance_width"]["score"]
        == 29.6985
    )
    assert (
        path_rows[
            "free_space_polygon_graph_mean_entry_region_min_clearance_width"
        ]["score"]
        == 30.6957
    )
    assert (
        path_rows[
            "free_space_polygon_graph_mean_entry_region_widest_clearance_width"
        ]["score"]
        == 57.2609
    )
    assert path_rows["inferred_gap_path_width_free_space_clearance_ratio"] == {
        "view_id": "path_connectivity",
        "metric": "inferred_gap_path_width_free_space_clearance_ratio",
        "score": 0.3951,
        "status": "computed",
        "method": "free_space_edge_clearance_width_over_inferred_gap_band_width",
        "evidence": {
            "free_space_mean_edge_clearance_width": 29.6985,
            "walkable_proxy_mean_thickness": 75.1667,
            "walkable_proxy_min_thickness": 44.0,
            "walkable_proxy_edge_count": 6,
        },
        "uncertainty": "ratio between rect-cell free-space shared-edge width and inferred gap-band width; proxy consistency check, not route certification",
    }
    assert (
        len(path_rows["free_space_polygon_graph_mean_edge_clearance_width"]["evidence"])
        == 1426
    )
    assert (
        payload["evidence_geometry"]["room_minus_blocker_polygons"]["count"]
        == 1
    )
    assert (
        payload["evidence_geometry"]["cad_room_minus_blocker_polygons"]["count"]
        == 1
    )
    assert payload["evidence_geometry"]["cad_room_minus_blocker_entry_connected_area"] == {
        "method": "shapely_component_entry_touched_area_ratio_proxy",
        "entry_connected_component_ids": [0],
        "non_entry_connected_component_ids": [],
        "entry_connected_component_area": 684736.0,
        "non_entry_connected_component_area": 0.0,
        "cad_room_minus_blocker_area_total": 684736.0,
        "entry_connected_area_ratio": 1.0,
    }
    assert (
        len(
            payload["evidence_geometry"][
                "cad_room_minus_blocker_component_touch_evidence"
            ]["items"]
        )
        == 1
    )
    assert (
        payload["evidence_geometry"]["cad_room_minus_blocker_component_graph"][
            "node_count"
        ]
        == 12
    )
    assert (
        payload["evidence_geometry"]["cad_room_minus_blocker_component_graph"][
            "edge_count"
        ]
        == 11
    )
    assert payload["evidence_geometry"]["negative_space_graph"]["node_count"] == 12

    non_octa = [
        row
        for row in matrix["rows"]
        if row["view_id"]
        in {"west_lounge_geometry", "center_lounge_geometry", "east_armchair_geometry"}
    ]
    assert non_octa
    assert all(not row["method"].startswith("octa") for row in non_octa)

    full_family_rows = [
        row
        for row in matrix["rows"]
        if row["view_id"]
        in {
            "region_alignment",
            "column_alignment",
            "whole_space_force",
            "path_connectivity",
            "boundary_metrics",
        }
    ]
    assert all("status" in row for row in full_family_rows)
    column_alignment = [
        row
        for row in full_family_rows
        if row["view_id"] == "column_alignment"
        and row["metric"] == "region_column_axis_agreement"
    ][0]
    assert column_alignment["status"] == "computed"
    assert column_alignment["score"] == 0.9429
    assert any(
        item["basis"] == "authored_axis_angle" and item["id"] == "column_axis_x"
        for item in column_alignment["column_axis_evidence"]
    )
    column_phase = [
        row
        for row in full_family_rows
        if row["view_id"] == "column_alignment"
        and row["metric"] == "object_column_axis_phase_alignment"
    ][0]
    assert column_phase["score"] == 0.7001
    assert len(column_phase["object_axis_phase_evidence"]) == 22
    assert column_phase["method"] == "object_center_to_nearest_column_axis_distance_kernel"
    column_bay_fit = [
        row
        for row in full_family_rows
        if row["view_id"] == "column_alignment"
        and row["metric"] == "region_column_bay_fit"
    ][0]
    assert column_bay_fit["score"] == 0.446
    assert len(column_bay_fit["region_bay_fit_evidence"]) == 7
    assert (
        column_bay_fit["method"]
        == "region_bbox_overlap_with_adjacent_column_axis_bay"
    )
    column_local_position = [
        row
        for row in full_family_rows
        if row["view_id"] == "column_alignment"
        and row["metric"] == "object_column_bay_local_position_coverage"
    ][0]
    assert column_local_position["score"] == 0.4091
    assert len(column_local_position["object_bay_local_position_evidence"]) == 22
    assert (
        column_local_position["method"]
        == "object_center_affine_position_in_nearest_column_bay"
    )
    negative_space_polygon_count = [
        row
        for row in full_family_rows
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "negative_space_free_polygon_count"
    ][0]
    assert negative_space_polygon_count["score"] == 814
    assert len(negative_space_polygon_count["free_space_polygons"]) == 814
    assert (
        negative_space_polygon_count["method"]
        == "room_polygon_rect_cell_free_space_polygons_proxy"
    )
    negative_space_polygon_adjacency = [
        row
        for row in full_family_rows
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "negative_space_free_polygon_adjacency_count"
    ][0]
    assert negative_space_polygon_adjacency["score"] == 1426
    assert len(negative_space_polygon_adjacency["free_space_polygon_adjacency"]) == 1426
    assert (
        negative_space_polygon_adjacency["method"]
        == "room_polygon_rect_cell_shared_edge_adjacency_proxy"
    )
    negative_space_region_distance = [
        row
        for row in full_family_rows
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "negative_space_mean_entry_region_free_polygon_distance"
    ][0]
    assert negative_space_region_distance["score"] == 3.1429
    assert len(
        negative_space_region_distance[
            "entry_region_free_polygon_distance_evidence"
        ]
    ) == 7
    assert (
        negative_space_region_distance["method"]
        == "entry_to_region_rect_cell_adjacency_shortest_path_proxy"
    )
    negative_space_region_path_length = [
        row
        for row in full_family_rows
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "negative_space_mean_entry_region_free_polygon_path_length"
    ][0]
    assert negative_space_region_path_length["score"] == 95.7857
    assert len(
        negative_space_region_path_length[
            "entry_region_free_polygon_distance_evidence"
        ]
    ) == 7
    assert (
        negative_space_region_path_length["method"]
        == "entry_to_region_rect_cell_centerline_length_proxy"
    )
    region_alignment = [
        row for row in full_family_rows if row["view_id"] == "region_alignment"
    ][0]
    assert region_alignment["score"] == 0.2304
    assert any(
        item["basis"] == "polygon_pca_axis"
        and item["id"] == "region_slanted_test"
        and item["angle"] == 26.5651
        for item in region_alignment["axis_evidence"]
    )
    region_phase = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "region_centroid_phase_alignment"
    ][0]
    assert region_phase["score"] == 0.6508
    assert region_phase["method"] == "region_centroid_projection_gap_cv_score"
    assert len(region_phase["region_centroid_phase_evidence"]) == 7
    inferred_iou = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "inferred_region_explicit_iou_mean"
    ][0]
    assert inferred_iou["score"] == 0.7488
    assert [
        (item["region"], item["iou"])
        for item in inferred_iou["inferred_region_explicit_iou_evidence"][:3]
    ] == [
        ("east_work", 0.4529),
        ("east_armchairs", 0.6574),
        ("north_wall", 0.6996),
    ]
    assert [
        (item["region"], item["iou"], item["dominant_mismatch"])
        for item in inferred_iou["inferred_region_explicit_iou_evidence"][-2:]
    ] == [
        ("center_lounge", 0.9502, "candidate_overflows_explicit"),
        ("west_lounge", 1.0, "aligned"),
    ]
    membership = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "object_region_membership_coverage"
    ][0]
    assert membership["score"] == 1.0
    assert membership["method"] == "object_region_rect_or_polygon_overlap_area_ratio"
    assert len(membership["object_region_membership_evidence"]) == 20
    assert membership["missing_region_evidence"] == [
        "center_misc_fixture",
        "northwest_plant",
    ]
    assignment = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "object_region_assignment_coverage"
    ][0]
    assert assignment["score"] == 0.9091
    assert assignment["matched_object_count"] == 20
    assert assignment["total_object_count"] == 22
    assert assignment["missing_region_evidence"] == [
        "center_misc_fixture",
        "northwest_plant",
    ]
    region_boundary = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "region_boundary_axis_agreement"
    ][0]
    assert region_boundary["score"] == 0.9714
    assert region_boundary["method"] == "region_axis_to_boundary_axis_similarity"
    assert region_boundary["region_boundary_matches"][-1] == {
        "region_id": "region_slanted_test",
        "region_angle": 26.5651,
        "boundary_id": "diagonal_boundary",
        "boundary_angle": 45.0,
        "score": 0.8,
    }
    sourced_region_boundary = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "region_source_boundary_axis_agreement"
    ][0]
    assert sourced_region_boundary["score"] == 0.9333
    assert (
        sourced_region_boundary["method"]
        == "region_axis_to_same_region_boundary_axis_similarity"
    )
    assert sourced_region_boundary["region_boundary_matches"] == [
        {
            "region_id": "region_west_lounge",
            "region": "west_lounge",
            "region_angle": 90.0,
            "boundary_id": "rug_boundary",
            "boundary_angle": 90.0,
            "score": 1.0,
        },
        {
            "region_id": "region_center_lounge",
            "region": "center_lounge",
            "region_angle": 90.0,
            "boundary_id": "glass_boundary",
            "boundary_angle": 90.0,
            "score": 1.0,
        },
        {
            "region_id": "region_slanted_test",
            "region": "slanted_test",
            "region_angle": 26.5651,
            "boundary_id": "diagonal_boundary",
            "boundary_angle": 45.0,
            "score": 0.8,
        },
    ]
    weighted_source_boundary = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "region_source_boundary_weighted_axis_agreement"
    ][0]
    assert weighted_source_boundary["score"] == 0.9333
    assert (
        weighted_source_boundary["method"]
        == "region_axis_to_same_region_boundary_axis_similarity_weighted_by_length_grouping_strength"
    )
    assert weighted_source_boundary["region_boundary_weighted_matches"][1] == {
        "region_id": "region_center_lounge",
        "region": "center_lounge",
        "region_angle": 90.0,
        "score": 1.0,
        "total_influence": 428.5,
        "boundary_scores": [
            {
                "boundary_id": "glass_boundary",
                "boundary_angle": 90.0,
                "length": 305.0,
                "grouping_strength": 0.9,
                "influence": 274.5,
                "score": 1.0,
            },
            {
                "boundary_id": "material_boundary",
                "boundary_angle": 0.0,
                "length": 280.0,
                "grouping_strength": 0.55,
                "influence": 154.0,
                "score": 1.0,
            },
        ],
    }
    assert weighted_source_boundary["region_boundary_weighted_matches"][-1] == {
        "region_id": "region_slanted_test",
        "region": "slanted_test",
        "region_angle": 26.5651,
        "score": 0.8,
        "total_influence": 161.2203,
        "boundary_scores": [
            {
                "boundary_id": "diagonal_boundary",
                "boundary_angle": 45.0,
                "length": 268.7006,
                "grouping_strength": 0.6,
                "influence": 161.2203,
                "score": 0.8,
            },
        ],
    }
    source_boundary_proximity = [
        row
        for row in full_family_rows
        if row["view_id"] == "region_alignment"
        and row["metric"] == "region_source_boundary_proximity"
    ][0]
    assert source_boundary_proximity["score"] == 0.9964
    assert (
        source_boundary_proximity["method"]
        == "same_region_boundary_bbox_gap_weighted_by_length_grouping_strength"
    )
    assert source_boundary_proximity["region_boundary_proximity"][1] == {
        "region_id": "region_center_lounge",
        "region": "center_lounge",
        "score": 0.9893,
        "total_influence": 428.5,
            "boundary_scores": [
                {
                    "boundary_id": "glass_boundary",
                    "length": 305.0,
                    "gap": 5.0,
                    "region_scale": 295.0,
                    "proximity": 0.9833,
                    "influence": 274.5,
                },
                {
                    "boundary_id": "material_boundary",
                    "length": 280.0,
                    "gap": 0.0,
                    "region_scale": 295.0,
                    "proximity": 1.0,
                "influence": 154.0,
            },
        ],
    }
    whole_space = [
        row for row in full_family_rows if row["view_id"] == "whole_space_force"
    ][0]
    assert any(
        item["basis"] == "group_bbox_long_axis"
        and item["id"] == "west_lounge"
        and item["angle"] == 90.0
        for item in whole_space["axis_evidence"]
    )
    group_column = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "group_column_axis_agreement"
    ][0]
    assert group_column["score"] == 1.0
    assert group_column["method"] == "group_bbox_axis_to_column_axis_similarity"
    assert group_column["group_axis_evidence"] == whole_space["axis_evidence"]
    assert group_column["column_axis_evidence"] == column_alignment["column_axis_evidence"]
    group_path = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "group_path_axis_agreement"
    ][0]
    assert group_path["score"] == 1.0
    assert group_path["method"] == "group_bbox_axis_to_path_axis_similarity"
    assert group_path["group_axis_evidence"] == whole_space["axis_evidence"]
    assert group_path["path_axis_evidence"] == [
        {"id": "path_placeholder", "angle": 0.0, "basis": "polygon_longest_edge"}
    ]
    group_boundary = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "group_boundary_axis_agreement"
    ][0]
    assert group_boundary["score"] == 1.0
    assert group_boundary["method"] == "group_bbox_axis_to_boundary_axis_similarity"
    assert group_boundary["group_axis_evidence"] == whole_space["axis_evidence"]
    assert any(
        item["id"] == "room_boundary"
        and item["angle"] == 0.0
        and item["basis"] == "polygon_longest_edge"
        for item in group_boundary["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "glass_boundary"
        and item["angle"] == 90.0
        and item["basis"] == "polygon_longest_edge"
        for item in group_boundary["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "diagonal_boundary"
        and item["angle"] == 45.0
        and item["basis"] == "polygon_longest_edge"
        for item in group_boundary["boundary_axis_evidence"]
    )
    boundary_force = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "weighted_boundary_axis_concentration"
    ][0]
    assert boundary_force["score"] == 0.2826
    assert boundary_force["method"] == "boundary_axis_weighted_by_walk_see_grouping_strength"
    assert any(
        item["id"] == "glass_boundary"
        and item["angle"] == 90.0
        and item["weight"] == 0.6833
        for item in boundary_force["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "material_boundary"
        and item["angle"] == 0.0
        and item["weight"] == 0.1833
        for item in boundary_force["boundary_axis_evidence"]
    )
    length_boundary_force = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "length_weighted_boundary_axis_concentration"
    ][0]
    assert length_boundary_force["score"] == 0.7614
    assert (
        length_boundary_force["method"]
        == "boundary_axis_weighted_by_length_walk_see_grouping_strength"
    )
    assert any(
        item["id"] == "room_boundary"
        and item["length"] == 3720.0
        and item["weight"] == 1.0
        and item["influence"] == 3720.0
        for item in length_boundary_force["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "glass_boundary"
        and item["length"] == 305.0
        and item["weight"] == 0.6833
        and item["influence"] == 208.4167
        for item in length_boundary_force["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "diagonal_boundary"
        and item["angle"] == 45.0
        and item["length"] == 268.7006
        and item["weight"] == 0.2
        and item["influence"] == 53.7401
        for item in length_boundary_force["boundary_axis_evidence"]
    )
    thickness_boundary_force = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "whole_space_force"
        and row["metric"] == "thickness_weighted_boundary_axis_concentration"
    ][0]
    assert thickness_boundary_force["score"] == 0.8463
    assert (
        thickness_boundary_force["method"]
        == "boundary_axis_weighted_by_length_thickness_walk_see_grouping_strength"
    )
    assert any(
        item["id"] == "glass_boundary"
        and item["length"] == 305.0
        and item["thickness"] == 3.0
        and item["influence"] == 625.25
        for item in thickness_boundary_force["boundary_axis_evidence"]
    )
    assert any(
        item["id"] == "rug_boundary"
        and item["thickness"] == 0.0
        and item["influence"] == 0.0
        for item in thickness_boundary_force["boundary_axis_evidence"]
    )

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["entry_path_placeholder"]["score"] == 0.1463
    assert path_rows["entry_path_placeholder"]["method"] == "path_polygon_area_ratio_with_entry_count"
    assert path_rows["entry_touch_ratio"]["score"] == 0.5
    assert path_rows["disconnected_entry_ratio"]["score"] == 0.5
    assert path_rows["disconnected_entry_ratio"]["method"] == "openings_without_path_touch_over_openings"
    assert path_rows["disconnected_entry_ratio"]["evidence"] == [
        "left_entry",
        "right_entry_line",
    ]
    assert path_rows["disconnected_path_ratio"]["score"] == 0.0
    assert path_rows["disconnected_path_ratio"]["method"] == "paths_without_entry_touch_over_paths"
    assert path_rows["disconnected_path_ratio"]["path_entry_touch_evidence"] == [
        {
            "id": "path_placeholder",
            "touched_entry_ids": ["bottom_entry", "right_entry_arc"],
        },
    ]
    assert path_rows["path_region_touch_ratio"]["score"] == 0.7143
    assert path_rows["path_touched_region_boundary_cue_ratio"]["score"] == 0.4
    assert path_rows["path_region_split_tendency_proxy"]["score"] == 0.3029
    assert (
        path_rows["path_region_split_tendency_proxy"]["method"]
        == "path_region_touch_width_continuity_minus_boundary_grouping_proxy"
    )
    assert path_rows["path_touched_region_boundary_cue_count_mean"]["score"] == 0.6
    assert (
        path_rows["path_touched_region_boundary_cue_count_mean"]["method"]
        == "path_touched_region_same_region_boundary_cue_count_mean"
    )
    assert (
        path_rows["path_touched_region_boundary_cue_ratio"]["method"]
        == "path_touched_regions_with_same_region_boundary_proximity"
    )
    assert path_rows["path_touched_region_boundary_cue_strength_mean"]["score"] == 0.3979
    assert (
        path_rows["path_touched_region_boundary_cue_strength_mean"]["method"]
        == "path_touched_region_same_region_boundary_proximity_mean"
    )
    assert path_rows["path_touched_region_boundary_grouping_strength_mean"]["score"] == 0.3165
    assert (
        path_rows["path_touched_region_boundary_grouping_strength_mean"]["method"]
        == "path_touched_region_same_region_boundary_length_weighted_grouping_strength_mean"
    )
    assert path_rows["path_touched_region_boundary_walk_block_mean"]["score"] == 0.1043
    assert path_rows["path_touched_region_boundary_see_block_mean"]["score"] == 0.0156
    assert path_rows["path_touched_region_boundary_walk_see_gap_mean"]["score"] == 0.0886
    assert (
        path_rows["path_touched_region_boundary_walk_see_gap_mean"]["method"]
        == "path_touched_region_same_region_boundary_length_weighted_walk_see_gap_mean"
    )
    assert path_rows["path_touched_region_boundary_cue_perimeter_influence_mean"]["score"] == 0.1209
    assert (
        path_rows["path_touched_region_boundary_cue_perimeter_influence_mean"]["method"]
        == "path_touched_region_same_region_boundary_influence_per_region_bbox_perimeter_mean"
    )
    cue_evidence = {
        item["region_id"]: item
        for item in path_rows["path_touched_region_boundary_cue_ratio"][
            "path_region_boundary_cue_evidence"
        ]
    }
    assert len(cue_evidence) == 5
    assert cue_evidence["region_north_tables"]["has_boundary_cue"] is False
    assert cue_evidence["region_west_lounge"]["boundary_cue_kinds"] == ["rug"]
    assert cue_evidence["region_center_lounge"]["boundary_cue_kinds"] == [
        "glass",
        "material",
    ]
    assert cue_evidence["region_center_lounge"]["boundary_walk_see_gap"] == 0.4432
    assert cue_evidence["region_east_armchairs"]["has_boundary_cue"] is False
    assert matrix["isovist_radial_proxy"]["metrics"]["ray_count"] == 88
    assert matrix["isovist_radial_proxy"]["metrics"]["blocked_ray_count"] == 20
    assert matrix["isovist_radial_proxy"]["metrics"]["mean_hit_distance"] == 332.0904
    visual_handoff = payload["visual_analysis_handoff"]
    assert len(visual_handoff["visibility_graph"]["items"]) == 28
    assert len(visual_handoff["isovist_radial_proxy"]["ray_items"]) == 88
    assert len(visual_handoff["isovist_radial_proxy"]["area_items"]) == 11
    assert {
        **visual_handoff,
        "visibility_graph": {
            key: value
            for key, value in visual_handoff["visibility_graph"].items()
            if key != "items"
        },
        "isovist_radial_proxy": {
            key: value
            for key, value in visual_handoff["isovist_radial_proxy"].items()
            if key not in {"ray_items", "area_items"}
        },
    } == {
        "method": "adapter_visual_analysis_handoff_from_existing_visibility_proxies",
        "visibility_graph": {
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "node_count": 11,
            "edge_count": 28,
            "visible_edge_ratio": 0.7143,
            "blocked_edge_ratio": 0.2857,
            "blocking_boundary_count": 3,
        },
        "isovist_radial_proxy": {
            "method": "radial_isovist_see_block_ray_intersection_proxy",
            "status": "computed",
            "vantage_count": 11,
            "ray_count": 88,
            "blocked_ray_count": 20,
            "blocked_ray_ratio": 0.2273,
            "mean_hit_distance": 332.0904,
            "mean_hit_polygon_area": 415076.4205,
        },
        "uncertainty": "visual analysis handoff only; replace centerline visibility and radial ray proxies with full isovist polygons, VGA, or calibrated visual integration downstream",
    }
    assert payload["material_calibration_handoff"] == {
        "method": "adapter_material_calibration_handoff_from_authored_boundary_weights",
        "weight_metadata": {
            "method": "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records",
            "coverage": 1.0,
            "missing_ids": [],
        },
        "channel_means": {
            "walk_block": 0.4615,
            "see_block": 0.3962,
            "grouping_strength": 0.6077,
            "walk_see_block_gap": 0.0654,
            "non_blocking_grouping_cue": 0.1538,
        },
        "calibration_candidates": [
            {
                "id": "glass_boundary",
                "kind": "glass",
                "walk_block": 1.0,
                "see_block": 0.15,
                "grouping_strength": 0.9,
                "thickness": 3.0,
            },
            {
                "id": "rug_boundary",
                "kind": "rug",
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.85,
                "thickness": 0.0,
            },
            {
                "id": "material_boundary",
                "kind": "material",
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.55,
                "thickness": 0.0,
            },
            {
                "id": "diagonal_boundary",
                "kind": "visual",
                "walk_block": 0.0,
                "see_block": 0.0,
                "grouping_strength": 0.6,
                "thickness": 0.0,
            },
        ],
        "uncertainty": "material calibration handoff only; authored walk/see/grouping weights and thickness metadata must be replaced or calibrated from Rhino/BIM materials, lighting, and perception data downstream",
    }
    column_grid_handoff = payload["column_grid_handoff"]
    assert len(column_grid_handoff["axes"]["items"]) == 2
    assert len(column_grid_handoff["region_bays"]["items"]) == 7
    assert len(column_grid_handoff["object_bay_local_positions"]["items"]) == 22
    assert len(column_grid_handoff["C_global"]["items"]) == 14
    assert len(column_grid_handoff["C_local_profile"]["items"]) == 0
    assert {
        **column_grid_handoff,
        "axes": {
            key: value
            for key, value in column_grid_handoff["axes"].items()
            if key != "items"
        },
        "region_bays": {
            key: value
            for key, value in column_grid_handoff["region_bays"].items()
            if key != "items"
        },
        "object_bay_local_positions": {
            key: value
            for key, value in column_grid_handoff["object_bay_local_positions"].items()
            if key != "items"
        },
        "C_global": {
            key: value
            for key, value in column_grid_handoff["C_global"].items()
            if key != "items"
        },
        "C_local_profile": {
            key: value
            for key, value in column_grid_handoff["C_local_profile"].items()
            if key != "items"
        },
    } == {
        "method": "adapter_column_grid_handoff_from_existing_column_alignment_rows",
        "axes": {
            "method": "region_bbox_axis_to_column_axis_similarity",
            "axis_count": 2,
            "axis_ids": ["column_axis_x", "column_axis_y"],
            "region_axis_agreement": 0.9429,
        },
        "object_phase": {
            "method": "object_center_to_nearest_column_axis_distance_kernel",
            "score": 0.7001,
            "evidence_count": 22,
        },
        "region_bays": {
            "method": "region_bbox_overlap_with_adjacent_column_axis_bay",
            "score": 0.446,
            "evidence_count": 7,
        },
        "object_bay_local_positions": {
            "method": "object_center_affine_position_in_nearest_column_bay",
            "score": 0.4091,
            "evidence_count": 22,
        },
        "C_global": {
            "method": "explicit_column_grid_region_to_system_branch_frame_agreement",
            "score": 1.0,
            "evidence_count": 14,
        },
        "C_local_profile": {
            "method": "not_available",
            "score": None,
            "evidence_count": 0,
        },
        "uncertainty": "column-grid handoff only; authored axis and bay proxies must be replaced by Rhino/BIM grid topology or irregular local grid interpolation downstream",
    }
    assert payload["adapter_capability_matrix"] == {
        "method": "adapter_capability_matrix_from_current_payload_handoffs",
        "ready_handoffs": [
            "host_relationships",
            "route_topology_handoff",
            "visual_analysis_handoff",
            "material_calibration_handoff",
            "column_grid_handoff",
        ],
        "capabilities": [
            {
                "name": "host_relationships",
                "status": "proxy_handoff",
                "replacement": "live Rhino/VisualARQ/BIM hosted opening topology",
            },
            {
                "name": "route_topology_handoff",
                "status": "proxy_handoff",
                "replacement": "navmesh, medial-axis, skeleton, or hosted BIM topology",
            },
            {
                "name": "visual_analysis_handoff",
                "status": "proxy_handoff",
                "replacement": "full isovist polygons, VGA, or calibrated visual integration",
            },
            {
                "name": "material_calibration_handoff",
                "status": "metadata_handoff",
                "replacement": "Rhino/BIM materials, lighting, and perception calibration",
            },
            {
                "name": "column_grid_handoff",
                "status": "proxy_handoff",
                "replacement": "Rhino/BIM grid topology or irregular local grid interpolation",
            },
        ],
        "open_uncertainty_routes": {
            "geometry_upgrade": 8,
            "perception_experiment": 8,
            "bim_mapping": 8,
            "method_replacement": 8,
        },
        "uncertainty": "capability matrix is a handoff readiness index only; it does not prove live adapter execution, hosted topology, validated geometry, material calibration, or final route/visibility analysis",
    }
    assert payload["notebook_audit_manifest"] == {
        "method": "notebook_audit_manifest_for_clean_ordered_evidence_overlay",
        "section_order": [
            "1. Source Fixture",
            "2. Evaluation Summary",
            "3. Metric Matrix",
            "4. Clean Evidence Overlay",
            "5. Audit Snapshot",
        ],
        "default_overlay": {
            "function": "scene_metric_overlay_svg(scene, matrix)",
            "include_free_space_paths": False,
            "dense_free_space_paths_layer": "free-space-graph-entry-region-path",
        },
        "optional_dense_layers": ["free-space-graph-entry-region-path"],
        "status": "ordered_clean_overlay",
        "uncertainty": "notebook audit manifest describes current executable notebook display policy only; it is not visual QA for every rendered layer or a final presentation layout",
    }
    assert path_rows["isovist_radial_blocked_ray_ratio"]["score"] == 0.2273
    assert path_rows["entry_to_region_reachability"]["score"] == 0.3571
    assert path_rows["line_of_sight_entry_region_ratio"]["score"] == 1.0
    assert (
        path_rows["line_of_sight_entry_region_ratio"]["method"]
        == "entry_region_centerline_see_block_intersection"
    )
    assert len(path_rows["line_of_sight_entry_region_ratio"]["line_of_sight_evidence"]) == 7
    assert path_rows["line_of_sight_region_pair_ratio"]["score"] == 0.619
    assert (
        path_rows["line_of_sight_region_pair_ratio"]["method"]
        == "region_pair_centerline_see_block_intersection"
    )
    assert len(path_rows["line_of_sight_region_pair_ratio"]["line_of_sight_region_pair_evidence"]) == 21
    assert path_rows["sampled_grid_resolution"]["score"] == 55.0
    assert path_rows["sampled_grid_resolution"]["method"] == "sampled_grid_cell_size_scene_units"
    assert path_rows["sampled_min_clearance_to_walk_blocker"]["score"] == 0.0
    assert (
        path_rows["sampled_min_clearance_to_walk_blocker"]["method"]
        == "sampled_free_cell_center_to_nearest_walk_blocker_gap"
    )
    fixture_clearance = path_rows["sampled_min_clearance_to_walk_blocker"]["clearance"]
    assert fixture_clearance["mean_clearance"] == 44.3584
    assert fixture_clearance["sample_count"] == 262
    assert fixture_clearance["zero_clearance_sample_count"] == 10
    assert fixture_clearance["min_clearance_samples"][0] == {
        "cell": (2, 1),
        "point": (82.5, 137.5),
        "blocker_id": "northwest_plant",
        "distance": 0.0,
    }
    assert path_rows["sampled_zero_clearance_cell_ratio"]["score"] == 0.0382
    assert (
        path_rows["sampled_zero_clearance_cell_ratio"]["method"]
        == "sampled_zero_clearance_cells_over_clearance_samples"
    )
    assert (
        path_rows["sampled_entry_reachable_min_clearance_to_walk_blocker"]["score"]
        == 0.0
    )
    assert (
        path_rows["sampled_entry_reachable_min_clearance_to_walk_blocker"]["method"]
        == "sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap"
    )
    assert (
        path_rows["sampled_entry_reachable_min_clearance_to_walk_blocker"][
            "clearance"
        ]["zero_clearance_sample_count"]
        == 10
    )

    boundary_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "boundary_metrics"
    }
    assert boundary_rows["walk_block_mean"]["score"] == 0.4615
    assert boundary_rows["see_block_mean"]["score"] == 0.3962
    assert boundary_rows["closed_blocking_boundary_ratio"]["score"] == 0.5556
    assert (
        boundary_rows["closed_blocking_boundary_ratio"]["method"]
        == "walk_and_see_blocking_boundaries_over_boundaries"
    )
    assert boundary_rows["closed_blocking_boundary_ratio"]["evidence"] == [
        "room_boundary",
        "outer_wall",
        "north_short_wall",
        "bottom_partition",
        "internal_partition",
    ]
    assert boundary_rows["walk_see_block_gap_mean"]["score"] == 0.0654
    assert (
        boundary_rows["walk_see_block_gap_mean"]["method"]
        == "mean_abs_walk_block_minus_see_block"
    )
    assert boundary_rows["grouping_strength_mean"]["score"] == 0.6077
    assert boundary_rows["non_blocking_grouping_cue_mean"]["score"] == 0.1538
    assert boundary_rows["boundary_weight_metadata_coverage"]["score"] == 1.0
    assert len(
        boundary_rows["boundary_weight_metadata_coverage"][
            "weight_metadata_evidence"
        ]
    ) == 13
    assert (
        boundary_rows["boundary_weight_metadata_coverage"][
            "missing_weight_metadata_ids"
        ]
        == []
    )
    assert (
        boundary_rows["non_blocking_grouping_cue_mean"]["method"]
        == "mean_grouping_strength_without_walk_or_see_block"
    )
    assert boundary_rows["entry_width_mean"]["score"] == 93.75
    assert (
        boundary_rows["entry_width_mean"]["method"]
        == "opening_width_metadata_or_rect_max_dimension_mean"
    )
    assert boundary_rows["entry_width_mean"]["entry_widths"] == [
        {
            "id": "left_entry",
            "edge": "left",
            "width": 35.0,
            "center": (17.5, 150.0),
            "width_source": "opening_bbox_max_dimension",
        },
        {
            "id": "bottom_entry",
            "edge": "bottom",
            "width": 95.0,
            "center": (457.5, 882.5),
            "width_source": "opening_bbox_max_dimension",
        },
        {
            "id": "right_entry_arc",
            "edge": "right",
            "width": 120.0,
            "center": (905.0, 795.0),
            "width_source": "opening_bbox_max_dimension",
        },
        {
            "id": "right_entry_line",
            "edge": "right",
            "width": 125.0,
            "center": (965.0, 672.5),
            "width_source": "opening_bbox_max_dimension",
        },
    ]
    assert boundary_rows["opening_width_room_perimeter_ratio"]["score"] == 0.1027
    assert (
        boundary_rows["opening_width_room_perimeter_ratio"]["method"]
        == "sum_opening_width_over_room_boundary_bbox_perimeter"
    )
    assert boundary_rows["opening_width_room_perimeter_ratio"]["room_boundary_id"] == "room_boundary"
    assert boundary_rows["opening_width_room_boundary_length_ratio"]["score"] == 0.1008
    assert (
        boundary_rows["opening_width_room_boundary_length_ratio"]["method"]
        == "sum_opening_width_over_room_boundary_polyline_length"
    )
    assert boundary_rows["opening_width_room_boundary_length_ratio"]["room_boundary_length"] == 3720.0
    assert boundary_rows["boundary_thickness_mean"]["score"] == 4.4444
    assert boundary_rows["boundary_thickness_mean"]["method"] == "authored_boundary_thickness_mean"
    assert boundary_rows["boundary_thickness_mean"]["thickness_evidence"] == [
        {"id": "room_boundary", "kind": "room", "thickness": 8.0},
        {"id": "outer_wall", "kind": "wall", "thickness": 8.0},
        {"id": "north_short_wall", "kind": "wall", "thickness": 8.0},
        {"id": "bottom_partition", "kind": "wall", "thickness": 8.0},
        {"id": "internal_partition", "kind": "partition", "thickness": 5.0},
        {"id": "glass_boundary", "kind": "glass", "thickness": 3.0},
        {"id": "rug_boundary", "kind": "rug", "thickness": 0.0},
        {"id": "material_boundary", "kind": "material", "thickness": 0.0},
        {"id": "diagonal_boundary", "kind": "visual", "thickness": 0.0},
    ]
    assert boundary_rows["entry_boundary_position_coverage"]["score"] == 0.5289
    assert (
        boundary_rows["entry_boundary_position_coverage"]["method"]
        == "entry_center_projection_ratio_on_room_boundary_polyline"
    )
    assert boundary_rows["entry_boundary_position_coverage"]["entry_positions"] == [
        {
            "id": "left_entry",
            "edge": "left",
            "boundary_distance": 3605.0,
            "boundary_ratio": 0.9691,
            "projected_point": (35.0, 150.0),
            "projection_gap": 17.5,
        },
        {
            "id": "bottom_entry",
            "edge": "bottom",
            "boundary_distance": 2402.5,
            "boundary_ratio": 0.6458,
            "projected_point": (457.5, 930.0),
            "projection_gap": 47.5,
        },
        {
            "id": "right_entry_arc",
            "edge": "right",
            "boundary_distance": 1760.0,
            "boundary_ratio": 0.4731,
            "projected_point": (965.0, 795.0),
            "projection_gap": 60.0,
        },
        {
            "id": "right_entry_line",
            "edge": "right",
            "boundary_distance": 1637.5,
            "boundary_ratio": 0.4402,
            "projected_point": (965.0, 672.5),
            "projection_gap": 0.0,
        },
    ]
    assert boundary_rows["entry_nearest_boundary_gap_mean"]["score"] == 31.25
    assert (
        boundary_rows["entry_nearest_boundary_gap_mean"]["method"]
        == "entry_center_to_nearest_boundary_geometry_gap_mean"
    )
    assert boundary_rows["entry_nearest_boundary_gap_mean"]["entry_boundary_associations"] == [
        {
            "id": "left_entry",
            "edge": "left",
            "width": 35.0,
            "center": (17.5, 150.0),
            "width_source": "opening_bbox_max_dimension",
            "boundary_id": "room_boundary",
            "boundary_kind": "room",
            "gap": 17.5,
            "projected_point": (35.0, 150.0),
            "association_method": "nearest_boundary_geometry",
        },
        {
            "id": "bottom_entry",
            "edge": "bottom",
            "width": 95.0,
            "center": (457.5, 882.5),
            "width_source": "opening_bbox_max_dimension",
            "boundary_id": "room_boundary",
            "boundary_kind": "room",
            "gap": 47.5,
            "projected_point": (457.5, 930.0),
            "association_method": "nearest_boundary_geometry",
        },
        {
            "id": "right_entry_arc",
            "edge": "right",
            "width": 120.0,
            "center": (905.0, 795.0),
            "width_source": "opening_bbox_max_dimension",
            "boundary_id": "room_boundary",
            "boundary_kind": "room",
            "gap": 60.0,
            "projected_point": (965.0, 795.0),
            "association_method": "nearest_boundary_geometry",
        },
        {
            "id": "right_entry_line",
            "edge": "right",
            "width": 125.0,
            "center": (965.0, 672.5),
            "width_source": "opening_bbox_max_dimension",
            "boundary_id": "room_boundary",
            "boundary_kind": "room",
            "gap": 0.0,
            "projected_point": (965.0, 672.5),
            "association_method": "nearest_boundary_geometry",
        },
    ]
    assert boundary_rows["hosted_entry_boundary_ratio"]["score"] == 0.0
    assert boundary_rows["hosted_entry_boundary_ratio"]["evidence"] == []
    assert boundary_rows["fallback_entry_boundary_ratio"]["score"] == 1.0
    assert boundary_rows["fallback_entry_boundary_ratio"]["evidence"] == [
        "left_entry",
        "bottom_entry",
        "right_entry_arc",
        "right_entry_line",
    ]
    assert boundary_rows["boundary_opening_width_ratio_max"]["score"] == 0.1008
    assert (
        boundary_rows["boundary_opening_width_ratio_max"]["method"]
        == "sum_associated_opening_width_over_boundary_length"
    )
    assert boundary_rows["boundary_opening_width_ratio_max"]["boundary_opening_evidence"][0] == {
        "id": "room_boundary",
        "kind": "room",
        "length": 3720.0,
        "opening_width": 375.0,
        "opening_ratio": 0.1008,
        "opening_ids": [
            "left_entry",
            "bottom_entry",
            "right_entry_arc",
            "right_entry_line",
        ],
    }
    assert any(
        item["id"] == "glass_boundary"
        and item["length"] == 305.0
        and item["opening_width"] == 0.0
        and item["opening_ratio"] == 0.0
        and item["opening_ids"] == []
        for item in boundary_rows["boundary_opening_width_ratio_max"]["boundary_opening_evidence"]
    )
    assert any(
        item["id"] == "diagonal_boundary"
        and item["length"] == 268.7006
        and item["opening_width"] == 0.0
        and item["opening_ratio"] == 0.0
        and item["opening_ids"] == []
        for item in boundary_rows["boundary_opening_width_ratio_max"]["boundary_opening_evidence"]
    )
    assert boundary_rows["boundary_path_connected_opening_ratio_max"]["score"] == 0.5
    assert (
        boundary_rows["boundary_path_connected_opening_ratio_max"]["method"]
        == "path_connected_openings_over_associated_openings_by_boundary"
    )
    assert boundary_rows["boundary_path_connected_opening_ratio_max"]["boundary_path_opening_evidence"][0] == {
        "id": "room_boundary",
        "kind": "room",
        "opening_count": 4,
        "path_connected_opening_count": 2,
        "path_connected_opening_ratio": 0.5,
        "opening_ids": [
            "left_entry",
            "bottom_entry",
            "right_entry_arc",
            "right_entry_line",
        ],
        "path_connected_opening_ids": ["bottom_entry", "right_entry_arc"],
        "path_disconnected_opening_ids": ["left_entry", "right_entry_line"],
    }
    assert boundary_rows["glass_walk_see_gap"]["score"] == 0.85
    assert boundary_rows["rug_grouping_without_block"]["score"] == 0.85

    uncertainty = [row for row in matrix["rows"] if row["view_id"] == "uncertainties"][0]
    assert "column-grid alignment unavailable without column metadata" not in uncertainty["evidence"]
    route_rows = [
        row for row in matrix["rows"]
        if row["view_id"] == "uncertainties"
        and row["metric"] == "uncertainty_routes"
    ]
    assert len(route_rows) == 1
    route_row = route_rows[0]
    assert route_row["score"] == 4
    assert route_row["status"] == "computed"
    assert route_row["method"] == "keyword_route_summary_from_metric_uncertainty_text"
    assert route_row["evidence"] == [
        "geometry_upgrade",
        "perception_experiment",
        "bim_mapping",
        "method_replacement",
    ]
    assert "region_column_bay_fit" in route_row["route_evidence"]["geometry_upgrade"]
    assert (
        "isovist_radial_blocked_ray_ratio"
        in route_row["route_evidence"]["perception_experiment"]
    )
    assert "inferred_region_count" in route_row["route_evidence"]["perception_experiment"]
    assert "glass_walk_see_gap" in boundary_rows
    assert (
        "thickness_weighted_boundary_axis_concentration"
        in route_row["route_evidence"]["bim_mapping"]
    )
    assert "inferred_region_explicit_iou_mean" in route_row["route_evidence"]["method_replacement"]
    assert (
        route_row["uncertainty"]
        == "routes are keyword summaries of declared metric uncertainty text, not a substitute for method validation"
    )


def test_evaluate_scene_returns_path_graph_evidence():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    graph = matrix["graph"]
    negative_space_graph = matrix["negative_space_graph"]
    node_kinds = {node["kind"] for node in graph["nodes"]}
    edge_kinds = {edge["kind"] for edge in graph["edges"]}

    assert {"entry", "path", "region"} <= node_kinds
    assert {"entry_path_touch", "path_region_touch"} <= edge_kinds
    assert any(
        node["kind"] == "negative_space_component"
        for node in negative_space_graph["nodes"]
    )
    assert {
        "entry_negative_space_component_touch",
        "negative_space_component_region_touch",
    } <= {edge["kind"] for edge in negative_space_graph["edges"]}
    assert {
        edge["refs"]["entry"] for edge in negative_space_graph["edges"]
        if edge["kind"] == "entry_negative_space_component_touch"
    } == {"bottom_entry", "left_entry", "right_entry_arc", "right_entry_line"}

    reachability = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "entry_to_region_reachability"
    ][0]
    assert reachability["score"] == 0.3571
    assert all(evidence_id.startswith("edge_") for evidence_id in reachability["evidence"])

    entry_touch = [
        row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
        and row["metric"] == "entry_touch_ratio"
    ][0]
    assert entry_touch["entry_touch_evidence"] == [
        {
            "id": "left_entry",
            "edge": "left",
            "width": 35.0,
            "boundary_id": "room_boundary",
            "boundary_gap": 17.5,
            "touched_path_ids": [],
        },
        {
            "id": "bottom_entry",
            "edge": "bottom",
            "width": 95.0,
            "boundary_id": "room_boundary",
            "boundary_gap": 47.5,
            "touched_path_ids": ["path_placeholder"],
        },
        {
            "id": "right_entry_arc",
            "edge": "right",
            "width": 120.0,
            "boundary_id": "room_boundary",
            "boundary_gap": 60.0,
            "touched_path_ids": ["path_placeholder"],
        },
        {
            "id": "right_entry_line",
            "edge": "right",
            "width": 125.0,
            "boundary_id": "room_boundary",
            "boundary_gap": 0.0,
            "touched_path_ids": [],
        },
    ]


def test_evaluate_scene_splits_walk_and_visibility_graph_evidence():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    graphs = matrix["graphs"]
    assert {"walk", "visibility"} <= set(graphs)

    walk_edge = graphs["walk"]["edges"][0]
    visibility_edge = graphs["visibility"]["edges"][0]

    assert walk_edge["mode"] == "walk"
    assert visibility_edge["mode"] == "visibility"
    assert "walk_cost" in walk_edge
    assert "visibility_cost" in visibility_edge
    assert walk_edge["walk_cost"] >= visibility_edge["visibility_cost"]

    boundary_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert boundary_rows["walk_visibility_cost_gap"]["score"] == 0.0653


def test_evaluate_scene_reports_basic_path_graph_topology_metrics():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    walk_metrics = matrix["graphs"]["walk"]["metrics"]
    assert walk_metrics["entry_region_reachability"] == 0.7143
    assert walk_metrics["reached_region_ids"] == [
        "region_center_lounge",
        "region_east_armchairs",
        "region_east_work",
        "region_north_tables",
        "region_west_lounge",
    ]
    assert walk_metrics["unreached_region_ids"] == [
        "region_north_wall",
        "region_slanted_test",
    ]
    assert walk_metrics["entry_region_mean_hops"] == 2.0
    assert walk_metrics["dead_end_ratio"] == 0.9167
    assert walk_metrics["component_count"] == 5
    assert walk_metrics["components"] == [
        ["node_entry_left_entry"],
        [
            "node_entry_bottom_entry",
            "node_entry_right_entry_arc",
            "node_path_path_placeholder",
            "node_region_region_center_lounge",
            "node_region_region_east_armchairs",
            "node_region_region_east_work",
            "node_region_region_north_tables",
            "node_region_region_west_lounge",
        ],
        ["node_entry_right_entry_line"],
        ["node_region_region_north_wall"],
        ["node_region_region_slanted_test"],
    ]
    assert walk_metrics["loop_count"] == 0
    assert walk_metrics["loop_ratio"] == 0.0
    assert walk_metrics["cycle_rank_inputs"] == {
        "node_count": 12,
        "edge_count": 7,
        "component_count": 5,
    }

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["graph_entry_region_reachability"]["score"] == 0.7143
    assert path_rows["graph_entry_region_reachability"]["reached_region_ids"] == [
        "region_center_lounge",
        "region_east_armchairs",
        "region_east_work",
        "region_north_tables",
        "region_west_lounge",
    ]
    assert path_rows["graph_entry_region_reachability"]["unreached_region_ids"] == [
        "region_north_wall",
        "region_slanted_test",
    ]
    assert path_rows["graph_entry_region_capacity_proxy"]["score"] == 0.2386
    assert (
        path_rows["graph_entry_region_capacity_proxy"]["method"]
        == "bbox_touch_reachability_times_path_width_times_walk_passability"
    )
    assert path_rows["graph_entry_region_capacity_proxy"]["capacity_factors"] == {
        "entry_region_reachability": 0.7143,
        "path_width_continuity": 0.6204,
        "walk_passability": 0.5385,
    }
    assert path_rows["graph_mean_entry_region_hops"]["score"] == 2.0
    assert path_rows["graph_dead_end_ratio"]["score"] == 0.9167
    assert path_rows["graph_dead_end_ratio"]["dead_end_nodes"] == [
        {"id": "node_entry_left_entry", "kind": "entry", "degree": 0},
        {"id": "node_entry_bottom_entry", "kind": "entry", "degree": 1},
        {"id": "node_entry_right_entry_arc", "kind": "entry", "degree": 1},
        {"id": "node_entry_right_entry_line", "kind": "entry", "degree": 0},
        {"id": "node_region_region_north_tables", "kind": "region", "degree": 1},
        {"id": "node_region_region_west_lounge", "kind": "region", "degree": 1},
        {"id": "node_region_region_center_lounge", "kind": "region", "degree": 1},
        {"id": "node_region_region_east_work", "kind": "region", "degree": 1},
        {"id": "node_region_region_east_armchairs", "kind": "region", "degree": 1},
        {"id": "node_region_region_north_wall", "kind": "region", "degree": 0},
        {"id": "node_region_region_slanted_test", "kind": "region", "degree": 0},
    ]
    assert path_rows["graph_component_count"] == {
        "view_id": "path_connectivity",
        "metric": "graph_component_count",
        "score": 5,
        "status": "computed",
        "method": "bbox_touch_graph_connected_components",
        "evidence": [
            ["node_entry_left_entry"],
            [
                "node_entry_bottom_entry",
                "node_entry_right_entry_arc",
                "node_path_path_placeholder",
                "node_region_region_center_lounge",
                "node_region_region_east_armchairs",
                "node_region_region_east_work",
                "node_region_region_north_tables",
                "node_region_region_west_lounge",
            ],
            ["node_entry_right_entry_line"],
            ["node_region_region_north_wall"],
            ["node_region_region_slanted_test"],
        ],
        "uncertainty": "connected components over proxy graph; route graph component extraction pending",
    }
    assert path_rows["graph_loop_count"]["score"] == 0
    assert path_rows["graph_loop_count"]["cycle_rank_inputs"] == {
        "node_count": 12,
        "edge_count": 7,
        "component_count": 5,
    }
    assert path_rows["graph_loop_ratio"]["score"] == 0.0
    assert path_rows["graph_loop_ratio"]["method"] == "undirected_cycle_rank_over_edge_count"
    assert path_rows["graph_loop_ratio"]["cycle_rank_inputs"] == {
        "node_count": 12,
        "edge_count": 7,
        "component_count": 5,
    }


def test_evaluate_scene_reports_proxy_shortest_path_and_detour_metrics():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    walk_metrics = matrix["graphs"]["walk"]["metrics"]
    assert walk_metrics["entry_region_mean_shortest_distance"] == 581.1641
    assert walk_metrics["entry_region_mean_detour_ratio"] == 2.8983

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["graph_mean_entry_region_shortest_distance"]["score"] == 581.1641
    assert path_rows["graph_mean_entry_region_detour_ratio"]["score"] == 2.8983
    assert "proxy" in path_rows["graph_mean_entry_region_detour_ratio"]["uncertainty"]


def test_evaluate_scene_reports_path_width_continuity_from_path_geometry():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    path_geometry = matrix["path_geometry"]["path_placeholder"]
    assert path_geometry["width_samples"] == [305.0, 150.0, 90.0, 65.0]
    assert path_geometry["width_continuity"] == 0.6204

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["path_width_continuity"]["score"] == 0.6204
    assert path_rows["path_width_continuity"]["evidence"] == ["path_placeholder"]
    assert path_rows["candidate_path_area_ratio_proxy"]["score"] == 0.6204
    assert path_rows["candidate_path_area_ratio_proxy"]["candidate_path_inputs"] == {
        "negative_space_entry_connected_area_ratio": 1.0,
        "path_width_continuity": 0.6204,
    }


def test_evaluate_scene_reports_path_clearance_to_blocker_proxy():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    path_geometry = matrix["path_geometry"]["path_placeholder"]
    assert path_geometry["clearance_samples"]
    samples = {
        sample["target_id"]: sample["distance"]
        for sample in path_geometry["clearance_samples"]
    }
    assert path_geometry["min_clearance_to_blocker"] == 0.0
    assert path_geometry["blocker_overlap_count"] == 11
    assert path_geometry["blocker_overlap_ratio"] == 0.4231
    assert path_geometry["path_polygon_area"] == 146300.0
    assert path_geometry["blocker_overlap_area"] == 26748.0
    assert path_geometry["summed_blocker_overlap_area"] == 26748.0
    assert path_geometry["blocker_overlap_area_ratio"] == 0.1828
    assert any(
        sample["target_id"] == "center_misc_fixture" and sample["distance"] == 0.0
        for sample in path_geometry["clearance_samples"]
    )
    assert samples["west_sofa_2"] > 200.0

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    clearance = path_rows["path_min_clearance_to_blocker"]
    assert clearance["score"] == 0.0
    assert "path_placeholder" in clearance["evidence"]
    assert "center_misc_fixture" in clearance["evidence"]
    assert clearance["method"] == "path_polygon_to_blocker_bbox_min_gap"
    assert "bbox" in clearance["uncertainty"]
    assert "not a medial-axis" in clearance["uncertainty"]

    overlap = path_rows["path_blocker_overlap_ratio"]
    assert overlap["score"] == 0.4231
    assert overlap["method"] == "path_polygon_blocker_bbox_zero_gap_ratio"
    assert "center_misc_fixture" in overlap["evidence"]
    assert "proxy" in overlap["uncertainty"]

    area = path_rows["path_blocker_overlap_area_ratio"]
    assert area["score"] == 0.1828
    assert area["method"] == "path_polygon_blocker_union_overlap_area"
    assert "east_work_chair" in area["evidence"]
    assert "glass_boundary" not in area["evidence"]
    assert "union" in area["uncertainty"]


def test_path_blocker_overlap_area_deduplicates_overlapping_rect_blockers():
    from features.affordance.models import Rect

    def record(record_id, role, rect, *, kind=None, walk_block=0.0):
        return {
            "id": record_id,
            "role": role,
            "group": "global",
            "region": "room",
            "rect": rect,
            "points": [],
            "weights": {
                "walk_block": walk_block,
                "see_block": walk_block,
                "grouping_strength": walk_block,
            },
            "metadata": {"boundary-kind": kind} if kind else {},
        }

    room = record(
        "room_boundary",
        "boundary",
        Rect(cx=50, cy=50, width=100, height=100),
        kind="room",
        walk_block=1.0,
    )
    scene = {
        "source": "synthetic_path_overlapping_blockers",
        "size": (100.0, 100.0),
        "objects": [
            record("left_table", "table", Rect(cx=40, cy=50, width=60, height=60)),
            record("right_table", "table", Rect(cx=60, cy=50, width=60, height=60)),
        ],
        "boundaries": [room],
        "entries": [],
        "paths": [
            record("path", "path", Rect(cx=50, cy=50, width=100, height=100)),
        ],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }

    matrix = evaluate_scene(scene)
    path_geometry = matrix["path_geometry"]["path"]

    assert path_geometry["blocker_overlap_area"] == 4800.0
    assert path_geometry["summed_blocker_overlap_area"] == 7200.0
    assert path_geometry["blocker_overlap_area_ratio"] == 0.48

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["path_blocker_overlap_area_ratio"]["score"] == 0.48
    assert (
        path_rows["path_blocker_overlap_area_ratio"]["method"]
        == "path_polygon_blocker_union_overlap_area"
    )


def test_evaluate_scene_reports_sampled_walkable_space_proxy():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)

    descriptor = matrix["sampled_walkable_space"]
    assert descriptor["resolution"] == 55.0
    assert descriptor["resolution_basis"] == "median_shortest_furniture_side"
    assert "east_armchair_left" in descriptor["resolution_evidence"]
    assert "center_sofa_upper" in descriptor["resolution_evidence"]
    assert descriptor["resolution_sensitivity"] == {
        "tested_resolutions": [27.5, 55.0, 110.0],
        "entry_reachable_cell_ratio_range": 0.1329,
        "entry_reachable_region_ratio_range": 0.0,
        "path_reachable_region_ratio_range": 0.0,
    }
    assert descriptor["total_cells"] == 361
    assert descriptor["domain_cells"] == 294
    assert descriptor["outside_domain_cells"] == 67
    assert descriptor["blocked_cells"] == 32
    assert descriptor["component_count"] == 1
    assert descriptor["component_sizes"] == [262]
    assert descriptor["largest_component_cell_ratio"] == 1.0
    assert descriptor["entry_reachable_component_ratio"] == 1.0
    assert descriptor["walkable_cell_ratio"] == 0.8912
    assert descriptor["entry_reachable_cell_ratio"] == 0.8912
    assert descriptor["entry_reachable_region_ratio"] == 1.0
    assert descriptor["sampled_entry_reachable_region_pair_ratio"] == 1.0
    assert len(descriptor["sampled_entry_reachable_region_pair_evidence"]) == 21
    assert descriptor["sampled_unreachable_region_pair_evidence"] == []
    assert descriptor["visibility_reachable_region_ratio"] == 1.0
    assert descriptor["sampled_visibility_reachable_region_pair_ratio"] == 1.0
    assert len(descriptor["sampled_visibility_reachable_region_pair_evidence"]) == 21
    assert descriptor["sampled_visibility_unreachable_region_pair_evidence"] == []
    assert descriptor["sampled_visibility_only_region_pair_ratio"] == 0.0
    assert descriptor["sampled_walk_only_region_pair_ratio"] == 0.0
    assert descriptor["sampled_walk_visibility_disagreement_region_pair_ratio"] == 0.0
    assert descriptor["visibility_only_region_ratio"] == 0.0
    assert descriptor["walk_only_region_ratio"] == 0.0
    assert descriptor["walk_visibility_disagreement_region_ratio"] == 0.0
    assert descriptor["mean_visibility_region_grid_steps"] == 2.2857
    assert descriptor["mean_visibility_region_grid_distance"] == 125.7143
    assert descriptor["mean_entry_region_grid_steps"] == 2.2857
    assert descriptor["mean_entry_region_grid_distance"] == 125.7143
    assert len(descriptor["region_pair_grid_distances"]) == 21
    assert descriptor["mean_region_pair_grid_steps"] == 5.2381
    assert descriptor["mean_region_pair_grid_distance"] == 288.0952
    assert {
        item["region_id"]: item["distance"]
        for item in descriptor["entry_region_grid_distances"]
    } == {
        "region_north_tables": 55.0,
        "region_west_lounge": 110.0,
        "region_center_lounge": 0.0,
        "region_east_work": 0.0,
        "region_east_armchairs": 0.0,
        "region_north_wall": 385.0,
        "region_slanted_test": 330.0,
    }
    assert descriptor["path_reachable_region_ratio"] == 0.7143
    assert descriptor["method"] == "sampled_occupancy_grid_bfs_proxy"
    assert "not CAD boolean negative space" in descriptor["uncertainty"]
    negative_space = matrix["negative_space"]
    assert negative_space["negative_space_area_ratio_proxy"] == 0.8493
    assert negative_space["room_area"] == 806275.0
    assert negative_space["blocker_overlap_area"] == 121539.0
    assert negative_space["summed_blocker_overlap_area"] == 123387.0
    assert len(negative_space["room_minus_blocker_polygons"]) == 1
    assert len(negative_space["room_minus_blocker_polygons"][0]["holes"]) == 20
    assert negative_space["room_minus_blocker_polygons"][0]["area"] == 684736.0
    assert len(negative_space["cad_room_minus_blocker_polygons"]) == 1
    assert len(negative_space["cad_room_minus_blocker_polygons"][0]["holes"]) == 20
    assert negative_space["cad_room_minus_blocker_polygons"][0]["area"] == 684736.0
    assert negative_space["cad_room_minus_blocker_area_total"] == 684736.0
    assert negative_space["cad_room_minus_blocker_area_residual"] == 0.0
    assert negative_space["cad_room_minus_blocker_area_residual_ratio"] == 0.0
    assert negative_space["cad_room_minus_blocker_component_touch_evidence"][0][
        "region_ids"
    ] == [
        "region_center_lounge",
        "region_east_armchairs",
        "region_east_work",
        "region_north_tables",
        "region_north_wall",
        "region_slanted_test",
        "region_west_lounge",
    ]
    assert "north_table_r1_c1" in negative_space["blocker_evidence"]
    assert negative_space["component_count"] >= 1
    assert 0.0 < negative_space["largest_component_area_ratio"] <= 1.0
    assert negative_space["entry_connected_component_count"] == 1
    assert negative_space["entry_connected_area_ratio"] == 1.0
    assert negative_space["entry_component_evidence"][0]["entry_ids"] == [
        "bottom_entry",
        "left_entry",
        "right_entry_arc",
        "right_entry_line",
    ]
    isovist = matrix["isovist_radial_proxy"]
    assert isovist["metrics"]["mean_hit_polygon_area"] == 415076.4205
    assert len(isovist["isovist_area_evidence"]) == 11

    path_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "path_connectivity"
    }
    assert path_rows["sampled_grid_resolution"]["evidence"] == descriptor["resolution_evidence"]
    assert path_rows["sampled_resolution_sensitivity"]["score"] == 0.1329
    assert (
        path_rows["sampled_resolution_sensitivity"]["evidence"]
        == descriptor["resolution_sensitivity"]
    )
    assert path_rows["sampled_walkable_cell_ratio"]["score"] == descriptor["walkable_cell_ratio"]
    assert path_rows["sampled_negative_space_area_ratio_delta"] == {
        "view_id": "path_connectivity",
        "metric": "sampled_negative_space_area_ratio_delta",
        "score": 0.0419,
        "status": "computed",
        "method": "absolute_sampled_walkable_minus_negative_space_area_ratio",
        "evidence": {
            "sampled_walkable_cell_ratio": 0.8912,
            "negative_space_area_ratio_proxy": 0.8493,
        },
        "uncertainty": "absolute difference between sampled occupancy and rect-cell negative-space area proxies; flags proxy disagreement, not geometric truth",
    }
    assert path_rows["sampled_entry_reachable_cell_ratio"]["score"] == descriptor["entry_reachable_cell_ratio"]
    assert path_rows["sampled_entry_reachable_region_ratio"]["score"] == descriptor["entry_reachable_region_ratio"]
    assert (
        path_rows["sampled_entry_reachable_region_pair_ratio"]["score"]
        == descriptor["sampled_entry_reachable_region_pair_ratio"]
    )
    assert (
        len(
            path_rows["sampled_entry_reachable_region_pair_ratio"][
                "region_pair_evidence"
            ]
        )
        == 21
    )
    assert path_rows["sampled_visibility_reachable_region_ratio"]["score"] == 1.0
    assert path_rows["sampled_visibility_reachable_region_pair_ratio"]["score"] == 1.0
    assert (
        len(
            path_rows["sampled_visibility_reachable_region_pair_ratio"][
                "region_pair_evidence"
            ]
        )
        == 21
    )
    assert path_rows["sampled_visibility_only_region_pair_ratio"]["score"] == 0.0
    assert path_rows["sampled_walk_only_region_pair_ratio"]["score"] == 0.0
    assert (
        path_rows["sampled_walk_visibility_disagreement_region_pair_ratio"]["score"]
        == 0.0
    )
    assert path_rows["sampled_visibility_only_region_ratio"]["score"] == 0.0
    assert path_rows["sampled_walk_only_region_ratio"]["score"] == 0.0
    assert path_rows["sampled_walk_visibility_disagreement_region_ratio"]["score"] == 0.0
    assert path_rows["sampled_mean_visibility_region_grid_distance"]["score"] == 125.7143
    assert path_rows["sampled_mean_entry_region_grid_distance"]["score"] == 125.7143
    assert path_rows["sampled_mean_entry_region_widest_clearance"]["score"] == 46.3776
    assert (
        path_rows["sampled_mean_entry_region_widest_clearance"]["method"]
        == "sampled_grid_widest_path_clearance_proxy"
    )
    assert len(path_rows["sampled_mean_entry_region_widest_clearance"]["evidence"]) == 7
    assert path_rows["sampled_mean_entry_region_clearance_per_distance"]["score"] == 0.5859
    assert (
        path_rows["sampled_mean_entry_region_clearance_per_distance"]["method"]
        == "sampled_widest_clearance_over_entry_region_distance_proxy"
    )
    assert path_rows["sampled_mean_region_pair_grid_distance"]["score"] == 288.0952
    assert path_rows["sampled_region_pair_reachable_ratio"]["score"] == 1.0
    assert path_rows["sampled_component_count"]["score"] == 1
    assert path_rows["sampled_largest_component_cell_ratio"]["score"] == 1.0
    assert path_rows["sampled_path_reachable_region_ratio"]["score"] == descriptor["path_reachable_region_ratio"]
    assert (
        path_rows["negative_space_area_ratio_proxy"]["score"]
        == negative_space["negative_space_area_ratio_proxy"]
    )
    assert (
        path_rows["negative_space_area_ratio_proxy"]["method"]
        == "room_polygon_minus_blocker_union_area_proxy"
    )
    assert path_rows["negative_space_room_minus_blocker_polygon_count"]["score"] == 1
    assert (
        path_rows["negative_space_room_minus_blocker_polygon_count"]["method"]
        == "rect_cell_room_minus_blocker_boundary_union_proxy"
    )
    assert path_rows["cad_room_minus_blocker_polygon_count"]["score"] == 1
    assert (
        path_rows["cad_room_minus_blocker_polygon_count"]["method"]
        == "shapely_room_polygon_difference_blocker_union"
    )
    assert path_rows["cad_room_minus_blocker_area_residual_ratio"]["score"] == 0.0
    assert (
        path_rows["cad_room_minus_blocker_area_residual_ratio"]["method"]
        == "shapely_room_minus_blocker_area_minus_negative_space_area"
    )
    assert (
        path_rows["cad_room_minus_blocker_largest_component_area_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["cad_room_minus_blocker_entry_connected_region_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["cad_room_minus_blocker_entry_connected_area_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["cad_room_minus_blocker_entry_connected_component_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["cad_room_minus_blocker_entry_connected_region_pair_ratio"]["score"]
        == 1.0
    )
    assert (
        path_rows["cad_room_minus_blocker_entry_connected_region_pair_ratio"][
            "entry_connected_region_pair_count"
        ]
        == 21
    )
    assert (
        len(
            path_rows["cad_room_minus_blocker_entry_connected_region_pair_ratio"][
                "region_pair_evidence"
            ]
        )
        == 21
    )
    assert path_rows["cad_room_minus_blocker_component_graph_edge_count"] == {
        "view_id": "path_connectivity",
        "metric": "cad_room_minus_blocker_component_graph_edge_count",
        "score": 11,
        "status": "computed",
        "method": "shapely_component_entry_region_touch_graph_proxy",
        "evidence": {
            "node_count": 12,
            "edge_count": 11,
            "component_node_count": 1,
            "entry_node_count": 4,
            "region_node_count": 7,
        },
        "uncertainty": "graph-shaped Shapely component/entry/region touch evidence for adapter handoff; not navmesh, skeleton, hosted topology, or route graph",
    }
    assert "region_room_misc" not in path_rows[
        "cad_room_minus_blocker_entry_connected_region_ratio"
    ]["entry_connected_region_ids"]
    assert (
        path_rows["negative_space_component_count"]["score"]
        == negative_space["component_count"]
    )
    assert (
        path_rows["negative_space_component_cell_area_residual_ratio"]["score"]
        == matrix["negative_space_graph"]["metrics"][
            "max_component_cell_area_residual_ratio"
        ]
    )
    assert (
        path_rows["negative_space_component_cell_area_residual_ratio"][
            "component_cell_area_sums"
        ]
        == matrix["negative_space_graph"]["metrics"]["component_cell_area_sums"]
    )
    assert (
        path_rows["negative_space_largest_component_area_ratio"]["score"]
        == negative_space["largest_component_area_ratio"]
    )
    assert (
        path_rows["negative_space_entry_connected_component_count"]["score"]
        == negative_space["entry_connected_component_count"]
    )
    assert (
        path_rows["negative_space_entry_connected_area_ratio"]["score"]
        == negative_space["entry_connected_area_ratio"]
    )
    assert path_rows["negative_space_entry_connected_region_ratio"]["score"] == 1.0
    assert path_rows["negative_space_entry_connected_region_ratio"][
        "entry_connected_region_ids"
    ] == [
        "region_center_lounge",
        "region_east_armchairs",
        "region_east_work",
        "region_north_tables",
        "region_north_wall",
        "region_slanted_test",
        "region_west_lounge",
    ]
    assert path_rows["negative_space_entry_connected_region_ratio"][
        "non_entry_connected_region_ids"
    ] == []
    assert all(
        edge_id.startswith("edge_negative_space_component_region_component_0_")
        for edge_id in path_rows["negative_space_entry_connected_region_ratio"]["evidence"]
    )
    assert path_rows["negative_space_entry_connected_region_pair_ratio"]["score"] == 1.0
    assert len(path_rows["negative_space_entry_connected_region_pair_ratio"]["region_pair_evidence"]) == 21
    assert path_rows["candidate_path_region_pair_ratio_proxy"]["score"] == 0.6204
    assert path_rows["candidate_path_region_pair_ratio_proxy"]["candidate_path_pair_inputs"] == {
        "candidate_path_area_ratio_proxy": 0.6204,
        "negative_space_entry_connected_region_pair_ratio": 1.0,
        "entry_connected_region_pair_count": 21,
        "total_region_pair_count": 21,
    }
    assert (
        path_rows["negative_space_entry_connected_region_area_coverage_ratio"]["score"]
        == 0.6996
    )
    assert (
        len(
            path_rows["negative_space_entry_connected_region_area_coverage_ratio"][
                "region_area_coverage_evidence"
            ]
        )
        == 7
    )
    assert (
        path_rows["isovist_radial_hit_polygon_area_mean"]["score"]
        == isovist["metrics"]["mean_hit_polygon_area"]
    )
    assert (
        path_rows["isovist_radial_hit_polygon_area_mean"]["method"]
        == "radial_isovist_hit_point_polygon_area_proxy"
    )
    assert len(
        path_rows["isovist_radial_hit_polygon_area_mean"]["isovist_area_evidence"]
    ) == 11
    assert path_rows["sampled_entry_reachable_cell_ratio"]["method"] == "sampled_occupancy_grid_bfs_proxy"
    assert (
        path_rows["sampled_visibility_reachable_region_ratio"]["method"]
        == "sampled_visibility_grid_bfs_proxy"
    )
    assert (
        path_rows["sampled_mean_visibility_region_grid_distance"]["method"]
        == "sampled_visibility_grid_bfs_distance_proxy"
    )
    assert (
        path_rows["sampled_mean_entry_region_grid_distance"]["method"]
        == "sampled_occupancy_grid_bfs_distance_proxy"
    )
    assert path_rows["sampled_component_count"]["method"] == "sampled_occupancy_grid_component_proxy"
    assert "proxy" in path_rows["sampled_path_reachable_region_ratio"]["uncertainty"]


def test_scene_metric_overlay_svg_contains_source_ids_and_metric_layers():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert "<svg" in svg
    assert "north_table_r1_c1" in svg
    assert "west_lounge" in svg
    assert 'data-layer="metric-evidence"' in svg
    assert 'data-layer="path-graph-node"' in svg
    assert 'data-layer="path-graph-edge"' in svg
    assert 'data-layer="negative-space-graph-node"' in svg
    assert 'data-layer="negative-space-graph-edge"' in svg
    assert 'data-layer="negative-space-component"' in svg
    assert 'data-layer="free-space-graph-entry-anchor"' in svg
    assert 'data-layer="free-space-graph-region-anchor"' in svg
    assert 'data-entry="left_entry"' in svg
    assert 'data-region="region_north_tables"' in svg
    assert 'data-component="0"' in svg
    assert 'data-layer="free-space-graph-entry-region-path"' not in svg
    assert 'data-from-cell="component_0_cell_' not in svg
    assert 'data-to-cell="component_0_cell_' not in svg
    assert 'data-cell-count="' in svg
    assert 'data-bbox-left="' in svg
    assert 'data-layer="line-of-sight-blocker-hit"' in svg
    assert 'data-boundary="glass_boundary"' in svg
    assert 'data-x="690.0000"' in svg
    assert 'data-distance-ratio="0.6240"' in svg
    assert 'data-layer="line-of-sight-centerline"' in svg
    assert 'data-from="region_north_tables"' in svg
    assert 'data-to="region_east_armchairs"' in svg
    assert 'data-visible="false"' in svg
    assert 'data-blocker-count="1"' in svg
    assert 'x1="495.0" y1="355.0" x2="807.5" y2="875.0"' in svg
    assert "edge_negative_space_component_region_component_0_region_north_tables" in svg
    assert 'data-overlap-area="337125.0"' in svg
    assert 'data-layer="column-axis"' in svg
    # The evaluated column-grid evidence has explicit axes but no paired axis
    # lists, so the overlay must not draw legacy synthetic bay placeholders.
    assert matrix["column_grid"]["bays"] == []
    assert 'data-layer="column-bay"' not in svg
    assert 'data-layer="region-axis"' in svg
    assert 'data-region="region_slanted_test"' in svg
    assert 'data-basis="polygon_pca_axis"' in svg
    assert 'data-angle="26.5651"' in svg
    assert 'data-layer="boundary-axis"' in svg
    assert 'data-boundary="glass_boundary"' in svg
    assert 'data-kind="glass"' in svg
    assert 'data-walk-block="1.0000"' in svg
    assert 'data-see-block="0.1500"' in svg
    assert 'data-boundary="rug_boundary"' in svg
    assert 'data-kind="rug"' in svg
    assert 'data-grouping-strength="0.8500"' in svg
    assert 'data-layer="region-boundary-cue"' in svg
    assert 'data-region="region_center_lounge"' in svg
    assert 'data-boundary="glass_boundary"' in svg
    assert 'data-gap="5.0000"' in svg
    assert 'data-proximity="0.9833"' in svg
    assert 'data-layer="object-region-membership"' in svg
    assert 'data-object="north_table_r1_c1"' in svg
    assert 'data-region="region_north_tables"' in svg
    assert 'data-score="1.0000"' in svg
    assert 'data-region="region_room_misc"' in svg
    assert 'data-object="center_misc_fixture"' in svg
    assert 'data-layer="region-axis" data-region="region_room_misc"' not in svg
    assert 'data-layer="path-blocker-conflict"' in svg
    assert 'data-overlap-area="6820.0"' in svg
    assert 'data-blocker="east_work_table"' in svg
    assert "edge_entry_path_touch_bottom_entry_path_placeholder" in svg
    assert "center_misc_fixture" in svg


def test_overlay_draws_column_grid_relation_layers():
    """Overlay should draw relation evidence from the evaluated column grid."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            {
                "id": "seating",
                "region": "seating",
                "role": "region",
                "rect": Rect(cx=40, cy=40, width=40, height=40),
                "metadata": {},
            }
        ],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"branch-id": "with_bays", "axis-list": "y"},
            },
        ],
    }

    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="column-axis"' in svg
    assert 'data-layer="column-bay"' in svg
    assert 'data-layer="column-seed-bay"' in svg
    assert 'data-layer="column-global-frame"' in svg
    assert 'data-layer="column-local-profile"' in svg


def test_overlay_draws_physical_columns_from_svg_proxy():
    """SVG piler records should remain visible as physical column evidence."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="column-physical"' in svg
    assert 'data-column="piler1"' in svg


def test_overlay_does_not_draw_legacy_column_bays_when_matrix_bays_are_empty():
    """Explicit empty evaluated bays should suppress legacy axis-derived bays."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=0, width=100, height=0),
                "points": [(0, 0), (100, 0)],
                "metadata": {},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=50, cy=100, width=100, height=0),
                "points": [(0, 100), (100, 100)],
                "metadata": {},
            },
        ],
    }
    matrix = {"rows": [], "column_grid": {"status": "computed", "bays": []}}

    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="column-axis"' in svg
    assert 'data-layer="column-bay"' not in svg


def test_scene_metric_overlay_svg_can_include_dense_free_space_paths():
    from features.affordance.models import Rect

    scene = {
        "source": "synthetic_overlay",
        "size": (100.0, 100.0),
        "objects": [
            {
                "id": "table",
                "role": "table",
                "group": "global",
                "region": "room",
                "rect": Rect(cx=10, cy=10, width=10, height=10),
                "points": [],
                "weights": {},
                "metadata": {},
                "adapter_refs": {},
            }
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "column_axes": [],
        "uncertainties": [],
    }
    matrix = {
        "rows": [],
        "graph": {"nodes": [], "edges": []},
        "negative_space_graph": {"nodes": [], "edges": []},
        "negative_space": {
            "free_space_polygon_graph": {
                "nodes": [
                    {"id": "component_0_cell_a", "point": (0.0, 0.0)},
                    {"id": "component_0_cell_b", "point": (10.0, 0.0)},
                ],
                "entry_region_distance_evidence": [
                    {
                        "entry_id": "entry",
                        "region_id": "region",
                        "component_index": 0,
                        "path_cell_ids": [
                            "component_0_cell_a",
                            "component_0_cell_b",
                        ],
                    }
                ],
                "anchors": {"entries": [], "regions": []},
            }
        },
    }
    svg = scene_metric_overlay_svg(scene, matrix, include_free_space_paths=True)

    assert 'data-layer="free-space-graph-entry-region-path"' in svg
    assert 'data-from-cell="component_0_cell_' in svg
    assert 'data-to-cell="component_0_cell_' in svg


import nbformat


def test_floorplan_notebook_uses_automatic_scene_loader():
    nb = nbformat.read("test/floorplan_order_matrix_demo.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in nb.cells)

    assert "load_structured_svg_scene" in source
    assert "evaluate_scene" in source
    assert "scene_metric_overlay_svg" in source
    assert "line_of_sight_entry_region_ratio" in source
    assert "isovist_radial_proxy" in source
    assert "isovist_radial_blocked_ray_ratio" in source
    assert "isovist_radial_hit_polygon_area_mean" in source
    assert "mean_hit_polygon_area" in source
    assert "isovist_area_evidence" in source
    assert "negative_space_graph_metrics" in source
    assert "entry_connected_component_area" in source
    assert "non_entry_connected_area_ratio" in source
    assert "entry_connected_region_pair_evidence" in source
    assert "unconnected_region_pair_evidence" in source
    assert "component_cell_counts" in source
    assert "component_cell_area_sums" in source
    assert "component_area_total" in source
    assert "component_cell_area_sum_total" in source
    assert "negative_space_free_polygon_count" in source
    assert "negative_space_room_minus_blocker_polygon_count" in source
    assert "cad_room_minus_blocker_polygon_count" in source
    assert "cad_room_minus_blocker_largest_component_area_ratio" in source
    assert "cad_room_minus_blocker_area_residual_ratio" in source
    assert "cad_room_minus_blocker_entry_connected_region_ratio" in source
    assert "cad_room_minus_blocker_entry_connected_area_ratio" in source
    assert "cad_room_minus_blocker_entry_connected_component_ratio" in source
    assert "cad_room_minus_blocker_entry_connected_region_pair_ratio" in source
    assert "cad_room_minus_blocker_component_graph_edge_count" in source
    assert "cad_room_minus_blocker_component_touch_evidence" in source
    assert "cad_room_minus_blocker_entry_connected_area" in source
    assert "cad_room_minus_blocker_component_graph" in source
    assert "room_minus_blocker_polygon_count" in source
    assert "cad_room_minus_blocker_polygon_count" in source
    assert "room_minus_blocker_polygons" in source
    assert "cad_room_minus_blocker_polygons" in source
    assert "negative_space_free_polygon_adjacency_count" in source
    assert "free_space_polygon_graph_node_count" in source
    assert "free_space_polygon_graph_edge_count" in source
    assert "free_space_polygon_graph_cycle_rank" in source
    assert "free_space_polygon_graph_mean_entry_region_distance" in source
    assert "free_space_polygon_graph_mean_edge_clearance_width" in source
    assert "free_space_polygon_graph_mean_entry_region_min_clearance_width" in source
    assert "free_space_polygon_graph_mean_entry_region_widest_clearance_width" in source
    assert "free_space_polygon_graph_entry_region_distance_count" in source
    assert "free-space-graph-entry-region-path" in source
    assert "free-space-graph-entry-anchor" in source
    assert "free-space-graph-region-anchor" in source
    assert "free_space_polygon_count" in source
    assert "free_space_polygon_adjacency_count" in source
    assert "negative_space_mean_entry_region_free_polygon_distance" in source
    assert "negative_space_mean_entry_region_free_polygon_path_length" in source
    assert "entry_region_free_polygon_distance_evidence" in source
    assert "negative_space_component_area_residual" in source
    assert "negative_space_component_area_residual_ratio" in source
    assert "max_component_cell_area_residual_ratio" in source
    assert "negative_space_component_cell_area_residual_ratio" in source
    assert "fallback_entry_boundary_ratio" in source
    assert "boundary_weight_metadata_coverage" in source
    assert "object_column_bay_local_position_coverage" in source
    assert "path_disconnected_opening_ids" in source
    assert "adapter_payload" in source
    assert "evidence_geometry" in source
    assert "scene_records" in source
    assert "external_refs" in source
    assert "adapter_reference_coverage" in source
    assert "adapter_reference_role_coverage" in source
    assert "Manual object declarations" not in source
    assert "objects = [" not in source


def test_floorplan_notebook_keeps_display_order_and_dense_paths_optional():
    nb = nbformat.read("test/floorplan_order_matrix_demo.ipynb", as_version=4)
    headings = [
        cell.source.strip()
        for cell in nb.cells
        if cell.cell_type == "markdown" and cell.source.strip().startswith("## ")
    ]
    code_sources = [
        cell.source
        for cell in nb.cells
        if cell.cell_type == "code"
    ]
    overlay_cells = [
        cell
        for cell in nb.cells
        if cell.cell_type == "code"
        and "display(SVG(data=scene_metric_overlay_svg(scene, matrix)))" in cell.source
    ]

    assert headings == [
        "## 1. Source Fixture",
        "## 2. Evaluation Summary",
        "## 3. Metric Matrix",
        "## 4. Clean Evidence Overlay",
        "## 5. Audit Snapshot",
    ]
    assert "display(SVG(data=scene_metric_overlay_svg(scene, matrix)))" in code_sources[3]
    assert "include_free_space_paths=True" not in "\n".join(code_sources)
    assert len(overlay_cells) == 1

    overlay_output = "".join(
        "".join(data)
        for output in overlay_cells[0].outputs
        for data in output.get("data", {}).get("image/svg+xml", [])
    )
    assert "free-space-graph-entry-region-path" not in overlay_output


def test_svg_id_inference_notebook_presents_three_auto_inference_fixtures():
    """The ID-only SVG inference notebook should focus on the three probe SVGs."""
    nb = nbformat.read("test/svg_id_inference_demo.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in nb.cells)
    headings = [
        cell.source.strip()
        for cell in nb.cells
        if cell.cell_type == "markdown" and cell.source.strip().startswith("## ")
    ]

    assert headings == [
        "## 1. Probe SVGs",
        "## 2. Automatic Inference Summary",
        "## 3. Inference Overlays",
    ]
    assert 'glob("SVG*.svg")' in source
    assert "infer_scene_evidence" in source
    assert "_inference_overlay_html" in source
    assert "region-trend" in source
    assert "region-trend-primary" in source
    assert "region-trend-secondary" in source
    assert "region-polygon" in source
    assert "region-shape-basis" in source
    assert "data-shape-basis" in source
    assert "data-frame-delta" in source
    assert "axis-visual-length-basis" in source
    assert "extent * max(0.15, strength)" not in source
    assert "extent * 0.65 * strength" in source
    assert "extent_times_0.65_times_strength" in source
    assert "axis-strength" in source
    assert "manual_regions" in source
    assert "manual_paths" in source
    assert "evaluate_scene(" not in source


def test_docs_do_not_describe_current_notebook_as_manual_object_table():
    spec = Path("docs/indoor_layout_evaluation_matrix_spec.md").read_text(
        encoding="utf-8"
    )
    audit = Path(
        "docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md"
    ).read_text(encoding="utf-8")

    stale_claims = [
        "still declares objects manually",
        "manual fixture notebook",
        "automatic SVG-to-matrix remains open until implemented",
    ]
    for claim in stale_claims:
        assert claim not in spec
        assert claim not in audit


def test_audit_records_automatic_svg_path_as_implemented_after_work():
    audit = Path(
        "docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md"
    ).read_text(encoding="utf-8")
    status = Path("docs/indoor_layout_evaluation_matrix_task_status.md").read_text(
        encoding="utf-8"
    )

    assert "Automatic structured 2D plan to evaluation matrix" in audit
    assert "Prototype expanded" in audit
    assert "Full evaluation matrix implementation" in audit
    assert "load_structured_svg_scene" in status
    assert "evaluate_scene(scene)" in status
    assert "export_adapter_payload_json" in status
    assert "computed region-axis-to-column-axis similarity score" in status
    assert "explicit path graph evidence proxy" in status
    assert "path polygon-to-blocker clearance proxy" in status
    assert "path blocker overlap ratio" in status
    assert "path blocker overlap area ratio" in status
    assert "path_polygon_blocker_union_overlap_area" in status
    assert "sampled walkable-space proxy" in status
    assert "sampled_occupancy_grid_bfs_proxy" in status
    assert "sampled_negative_space_area_ratio_delta" in status
    assert "negative_space_polygon_overlap_risk_count" in status
    assert "path_touched_region_boundary_cue_strength_mean" in status
    assert "path_touched_region_boundary_cue_perimeter_influence_mean" in status
    assert "path_touched_region_boundary_cue_count_mean" in status
    assert "boundary_cue_kinds" in status
    assert "path_touched_region_boundary_grouping_strength_mean" in status
    assert "path_touched_region_boundary_walk_see_gap_mean" in status
    assert "boundary_cue_profiles" in status
    assert "path_region_split_tendency_proxy" in status
    assert "disconnected_entry_ratio" in status
    assert "disconnected_path_ratio" in status
    assert "closed_blocking_boundary_ratio" in status
    assert "hosted_entry_boundary_ratio" in status
    assert "fallback_entry_boundary_ratio" in status
    assert "host_relationships" in status
    assert "route_topology_handoff" in status
    assert "route_topology_handoff.inferred_gap_paths" in status
    assert "route_topology_handoff.cad_component_graph.items" in status
    assert "route_topology_handoff.free_space_polygon_graph.items" in status
    assert "visual_analysis_handoff" in status
    assert "visual_analysis_handoff.visibility_graph.items" in status
    assert "visual_analysis_handoff.isovist_radial_proxy.ray_items" in status
    assert "visual_analysis_handoff.isovist_radial_proxy.area_items" in status
    assert "material_calibration_handoff" in status
    assert "column_grid_handoff" in status
    assert "adapter_capability_matrix" in status
    assert "matrix_completion_audit" in status
    assert "completion_gate_from_current_metric_family_status" in status
    assert "notebook_audit_manifest" in status
    assert "boundary_weight_metadata_coverage" in status
    assert "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records" in status
    assert "path_disconnected_opening_ids" in status
    assert "adapter_refs" in status
    assert "neutral adapter payload" in status
    assert "adapter_payload" in status
    assert "score_matrix" in status
    assert "computed_unit_interval_metric_mean_by_view_id" in status
    assert "evidence_geometry" in status
    assert "adapter_payload.evidence_geometry.affordance_zones" in status
    assert "adapter_payload.evidence_geometry.furniture_affordance_extents" in status
    assert "adapter_payload.evidence_geometry.inferred_region_candidates" in status
    assert "adapter_payload.evidence_geometry.inferred_region_gap_paths" in status
    assert "adapter_payload.evidence_geometry.inferred_region_gap_path_occupancy" in status
    assert "adapter_payload.evidence_geometry.inferred_region_gap_path_free_space_overlap" in status
    assert "inferred_region_gap_path_cad_free_space_overlap_ratio" in status
    assert "inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons" in status
    assert "cad_free_space_supported_edge_count" in status
    assert "cad_free_space_supported_edges" in status
    assert "adapter_payload.evidence_geometry.inferred_region_gap_path_cad_free_space_overlap" in status
    assert "free_space_polygon_graph" in status
    assert "free_space_polygon_graph_cycle_rank" in status
    assert "free_space_polygon_graph_mean_entry_region_distance" in status
    assert "free_space_polygon_graph_mean_edge_clearance_width" in status
    assert "free_space_polygon_graph_mean_entry_region_min_clearance_width" in status
    assert "free_space_polygon_graph_mean_entry_region_widest_clearance_width" in status
    assert "inferred_gap_path_width_free_space_clearance_ratio" in status
    assert "free_space_edge_clearance_width_over_inferred_gap_band_width" in status
    assert "free-space-graph-entry-region-path" in status
    assert "adapter_reference_coverage" in status
    assert "adapter_reference_role_coverage" in status
    assert "negative_space_area_ratio_proxy" in status
    assert "room_polygon_minus_blocker_union_area_proxy" in status
    assert "summed_blocker_overlap_area" in status
    assert "separate-polygon-blocker regression" in status
    assert "duplicate-polygon-blocker regression" in status
    assert "negative_space_component_count" in status
    assert "negative_space_room_minus_blocker_polygon_count" in status
    assert "cad_room_minus_blocker_polygon_count" in status
    assert "cad_room_minus_blocker_largest_component_area_ratio" in status
    assert "shapely_largest_component_area_over_total_free_area" in status
    assert "cad_room_minus_blocker_area_residual_ratio" in status
    assert "cad_room_minus_blocker_entry_connected_region_ratio" in status
    assert "cad_room_minus_blocker_entry_connected_area_ratio" in status
    assert "shapely_component_entry_touched_area_ratio_proxy" in status
    assert "cad_room_minus_blocker_entry_connected_component_ratio" in status
    assert "shapely_component_entry_touched_component_count_proxy" in status
    assert "cad_room_minus_blocker_entry_connected_region_pair_ratio" in status
    assert "shapely_component_entry_connected_region_pair_proxy" in status
    assert "cad_room_minus_blocker_component_graph_edge_count" in status
    assert "shapely_component_entry_region_touch_proxy" in status
    assert "cad_room_minus_blocker_component_touch_evidence" in status
    assert "cad_room_minus_blocker_entry_connected_area" in status
    assert "cad_room_minus_blocker_component_graph" in status
    assert "shapely_component_entry_region_touch_graph_proxy" in status
    assert "rect_cell_room_minus_blocker_boundary_union_proxy" in status
    assert "shapely_room_polygon_difference_blocker_union" in status
    assert "shapely_room_minus_blocker_area_minus_negative_space_area" in status
    assert "room_minus_blocker_polygons" in status
    assert "cad_room_minus_blocker_polygons" in status
    assert "component_rects" in status
    assert "cell_count" in status
    assert "cell_rects" in status
    assert "component_cell_area_sums" in status
    assert "component_area_total" in status
    assert "component_cell_area_sum_total" in status
    assert "negative_space_component_area_residual" in status
    assert "negative_space_component_area_residual_ratio" in status
    assert "max_component_cell_area_residual_ratio" in status
    assert "negative_space_component_cell_area_residual_ratio" in status
    assert "room_polygon_rect_cell_decomposition_proxy" in status
    assert "polygon blocker" in status
    assert "negative_space_entry_connected_component_ratio" in status
    assert "entry_connected_component_ids" in status
    assert "non_entry_connected_component_ids" in status
    assert "entry_connected_component_ratio" in status
    assert "component_area" in status
    assert "entry_connected_component_area" in status
    assert "non_entry_connected_component_area" in status
    assert "entry_connected_area_ratio" in status
    assert "non_entry_connected_area_ratio" in status
    assert "negative_space_entry_connected_area_ratio" in status
    assert "negative_space_graph" in status
    assert "negative_space_entry_connected_region_ratio" in status
    assert "entry_connected_region_ids" in status
    assert "non_entry_connected_region_ids" in status
    assert "entry_connected_region_ratio" in status
    assert "negative_space_entry_connected_region_pair_ratio" in status
    assert "entry_connected_region_pair_count" in status
    assert "total_region_pair_count" in status
    assert "entry_connected_region_pair_ratio" in status
    assert "entry_connected_region_pair_evidence" in status
    assert "unconnected_region_pair_evidence" in status
    assert "candidate_path_region_pair_ratio_proxy" in status
    assert "sampled_entry_reachable_region_pair_ratio" in status
    assert "sampled_visibility_reachable_region_pair_ratio" in status
    assert "sampled_walk_visibility_disagreement_region_pair_ratio" in status
    assert "sampled_mean_region_pair_grid_distance" in status
    assert "sampled_resolution_sensitivity" in status
    assert "uncertainty_routes" in status
    assert "line_of_sight_region_pair_ratio" in status
    assert "line_of_sight_graph" in status
    assert "isovist_radial_proxy" in status
    assert "isovist_radial_blocked_ray_ratio" in status
    assert "radial_isovist_see_block_ray_intersection_proxy" in status
    assert "isovist_radial_hit_polygon_area_mean" in status
    assert "radial_isovist_hit_point_polygon_area_proxy" in status
    assert "mean_hit_polygon_area" in status
    assert "line_of_sight_graph_visible_edge_ratio" in status
    assert "line_of_sight_graph_blocked_edge_ratio" in status
    assert "line_of_sight_graph_blocking_boundary_count" in status
    assert "line_of_sight_graph_unique_blocking_boundary_count" in status
    assert "blocking_boundary_edge_evidence" in status
    assert "region_pair_centerline_visibility" in status
    assert "visible_edge_ratio" in status
    assert "blocked_edge_ids" in status
    assert "blocking_boundary_evidence" in status
    assert "intersection_points" in status
    assert "intersection_distances_from_start" in status
    assert "intersection_distance_ratios" in status
    assert "line-of-sight blocker overlay evidence pass" in status
    assert "line-of-sight centerline overlay evidence pass" in status
    assert "data-distance-ratio" in status
    assert "data-blocker-count" in status
    assert "dead_end_nodes" in status
    assert "cycle_rank_inputs" in status
    assert "graph_component_count" in status
    assert "reached_region_ids" in status
    assert "unreached_region_ids" in status
    assert "negative_space_entry_connected_region_area_coverage_ratio" in status
    assert "object_column_axis_phase_alignment" in status
    assert "region_centroid_phase_alignment" in status
    assert "region_centroid_trend_alignment" in status
    assert "region_centroid_pca_axis_cross_deviation_score" in status
    assert "affordance_use_zone_count" in status
    assert "object_footprint_adjacent_affordance_rect_zones" in status
    assert "furniture_affordance_extent_count" in status
    assert "object_footprint_plus_own_affordance_zone_extent" in status
    assert "furniture-affordance-extent" in status
    assert "geometry_basis=object_footprints_plus_affordance_zone_rects" in status
    assert "affordance_zone_ids" in status
    assert "affordance-use-zone" in status
    assert "inferred_region_candidate_count" in status
    assert "affordance_zone_boundary_cue_expanded_group_candidate_bounds" in status
    assert "inferred_region_count" in status
    assert "affordance_expanded_group_bounds" in status
    assert "inferred_region_explicit_iou_mean" in status
    assert "affordance_expanded_candidate_region_to_explicit_region_iou" in status
    assert "inferred_region_gap_path_count" in status
    assert "affordance_region_bbox_axis_gap_band_proxy" in status
    assert "inferred_region_gap_path_occupancy_ratio" in status
    assert "inferred_gap_band_overlap_with_object_footprints_and_affordance_zones" in status
    assert "inferred_region_gap_path_free_space_overlap_ratio" in status
    assert "inferred_gap_band_overlap_with_rect_cell_free_space_polygons" in status
    assert "inferred_region_gap_path_walkable_proxy_ratio" in status
    assert "clear_and_free_space_supported_inferred_gap_path_edges" in status
    assert "walkable_proxy_component_count" in status
    assert "walkable_proxy_components" in status
    assert "walkable_proxy_min_thickness" in status
    assert "walkable_proxy_mean_thickness" in status
    assert "walkable_proxy_edge_widths" in status
    assert "inferred_region_gap_path_min_width_pass_ratio" in status
    assert "scene.settings.required_path_width" in status
    assert "walkable_gap_band_thickness_over_manual_required_path_width" in status
    assert "walkable_gap_band_thickness_over_half_sampled_grid_resolution" in status
    assert "minimum_width_basis" in status
    assert "width_pass_edges" in status
    assert "width_fail_edges" in status
    assert "inferred-gap-path-occupancy" in status
    assert "occupied_area" in status
    assert "clear_status" in status
    assert "data-occupied" in status
    assert "data-occupancy-ratio" in status
    assert "data-clear-status" in status
    assert "inferred_region_gap_path_explicit_path_iou_mean" in status
    assert "affordance_gap_band_to_explicit_path_bbox_iou" in status
    assert "object_region_membership_coverage" in status
    assert "object_region_assignment_coverage" in status
    assert "region_column_bay_fit" in status
    assert "object_column_bay_local_position_coverage" in status
    assert "object_center_affine_position_in_nearest_column_bay" in status
    assert "column_grid_handoff.region_bays.items" in status
    assert "column_grid_handoff.object_bay_local_positions.items" in status
    assert "negative-space component bbox overlay evidence pass" in status
    assert "data-bbox-left" in status
    assert "column-grid overlay evidence pass" in status
    assert "data-score-max" in status
    assert "region-axis overlay evidence pass" in status
    assert "data-basis" in status
    assert "boundary-axis overlay evidence pass" in status
    assert "data-walk-block" in status
    assert "region-boundary cue overlay evidence pass" in status
    assert "data-proximity" in status
    assert "object-region membership overlay evidence pass" in status
    assert "data-object" in status
    assert "missing-region overlay evidence pass" in status
    assert "data-region-key" in status
    assert "opening_width_metadata_or_rect_max_dimension_mean" in status
    assert "width_source" in status
    assert "opening_width_metadata" in status
    assert "sampled_min_clearance_to_walk_blocker" in status
    assert "sampled_free_cell_center_to_nearest_walk_blocker_gap" in status
    assert "zero_clearance_sample_count" in status
    assert "min_clearance_samples" in status
    assert "sampled_zero_clearance_cell_ratio" in status
    assert "sampled_zero_clearance_cells_over_clearance_samples" in status
    assert "sampled_entry_reachable_min_clearance_to_walk_blocker" in status
    assert "sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap" in status
    assert "sampled_mean_entry_region_widest_clearance" in status
    assert "sampled_grid_widest_path_clearance_proxy" in status
    assert "path_cells" in status
    assert "sampled_widest_path_cell_evidence" in status
    assert "sampled_mean_entry_region_clearance_per_distance" in status
    assert "sampled_widest_clearance_over_entry_region_distance_proxy" in status
    assert "not medial-axis width field or navmesh clearance" in status
    assert "bbox-touch graph evidence" in audit
    assert "furniture_affordance_extent_count" in audit
    assert "adapter_payload.evidence_geometry.furniture_affordance_extents" in audit
    assert "furniture-affordance-extent" in audit
    assert "cad_room_minus_blocker_polygon_count" in audit
    assert "cad_room_minus_blocker_largest_component_area_ratio" in audit
    assert "shapely_largest_component_area_over_total_free_area" in audit
    assert "cad_room_minus_blocker_area_residual_ratio" in audit
    assert "cad_room_minus_blocker_entry_connected_region_ratio" in audit
    assert "cad_room_minus_blocker_entry_connected_area_ratio" in audit
    assert "shapely_component_entry_touched_area_ratio_proxy" in audit
    assert "cad_room_minus_blocker_entry_connected_component_ratio" in audit
    assert "shapely_component_entry_touched_component_count_proxy" in audit
    assert "cad_room_minus_blocker_entry_connected_region_pair_ratio" in audit
    assert "cad_room_minus_blocker_component_graph_edge_count" in audit
    assert "shapely_component_entry_region_touch_proxy" in audit
    assert "cad_room_minus_blocker_component_graph" in audit
    assert "shapely_room_polygon_difference_blocker_union" in audit
    assert "graph_component_count" in audit
    assert "cycle_rank_inputs" in audit
    assert "reached_region_ids" in audit
    assert "unreached_region_ids" in audit
    assert "not the final evaluation matrix" in status


def test_method_ledger_records_source_backed_method_decisions():
    ledger = Path("docs/indoor_layout_evaluation_matrix_method_ledger.md")
    assert ledger.exists()

    text = ledger.read_text(encoding="utf-8")
    assert "OCTA" in text
    assert "Visibility Graph Analysis" in text
    assert "Benedikt" in text
    assert "CGAL" in text
    assert "RhinoCommon" in text
    assert "VisualARQ" in text
    assert "bbox-touch graph evidence remains a proxy" in text
    assert "path polygon clearance proxy remains a proxy" in text
    assert "sampled occupancy grid BFS remains a proxy" in text
    assert "path_polygon_blocker_union_overlap_area" in text
    assert "path_touched_region_boundary_cue_strength_mean" in text
    assert "path_touched_region_boundary_cue_perimeter_influence_mean" in text
    assert "path_touched_region_boundary_cue_count_mean" in text
    assert "boundary_cue_kinds" in text
    assert "path_touched_region_boundary_grouping_strength_mean" in text
    assert "path_touched_region_boundary_walk_see_gap_mean" in text
    assert "boundary_cue_profiles" in text
    assert "path_region_split_tendency_proxy" in text
    assert "disconnected_entry_ratio" in text
    assert "disconnected_path_ratio" in text
    assert "closed_blocking_boundary_ratio" in text
    assert "hosted_entry_boundary_ratio" in text
    assert "fallback_entry_boundary_ratio" in text
    assert "host_relationships" in text
    assert "route_topology_handoff" in text
    assert "inferred gap-path clear/occupied proxies" in text
    assert "route_topology_handoff.cad_component_graph.items" in text
    assert "route_topology_handoff.free_space_polygon_graph.items" in text
    assert "visual_analysis_handoff" in text
    assert "visual_analysis_handoff.visibility_graph.items" in text
    assert "visual_analysis_handoff.isovist_radial_proxy.ray_items" in text
    assert "visual_analysis_handoff.isovist_radial_proxy.area_items" in text
    assert "material_calibration_handoff" in text
    assert "column_grid_handoff" in text
    assert "adapter_capability_matrix" in text
    assert "matrix_completion_audit" in text
    assert "completion_gate_from_current_metric_family_status" in text
    assert "notebook_audit_manifest" in text
    assert "boundary_weight_metadata_coverage" in text
    assert "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records" in text
    assert "path_disconnected_opening_ids" in text
    assert "adapter_reference_coverage" in text
    assert "adapter_reference_role_coverage" in text
    assert "adapter_payload" in text
    assert "export_adapter_payload_json" in text
    assert "score_matrix" in text
    assert "computed_unit_interval_metric_mean_by_view_id" in text
    assert "evidence_geometry" in text
    assert "inferred candidate regions/gap paths" in text
    assert "furniture_affordance_extent_count" in text
    assert "object_footprint_plus_own_affordance_zone_extent" in text
    assert "adapter_payload.evidence_geometry.furniture_affordance_extents" in text
    assert "free_space_polygon_graph" in text
    assert "free_space_polygon_graph_cycle_rank" in text
    assert "free_space_polygon_graph_mean_entry_region_distance" in text
    assert "free_space_polygon_graph_mean_edge_clearance_width" in text
    assert "free_space_polygon_graph_mean_entry_region_min_clearance_width" in text
    assert "free_space_polygon_graph_mean_entry_region_widest_clearance_width" in text
    assert "inferred_gap_path_width_free_space_clearance_ratio" in text
    assert "free_space_edge_clearance_width_over_inferred_gap_band_width" in text
    assert "free-space-graph-entry-region-path" in text
    assert "neutral_adapter_payload_export" in text
    assert "opening_width_metadata_or_rect_max_dimension_mean" in text
    assert "width_source" in text
    assert "opening_width_metadata" in text
    assert "opening bbox max dimensions only" not in text
    assert "sampled_min_clearance_to_walk_blocker" in text
    assert "sampled_free_cell_center_to_nearest_walk_blocker_gap" in text
    assert "zero_clearance_sample_count" in text
    assert "min_clearance_samples" in text
    assert "sampled_zero_clearance_cell_ratio" in text
    assert "sampled_zero_clearance_cells_over_clearance_samples" in text
    assert "sampled_entry_reachable_min_clearance_to_walk_blocker" in text
    assert "sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap" in text
    assert "sampled_mean_entry_region_widest_clearance" in text
    assert "sampled_grid_widest_path_clearance_proxy" in text
    assert "path_cells" in text
    assert "sampled_widest_path_cell_evidence" in text
    assert "sampled_mean_entry_region_clearance_per_distance" in text
    assert "sampled_widest_clearance_over_entry_region_distance_proxy" in text
    assert "not medial-axis width field or navmesh clearance" in text
    assert "negative_space_area_ratio_proxy" in text
    assert "room_polygon_minus_blocker_union_area_proxy" in text
    assert "sampled_negative_space_area_ratio_delta" in text
    assert "negative_space_polygon_overlap_risk_count" in text
    assert "blocker union area" in text
    assert "separate polygon blockers" in text
    assert "identical blocker geometry" in text
    assert "negative_space_component_count" in text
    assert "negative_space_entry_connected_component_ratio" in text
    assert "component_rects" in text
    assert "cell_count" in text
    assert "cell_rects" in text
    assert "component_cell_area_sums" in text
    assert "free_space_polygons" in text
    assert "free_space_polygon_adjacency" in text
    assert "negative_space_free_polygon_count" in text
    assert "negative_space_room_minus_blocker_polygon_count" in text
    assert "cad_room_minus_blocker_polygon_count" in text
    assert "cad_room_minus_blocker_largest_component_area_ratio" in text
    assert "shapely_largest_component_area_over_total_free_area" in text
    assert "cad_room_minus_blocker_area_residual_ratio" in text
    assert "cad_room_minus_blocker_entry_connected_region_ratio" in text
    assert "cad_room_minus_blocker_entry_connected_area_ratio" in text
    assert "shapely_component_entry_touched_area_ratio_proxy" in text
    assert "cad_room_minus_blocker_entry_connected_component_ratio" in text
    assert "shapely_component_entry_touched_component_count_proxy" in text
    assert "cad_room_minus_blocker_entry_connected_region_pair_ratio" in text
    assert "shapely_component_entry_connected_region_pair_proxy" in text
    assert "cad_room_minus_blocker_component_graph_edge_count" in text
    assert "shapely_component_entry_region_touch_proxy" in text
    assert "cad_room_minus_blocker_component_touch_evidence" in text
    assert "cad_room_minus_blocker_entry_connected_area" in text
    assert "cad_room_minus_blocker_component_graph" in text
    assert "shapely_component_entry_region_touch_graph_proxy" in text
    assert "rect_cell_room_minus_blocker_boundary_union_proxy" in text
    assert "shapely_room_polygon_difference_blocker_union" in text
    assert "shapely_room_minus_blocker_area_minus_negative_space_area" in text
    assert "room_minus_blocker_polygons" in text
    assert "cad_room_minus_blocker_polygons" in text
    assert "negative_space_free_polygon_adjacency_count" in text
    assert "room_polygon_rect_cell_free_space_polygons_proxy" in text
    assert "room_polygon_rect_cell_shared_edge_adjacency_proxy" in text
    assert "negative_space_mean_entry_region_free_polygon_distance" in text
    assert "entry_to_region_rect_cell_adjacency_shortest_path_proxy" in text
    assert "negative_space_mean_entry_region_free_polygon_path_length" in text
    assert "entry_to_region_rect_cell_centerline_length_proxy" in text
    assert "component_area_total" in text
    assert "component_cell_area_sum_total" in text
    assert "negative_space_component_area_residual" in text
    assert "negative_space_component_area_residual_ratio" in text
    assert "max_component_cell_area_residual_ratio" in text
    assert "negative_space_component_cell_area_residual_ratio" in text
    assert "room_polygon_rect_cell_decomposition_proxy" in text
    assert "polygon blocker" in text
    assert "negative_space_entry_connected_area_ratio" in text
    assert "negative_space_graph" in text
    assert "negative_space_entry_connected_region_ratio" in text
    assert "entry_connected_region_ids" in text
    assert "non_entry_connected_region_ids" in text
    assert "negative_space_entry_connected_region_pair_ratio" in text
    assert "entry_connected_region_pair_evidence" in text
    assert "unconnected_region_pair_evidence" in text
    assert "candidate_path_region_pair_ratio_proxy" in text
    assert "sampled_entry_reachable_region_pair_ratio" in text
    assert "sampled_visibility_reachable_region_pair_ratio" in text
    assert "sampled_walk_visibility_disagreement_region_pair_ratio" in text
    assert "sampled_mean_region_pair_grid_distance" in text
    assert "sampled_resolution_sensitivity" in text
    assert "line_of_sight_region_pair_ratio" in text
    assert "isovist_radial_blocked_ray_ratio" in text
    assert "radial_isovist_see_block_ray_intersection_proxy" in text
    assert "isovist_radial_hit_polygon_area_mean" in text
    assert "radial_isovist_hit_point_polygon_area_proxy" in text
    assert "mean_hit_polygon_area" in text
    assert "blocking_boundary_evidence" in text
    assert "intersection_points" in text
    assert "dead_end_nodes" in text
    assert "cycle_rank_inputs" in text
    assert "graph_component_count" in text
    assert "reached_region_ids" in text
    assert "unreached_region_ids" in text
    assert "negative_space_entry_connected_region_area_coverage_ratio" in text
    assert "object_column_axis_phase_alignment" in text
    assert "region_centroid_phase_alignment" in text
    assert "region_centroid_trend_alignment" in text
    assert "region_centroid_pca_axis_cross_deviation_score" in text
    assert "affordance_use_zone_count" in text
    assert "object_footprint_adjacent_affordance_rect_zones" in text
    assert "furniture-affordance-extent" in text
    assert "geometry_basis=object_footprints_plus_affordance_zone_rects" in text
    assert "affordance_zone_ids" in text
    assert "inferred_region_candidate_count" in text
    assert "affordance_zone_boundary_cue_expanded_group_candidate_bounds" in text
    assert "inferred_region_count" in text
    assert "affordance_expanded_group_bounds" in text
    assert "inferred_region_explicit_iou_mean" in text
    assert "affordance_expanded_candidate_region_to_explicit_region_iou" in text
    assert "inferred_region_gap_path_count" in text
    assert "affordance_region_bbox_axis_gap_band_proxy" in text
    assert "inferred_region_gap_path_occupancy_ratio" in text
    assert "inferred_gap_band_overlap_with_object_footprints_and_affordance_zones" in text
    assert "inferred_region_gap_path_free_space_overlap_ratio" in text
    assert "inferred_gap_band_overlap_with_rect_cell_free_space_polygons" in text
    assert "inferred_region_gap_path_cad_free_space_overlap_ratio" in text
    assert "inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons" in text
    assert "cad_free_space_supported_edge_count" in text
    assert "cad_free_space_supported_edges" in text
    assert "adapter_payload.evidence_geometry.inferred_region_gap_path_cad_free_space_overlap" in text
    assert "inferred_region_gap_path_walkable_proxy_ratio" in text
    assert "clear_and_free_space_supported_inferred_gap_path_edges" in text
    assert "walkable_proxy_component_count" in text
    assert "walkable_proxy_components" in text
    assert "walkable_proxy_min_thickness" in text
    assert "walkable_proxy_mean_thickness" in text
    assert "walkable_proxy_edge_widths" in text
    assert "inferred_region_gap_path_min_width_pass_ratio" in text
    assert "scene.settings.required_path_width" in text
    assert "walkable_gap_band_thickness_over_manual_required_path_width" in text
    assert "walkable_gap_band_thickness_over_half_sampled_grid_resolution" in text
    assert "minimum_width_basis" in text
    assert "width_pass_edges" in text
    assert "width_fail_edges" in text
    assert "inferred-gap-path-occupancy" in text
    assert "occupied_area" in text
    assert "clear_status" in text
    assert "data-occupied" in text
    assert "data-occupancy-ratio" in text
    assert "data-clear-status" in text
    assert "inferred_region_gap_path_explicit_path_iou_mean" in text
    assert "affordance_gap_band_to_explicit_path_bbox_iou" in text
    assert "object_region_membership_coverage" in text
    assert "object_region_assignment_coverage" in text
    assert "region_column_bay_fit" in text
    assert "object_column_bay_local_position_coverage" in text
    assert "column_grid_handoff.region_bays.items" in text
    assert "column_grid_handoff.object_bay_local_positions.items" in text
    assert "local-frame containment proxy" in text

