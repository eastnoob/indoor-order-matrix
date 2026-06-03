import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.affordance import (
    AffordanceProfile,
    AffordanceBand,
    AisleProfile,
    ClearanceBand,
    Furniture,
    GridFrame,
    Polygon,
    Rect,
    RoadBand,
    SceneModel,
    SpatialGridBackend,
    build_affordance_band,
    build_affordance_bands,
    resolve_affordance_profile,
    resolve_aisle_profile,
)
from features.affordance.continuous_conflict import (
    geometry_intersection_polygon,
    geometry_overlaps,
    sample_overlap_cells,
)
from features.affordance.evaluator import (
    AffordanceEvaluator,
    AisleEvaluator,
    evaluate_spatial_access,
)
from features.affordance.visualization import scene_grid_overlay_svg
from features.analyzer import OrderAnalyzer
from features.entities import Chair, Road, Table, TableGrid, TableTemplate


def test_rect_geometry_helpers():
    rect = Rect(cx=10, cy=20, width=6, height=8)

    assert rect.left == pytest.approx(7)
    assert rect.right == pytest.approx(13)
    assert rect.top == pytest.approx(16)
    assert rect.bottom == pytest.approx(24)
    assert rect.area == pytest.approx(48)

    expanded = rect.expanded(left=1, right=3, top=2, bottom=4)
    assert expanded.left == pytest.approx(6)
    assert expanded.right == pytest.approx(16)
    assert expanded.top == pytest.approx(14)
    assert expanded.bottom == pytest.approx(28)
    assert expanded.cx == pytest.approx(11)
    assert expanded.cy == pytest.approx(21)
    assert expanded.width == pytest.approx(10)
    assert expanded.height == pytest.approx(14)

    assert rect.intersects(Rect(cx=13, cy=20, width=2, height=2))
    assert not rect.intersects(Rect(cx=20, cy=20, width=2, height=2))


def test_polygon_contains_point_and_bounds_for_rotated_rect():
    polygon = Polygon.from_local_rect(
        cx=100,
        cy=100,
        width=40,
        height=20,
        orientation=45,
    )

    assert len(polygon.points) == 4
    assert polygon.contains_point(100, 100)
    assert not polygon.contains_point(100, 70)
    assert polygon.bounds.width > 40
    assert polygon.bounds.height > 20


def test_continuous_geometry_overlap_helpers_ignore_edge_touch_and_handle_rotation():
    touching_left = Rect(cx=10, cy=10, width=20, height=20)
    touching_right = Rect(cx=30, cy=10, width=20, height=20)
    overlapping_road = Rect(cx=24, cy=10, width=12, height=40)
    rotated_table = Polygon.from_local_rect(
        cx=30,
        cy=10,
        width=28,
        height=14,
        orientation=45,
    )

    assert not geometry_overlaps(touching_left, touching_right)
    assert geometry_overlaps(overlapping_road, rotated_table)

    coarse_grid = SpatialGridBackend(width=80, height=80, resolution=20)
    fine_grid = SpatialGridBackend(width=80, height=80, resolution=10)
    coarse_cells = sample_overlap_cells(coarse_grid, overlapping_road, rotated_table)
    fine_cells = sample_overlap_cells(fine_grid, overlapping_road, rotated_table)

    assert coarse_cells
    assert fine_cells
    assert coarse_cells != fine_cells


def test_continuous_geometry_intersection_polygon_represents_real_overlap_area():
    clearance = Rect(cx=100, cy=100, width=40, height=120)
    affordance = Rect(cx=125, cy=100, width=30, height=40)
    rotated = Polygon.from_local_rect(
        cx=120,
        cy=100,
        width=40,
        height=20,
        orientation=45,
    )

    rect_overlap = geometry_intersection_polygon(clearance, affordance)
    rotated_overlap = geometry_intersection_polygon(clearance, rotated)

    assert rect_overlap is not None
    assert rect_overlap.bounds.left == pytest.approx(110)
    assert rect_overlap.bounds.right == pytest.approx(120)
    assert rect_overlap.bounds.top == pytest.approx(80)
    assert rect_overlap.bounds.bottom == pytest.approx(120)
    assert rotated_overlap is not None
    assert rotated_overlap.bounds.width < rotated.bounds.width
    assert rotated_overlap.bounds.height <= rotated.bounds.height


def test_scene_model_indexes_furniture_entities():
    table = Furniture(
        id="t1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=10, cy=10, width=20, height=10),
        parent_id="room-a",
    )
    chair = Furniture(
        id="c1",
        type_id="chair.default",
        role="chair",
        rect=Rect(cx=35, cy=10, width=10, height=10),
        parent_id="room-a",
    )
    grid = GridFrame(id="g1", kind="column_grid", parent_id="room-a")

    scene = SceneModel(entities=[table, chair], grids=[grid])

    assert scene.get_entity("t1") is table
    assert scene.entities_by_role("table") == [table]
    assert scene.entities_by_parent("room-a") == [table, chair]
    assert scene.grid_by_id["g1"] is grid


def test_affordance_profile_supports_edge_specific_depth_override():
    profile = resolve_affordance_profile(
        "table.default",
        override={
            "edge_depth": {"top": 40, "left": 10},
            "usable_edges": ("top", "left"),
            "coverage_threshold": 0.8,
        },
    )

    assert isinstance(profile, AffordanceProfile)
    assert profile.usable_edges == ("top", "left")
    assert profile.depth_for("top") == pytest.approx(40)
    assert profile.depth_for("left") == pytest.approx(10)
    assert profile.depth_for("bottom") == pytest.approx(0)
    assert profile.coverage_threshold == pytest.approx(0.8)


def test_aisle_profile_allows_instance_override():
    profile = resolve_aisle_profile(
        "chair.default",
        override={"min_width": 90, "reachability_required": False},
    )

    assert isinstance(profile, AisleProfile)
    assert profile.min_width == pytest.approx(90)
    assert profile.reachability_required is False


def test_spatial_grid_marks_occupied_and_affordance_owner_tags():
    grid = SpatialGridBackend(width=100, height=100, resolution=10)
    table_rect = Rect(cx=50, cy=50, width=20, height=20)
    affordance_rect = table_rect.expanded(left=10)

    grid.mark_occupied("t1", table_rect)
    grid.mark_affordance("t1", affordance_rect)

    occupied_cells = grid.cells_with("occupied_by", "t1")
    affordance_cells = grid.cells_with("affordance_for", "t1")

    assert occupied_cells
    assert affordance_cells
    assert all("t1" in grid.cells[row][col].occupied_by for row, col in occupied_cells)
    assert all("t1" in grid.cells[row][col].affordance_for for row, col in affordance_cells)
    assert not grid.free(*occupied_cells[0])


def test_spatial_grid_samples_rect_by_cell_area_intersection():
    grid = SpatialGridBackend(width=360, height=360, resolution=20)
    narrow_road = Rect(cx=240, cy=180, width=12, height=360)

    cells = set(grid.iter_indices_in_rect(narrow_road))

    assert cells
    assert (0, 11) in cells
    assert (0, 12) in cells


def test_spatial_grid_detects_conflicted_affordance_cells():
    grid = SpatialGridBackend(width=100, height=100, resolution=10)
    table_rect = Rect(cx=50, cy=50, width=20, height=20)
    chair_rect = Rect(cx=35, cy=50, width=10, height=10)

    grid.mark_occupied("t1", table_rect)
    grid.mark_affordance("t1", table_rect.expanded(left=20))
    grid.mark_occupied("c1", chair_rect)
    grid.mark_conflicts()

    conflict_cells = grid.cells_with("conflict_for", "t1")

    assert conflict_cells
    assert any("c1" in grid.cells[row][col].occupied_by for row, col in conflict_cells)


def test_spatial_grid_marks_aisle_and_aisle_conflict_owner_tags():
    grid = SpatialGridBackend(width=100, height=100, resolution=10)
    table_rect = Rect(cx=50, cy=50, width=20, height=20)

    grid.mark_occupied("t1", table_rect)
    grid.mark_aisle("t1", table_rect.expanded(left=20, right=20, top=20, bottom=20))
    grid.mark_affordance("t1", table_rect.expanded(right=20))
    grid.mark_aisle_conflicts()

    aisle_cells = grid.cells_with("aisle_for", "t1")
    aisle_conflict_cells = grid.cells_with("aisle_conflict_for", "t1")

    assert aisle_cells
    assert aisle_conflict_cells
    assert all("t1" in grid.cells[row][col].aisle_for for row, col in aisle_cells)
    assert any("t1" in grid.cells[row][col].affordance_for for row, col in aisle_conflict_cells)


def test_affordance_evaluator_reports_low_coverage_when_blocked():
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=100, height=50),
        affordance={
            "usable_edges": ("right",),
            "edge_depth": {"right": 100},
            "coverage_threshold": 0.75,
        },
    )
    blocker = Furniture(
        id="blocker_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=175, cy=100, width=50, height=50),
    )
    scene = SceneModel(entities=[table, blocker])

    result = AffordanceEvaluator(width=300, height=200, resolution=25).evaluate(scene)

    assert result["enabled"] is True
    assert result["backend"] == "grid"
    assert result["score"] < 1.0
    assert result["objects"]["table_1"]["coverage"] < 1.0
    assert result["objects"]["table_1"]["blocked_edges"] == ["right"]
    assert result["violations"]
    assert result["violations"][0]["type"] == "affordance_coverage_low"
    assert result["violations"][0]["suggestion_hint"] == "increase_clearance"


def test_affordance_evaluator_uses_external_edge_band_not_furniture_body():
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=100, height=50),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 50}},
    )
    scene = SceneModel(entities=[table])

    result = AffordanceEvaluator(width=300, height=200, resolution=25).evaluate(scene)

    assert result["objects"]["table_1"]["required_cells"] == 4
    assert result["objects"]["table_1"]["effective_cells"] == 4


def test_aisle_evaluator_marks_unreachable_object_when_blocked_by_wall():
    wall = Furniture(
        id="wall_1",
        type_id="furniture.default",
        role="obstacle",
        rect=Rect(cx=150, cy=100, width=50, height=200),
    )
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=250, cy=100, width=40, height=40),
    )
    scene = SceneModel(entities=[wall, table])

    result = AisleEvaluator(width=300, height=200, resolution=50).evaluate(scene)

    assert result["enabled"] is True
    assert result["score"] < 1.0
    assert result["reachable_objects"] == []
    assert result["unreachable_objects"] == ["table_1"]
    assert result["bottlenecks"]
    assert result["bottlenecks"][0]["suggestion_hint"] == "open_aisle_path"


def test_aisle_evaluator_reports_reserved_corridor_conflicts():
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=40, height=40),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 40}},
        aisle={"min_width": 40},
    )
    blocker = Furniture(
        id="blocker_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=135, cy=100, width=30, height=30),
    )
    scene = SceneModel(entities=[table, blocker])

    result = AisleEvaluator(width=220, height=200, resolution=10).evaluate(scene)

    assert result["score"] < 1.0
    assert "table_1" in result["objects"]
    assert result["objects"]["table_1"]["aisle_cells"] > 0
    assert result["objects"]["table_1"]["blocked_aisle_cells"] > 0
    assert result["objects"]["table_1"]["affordance_conflict_cells"] > 0
    assert result["debug"]["aisle"]
    assert result["debug"]["aisle_conflict"]
    assert any(item["type"] == "aisle_blocked" for item in result["bottlenecks"])
    assert any(item["type"] == "affordance_aisle_conflict" for item in result["bottlenecks"])


def test_table_and_chair_cells_include_profile_overrides():
    table = Table(
        id="table_1",
        size=(120, 80),
        affordance={"usable_edges": ("right",)},
        aisle={"min_width": 100},
    )
    chair = Chair(id="chair_1", size=(40, 40), orientation=180)

    table_cell = table.to_cell()
    chair_cell = chair.to_cell()

    assert table_cell["id"] == "table_1"
    assert table_cell["type_id"] == "table.default"
    assert table_cell["affordance"]["usable_edges"] == ("right",)
    assert table_cell["aisle"]["min_width"] == 100
    assert chair_cell["id"] == "chair_1"
    assert chair_cell["role"] == "chair"
    assert chair_cell["type_id"] == "chair.default"
    assert chair_cell["shape"] == "circle"


def test_table_align_right_is_preserved_as_user_level_cell_semantics():
    table = Table(id="right_table", size=(40, 20), align="right")

    cell = table.to_cell()

    assert cell["id"] == "right_table"
    assert cell["align"] == "right"
    assert "x_offset" not in cell


def test_order_analyzer_report_includes_affordance_and_aisle_when_enabled():
    grid = [
        [
            Table(
                id="table_1",
                size=(80, 40),
                affordance={
                    "usable_edges": ("right",),
                    "edge_depth": {"right": 80},
                },
            ),
            Table(id="blocker_1", size=(40, 40)),
        ]
    ]

    report = OrderAnalyzer(
        actual_matrix=grid,
        ideal_matrix=grid,
        layout_size=(300, 150),
        fit_to_layout=True,
    ).report(
        features=("shapes",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 150, "resolution": 25},
    )

    assert report["affordance"]["enabled"] is True
    assert report["affordance"]["backend"] == "grid"
    assert "table_1" in report["affordance"]["objects"]
    assert report["aisle"]["enabled"] is True
    assert report["schema"]["defaults"]["id"] == ""
    assert report["schema"]["defaults"]["type_id"] == ""


def test_align_right_places_table_at_cell_right_edge_for_scene_model():
    ideal = [
        [Table(id="t00", size=(40, 20)), Table(id="t01", size=(40, 20))],
    ]
    actual = [
        [
            Table(id="t00", size=(40, 20)),
            Table(id="t01", size=(40, 20), align="right"),
        ],
    ]

    analyzer = OrderAnalyzer(
        actual_matrix=actual,
        ideal_matrix=ideal,
        layout_size=(200, 100),
        fit_to_layout=True,
    )

    scene = analyzer._build_scene_model()

    # Cell [0][1] center is x=150. Right aligning a 40-wide table in a 100-wide
    # cell shifts its center by (100 - 40) / 2 = 30.
    assert scene.get_entity("t01").rect.cx == pytest.approx(180)
    assert scene.get_entity("t01").rect.right == pytest.approx(200)


def test_explicit_x_offset_overrides_align_right():
    actual = [[{"shape": "rect", "id": "t", "size": (40, 20), "align": "right", "x_offset": 5}]]

    analyzer = OrderAnalyzer(
        actual_matrix=actual,
        ideal_matrix=actual,
        layout_size=(100, 100),
        fit_to_layout=True,
    )

    scene = analyzer._build_scene_model()

    assert scene.get_entity("t").rect.cx == pytest.approx(55)


def test_report_scores_positions_and_affordance_for_align_right_table():
    ideal = [
        [Table(id="t00", size=(40, 20)), Table(id="t01", size=(40, 20))],
    ]
    actual = [
        [
            Table(id="t00", size=(40, 20)),
            Table(
                id="t01",
                size=(40, 20),
                align="right",
                affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
            ),
        ],
    ]

    report = OrderAnalyzer(
        actual_matrix=actual,
        ideal_matrix=ideal,
        layout_size=(200, 100),
        fit_to_layout=True,
    ).report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 200, "height": 100, "resolution": 10},
    )

    assert report["order"] < 1.0
    assert report["deviance_by_feature"]["positions"]["count"] == 1
    assert report["deviance_cells"] == [{"row": 0, "col": 1}]
    assert report["affordance"]["enabled"] is True
    assert report["aisle"]["enabled"] is True
    assert "aisle" in report["aisle"]["debug"]
    assert "aisle_conflict" in report["aisle"]["debug"]


def test_table_grid_fills_instances_from_one_template_with_unique_ids():
    template = TableTemplate(
        size=(40, 20),
        type_id="table.training",
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
        aisle={"min_width": 60},
    )

    matrix = TableGrid(3, 3, fill=template).to_matrix()
    ids = [cell["id"] for row in matrix for cell in row]

    assert len(matrix) == 3
    assert len(matrix[0]) == 3
    assert ids == ["t11", "t12", "t13", "t21", "t22", "t23", "t31", "t32", "t33"]
    assert len(set(ids)) == 9
    assert all(cell["type_id"] == "table.training" for row in matrix for cell in row)
    assert matrix[0][0]["affordance"] == {"usable_edges": ("right",), "edge_depth": {"right": 20}}
    assert matrix[2][2]["aisle"] == {"min_width": 60}


def test_table_grid_place_override_is_instance_local():
    template = TableTemplate(
        size=(40, 20),
        type_id="table.training",
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
    )
    grid = TableGrid(3, 3, fill=template)

    grid.place(
        0,
        1,
        align="right",
        affordance={"usable_edges": ("left",), "edge_depth": {"left": 10}},
        x_offset=3,
    )
    matrix = grid.to_matrix()

    assert matrix[0][1]["id"] == "t12"
    assert matrix[0][1]["align"] == "right"
    assert matrix[0][1]["x_offset"] == 3
    assert matrix[0][1]["affordance"] == {"usable_edges": ("left",), "edge_depth": {"left": 10}}
    assert matrix[0][0]["align"] == "center"
    assert matrix[0][0]["affordance"] == {"usable_edges": ("right",), "edge_depth": {"right": 20}}
    assert matrix[0][0]["affordance"] is not matrix[0][1]["affordance"]


def test_road_intent_and_table_grid_layout_preserve_matrix_compatibility():
    road = Road(
        axis="vertical",
        between=(0, 1),
        width=80,
        min_clearance=None,
        offset=5,
        level="primary",
        priority=2,
    )

    intent = road.to_intent()

    assert intent["axis"] == "vertical"
    assert intent["between"] == (0, 1)
    assert intent["width"] == 80.0
    assert intent["min_clearance"] == 80.0
    assert intent["offset"] == 5.0
    assert intent["level"] == "primary"
    assert intent["priority"] == 2

    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.road(axis="vertical", between=(0, 1), width=80, min_clearance=60)
    matrix = grid.to_matrix()
    layout = grid.to_layout()

    assert isinstance(matrix, list)
    assert "roads" not in matrix[0][0]
    assert layout["matrix"][0][0]["id"] == "t11"
    assert layout["roads"][0]["width"] == 80.0
    assert layout["roads"][0]["min_clearance"] == 60.0


def test_order_analyzer_layout_input_builds_road_and_clearance_bands():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.road(axis="vertical", between=(0, 1), width=80, min_clearance=60)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()

    assert analyzer.road_intents[0]["axis"] == "vertical"
    assert scene.road_bands[0].rect.left == pytest.approx(60)
    assert scene.road_bands[0].rect.right == pytest.approx(140)
    assert scene.clearance_bands[0].rect.left == pytest.approx(70)
    assert scene.clearance_bands[0].rect.right == pytest.approx(130)
    assert scene.road_band_by_id[scene.road_bands[0].id] is scene.road_bands[0]
    assert scene.clearance_band_by_id[scene.clearance_bands[0].id] is scene.clearance_bands[0]


def test_scene_model_builds_continuous_affordance_bands_from_shifted_furniture():
    template = TableTemplate(
        size=(40, 20),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(0, 1, align="right")

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_matrix(),
        ideal_matrix=grid.to_matrix(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    band = scene.affordance_bands_by_owner["t12"][0]

    assert band.owner_id == "t12"
    assert band.edge == "right"
    assert band.rect.left == pytest.approx(scene.get_entity("t12").rect.right)
    assert band.rect.right == pytest.approx(scene.get_entity("t12").rect.right + 20)

    svg = scene_grid_overlay_svg(
        scene=scene,
        report=analyzer.report(
            features=("positions",),
            include_affordance=True,
            affordance_options={"width": 300, "height": 300, "resolution": 20},
        ),
        layout_size=(300, 300),
        resolution=20,
    )
    assert 'data-layer="affordance-band"' in svg
    assert 'data-affordance="t12:right"' in svg


def test_rotated_affordance_band_follows_furniture_local_edge():
    template = TableTemplate(
        size=(64, 44),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(2, 2, orientation=45)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_matrix(),
        ideal_matrix=TableGrid(3, 3, fill=template).to_matrix(),
        layout_size=(360, 360),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    entity = scene.get_entity("t33")
    band = scene.affordance_bands_by_owner["t33"][0]

    assert entity.footprint is not None
    assert band.polygon is not None
    assert entity.footprint.bounds.width > entity.rect.width
    assert set(band.polygon.points) != {
        (band.rect.left, band.rect.top),
        (band.rect.right, band.rect.top),
        (band.rect.right, band.rect.bottom),
        (band.rect.left, band.rect.bottom),
    }
    assert band.polygon.contains_point(band.rect.cx, band.rect.cy)
    assert not band.polygon.contains_point(entity.rect.right + 9, entity.rect.cy)
    assert band.rect.left < entity.rect.right

    svg = scene_grid_overlay_svg(
        scene=scene,
        report=analyzer.report(
            features=("orientations",),
            include_affordance=True,
            affordance_options={"width": 360, "height": 360, "resolution": 10},
        ),
        layout_size=(360, 360),
        resolution=10,
    )

    assert 'data-layer="affordance-band"' in svg
    assert 'data-affordance="t33:right"' in svg
    assert "<polygon" in svg


def test_affordance_geometry_helpers_are_public_and_local_edge_based():
    table = Furniture(
        id="t",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=40, height=20),
        orientation=0,
    )
    profile = resolve_affordance_profile(
        "table.default",
        {"usable_edges": ("right",), "edge_depth": {"right": 10}},
    )

    band = build_affordance_band(table, profile, "right")
    bands = build_affordance_bands([table])

    assert band.rect.left == pytest.approx(120)
    assert band.rect.right == pytest.approx(130)
    assert band.polygon.contains_point(125, 100)
    assert bands


def test_analyzer_does_not_own_affordance_geometry_rules():
    analyzer_source = Path("features/analyzer.py").read_text(encoding="utf-8")

    assert "_affordance_polygon_for_entity" not in analyzer_source
    assert "def _build_affordance_bands" not in analyzer_source
    assert "build_affordance_bands" in analyzer_source


def test_road_and_clearance_sampling_debug_layers_are_reported():
    template = TableTemplate(
        size=(40, 20),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 80}},
    )
    actual_grid = TableGrid(3, 3, fill=template)
    actual_grid.road(axis="vertical", between=(0, 1), width=80, min_clearance=60)
    ideal_grid = TableGrid(3, 3, fill=template)

    analyzer = OrderAnalyzer(
        actual_matrix=actual_grid.to_layout(),
        ideal_matrix=ideal_grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    report_20 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )
    report_10 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 10},
    )

    assert scene.road_bands[0].rect.left == pytest.approx(60)
    assert scene.clearance_bands[0].rect.left == pytest.approx(70)
    assert sum(map(sum, report_20["aisle"]["debug"]["road"])) > 0
    assert sum(map(sum, report_20["aisle"]["debug"]["clearance"])) > 0
    assert sum(map(sum, report_20["aisle"]["debug"]["clearance_conflict"])) > 0
    assert sum(map(sum, report_10["aisle"]["debug"]["road"])) > sum(
        map(sum, report_20["aisle"]["debug"]["road"])
    )
    assert any(
        item["type"] in {"clearance_blocked", "road_affordance_conflict"}
        for item in report_20["aisle"]["bottlenecks"]
    )


def test_table_grid_road_network_expands_all_semantic_grid_lines():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.enable_road_network(width=80, min_clearance=70)

    roads = grid.to_layout()["roads"]

    assert len(roads) == 8
    assert [road["index"] for road in roads if road["axis"] == "vertical"] == [0, 1, 2, 3]
    assert [road["index"] for road in roads if road["axis"] == "horizontal"] == [0, 1, 2, 3]
    assert all(road["width"] == 80.0 for road in roads)
    assert all(road["min_clearance"] == 70.0 for road in roads)


def test_table_grid_road_network_axis_override_and_disable():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.enable_road_network(width=80, min_clearance=70)
    grid.road(axis="vertical", index=1, width=100, priority=5)
    grid.road(axis="horizontal", index=2, enabled=False)

    roads = grid.to_layout()["roads"]
    by_axis_index = {(road["axis"], road["index"]): road for road in roads}

    assert len(roads) == 7
    assert ("horizontal", 2) not in by_axis_index
    assert by_axis_index[("vertical", 1)]["width"] == 100.0
    assert by_axis_index[("vertical", 1)]["priority"] == 5
    assert by_axis_index[("vertical", 0)]["width"] == 80.0


def test_order_analyzer_road_network_builds_axis_bands_without_road_conflicts():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.enable_road_network(width=80, min_clearance=70)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )

    assert len(scene.road_bands) == 8
    assert len(scene.clearance_bands) == 8
    assert scene.road_band_by_id["road.vertical.1"].rect.cx == pytest.approx(100)
    assert scene.road_band_by_id["road.horizontal.2"].rect.cy == pytest.approx(200)
    assert not any("road_road" in item["type"] for item in report["aisle"]["bottlenecks"])

    # Sum by owner counts overlapping road-road intersections more than once;
    # boolean union counts each sampled road cell once.
    debug = report["aisle"]["debug"]["road"]
    union_cells = sum(1 for row in debug for value in row if value)
    owner_sum = sum(sum(row) for row in debug)
    assert union_cells < owner_sum


def test_road_network_disables_legacy_per_furniture_aisle_halo():
    template = TableTemplate(
        size=(64, 44),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
        aisle={"min_width": 80},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(0, 1, align="right")
    grid.enable_road_network(width=12, min_clearance=12)
    grid.road(axis="vertical", index=1, width=16, min_clearance=16)
    grid.road(axis="horizontal", index=2, enabled=False)

    report = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(360, 360),
        fit_to_layout=True,
    ).report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 10},
    )

    assert sum(map(sum, report["aisle"]["debug"]["aisle"])) == 0
    assert sum(map(sum, report["aisle"]["debug"]["aisle_conflict"])) == 0
    assert not any(
        item["type"] == "affordance_aisle_conflict"
        for item in report["aisle"]["bottlenecks"]
    )


def test_road_network_clearance_conflict_survives_coarse_resolution_sampling():
    template = TableTemplate(
        size=(64, 44),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
        aisle={"min_width": 80},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(0, 1, align="right")
    grid.enable_road_network(width=12, min_clearance=12)
    grid.road(axis="vertical", index=1, width=16, min_clearance=16)
    grid.road(axis="horizontal", index=2, enabled=False)

    report = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=TableGrid(3, 3, fill=template).to_layout(),
        layout_size=(360, 360),
        fit_to_layout=True,
    ).report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 20},
    )

    assert sum(map(sum, report["aisle"]["debug"]["clearance"])) > 0
    assert sum(map(sum, report["aisle"]["debug"]["clearance_conflict"])) > 0
    assert any(
        item["type"] == "road_affordance_conflict"
        for item in report["aisle"]["bottlenecks"]
    )


def test_continuous_road_affordance_conflict_is_resolution_stable():
    template = TableTemplate(
        size=(64, 44),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
        aisle={"min_width": 80},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(0, 1, align="right")
    grid.enable_road_network(width=12, min_clearance=12)
    grid.road(axis="vertical", index=1, width=16, min_clearance=16)
    grid.road(axis="horizontal", index=2, enabled=False)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=TableGrid(3, 3, fill=template).to_layout(),
        layout_size=(360, 360),
        fit_to_layout=True,
    )
    report_20 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 20},
    )
    report_10 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 10},
    )

    conflicts_20 = report_20["aisle"]["debug"]["continuous_conflicts"]
    conflicts_10 = report_10["aisle"]["debug"]["continuous_conflicts"]
    road_conflicts_20 = [
        item for item in conflicts_20 if item["type"] == "road_affordance_conflict"
    ]
    road_conflicts_10 = [
        item for item in conflicts_10 if item["type"] == "road_affordance_conflict"
    ]

    assert road_conflicts_20
    assert len(road_conflicts_20) == len(road_conflicts_10)
    assert report_20["aisle"]["score"] == pytest.approx(report_10["aisle"]["score"])

    sampled_20 = sum(map(sum, report_20["aisle"]["debug"]["clearance_conflict"]))
    sampled_10 = sum(map(sum, report_10["aisle"]["debug"]["clearance_conflict"]))
    assert sampled_20 > 0
    assert sampled_10 > 0
    assert sampled_20 != sampled_10


def test_overlay_draws_continuous_conflict_shape_from_geometry_source():
    template = TableTemplate(
        size=(64, 44),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
        aisle={"min_width": 80},
    )
    grid = TableGrid(3, 3, fill=template)
    grid.place(0, 1, align="right")
    grid.enable_road_network(width=12, min_clearance=12)
    grid.road(axis="vertical", index=1, width=16, min_clearance=16)
    grid.road(axis="horizontal", index=2, enabled=False)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=TableGrid(3, 3, fill=template).to_layout(),
        layout_size=(360, 360),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 20},
    )
    svg = scene_grid_overlay_svg(
        scene=scene,
        report=report,
        layout_size=(360, 360),
        resolution=20,
    )

    assert 'data-layer="continuous-conflict"' in svg
    assert 'data-conflict-type="road_affordance_conflict"' in svg
    assert 'data-source="road.vertical.2.clearance"' in svg


def test_continuous_affordance_blocker_reports_violation_without_grid_source_of_truth():
    owner = Furniture(
        id="owner",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=40, height=20),
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
    )
    blocker = Furniture(
        id="blocker",
        type_id="table.default",
        role="table",
        rect=Rect(cx=132, cy=100, width=16, height=18),
    )
    scene = SceneModel(
        entities=[owner, blocker],
        affordance_bands=build_affordance_bands([owner, blocker]),
    )

    result = evaluate_spatial_access(
        scene,
        width=200,
        height=200,
        resolution=20,
    )

    violations = result["affordance"]["violations"]
    assert any(
        item["type"] == "affordance_blocked_by_furniture"
        and item["object_ids"] == ["owner", "blocker"]
        for item in violations
    )
    assert any(
        item["type"] == "affordance_blocked_by_furniture"
        for item in result["affordance"]["debug"]["continuous_conflicts"]
    )


def test_table_grid_matrix_feeds_order_analyzer_and_right_align_scene_model():
    template = TableTemplate(size=(40, 20), type_id="table.training")
    ideal_grid = TableGrid(3, 3, fill=template)
    actual_grid = TableGrid(3, 3, fill=template)
    actual_grid.place(0, 1, align="right")

    analyzer = OrderAnalyzer(
        actual_matrix=actual_grid.to_matrix(),
        ideal_matrix=ideal_grid.to_matrix(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()

    # Cell [0][1] center is x=150. Right aligning a 40-wide table in a
    # 100-wide cell shifts its center by 30.
    assert scene.get_entity("t12").rect.cx == pytest.approx(180)
    assert scene.get_entity("t12").rect.right == pytest.approx(200)

    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )

    assert report["deviance_cells"] == [{"row": 0, "col": 1}]
    assert report["affordance"]["enabled"] is True
    assert report["aisle"]["enabled"] is True


def test_scene_grid_overlay_svg_exposes_geometry_and_sample_layers():
    template = TableTemplate(
        size=(40, 20),
        type_id="table.training",
        affordance={"usable_edges": ("right",), "edge_depth": {"right": 20}},
    )
    actual_grid = TableGrid(3, 3, fill=template)
    actual_grid.place(0, 1, align="right")
    ideal_grid = TableGrid(3, 3, fill=template)

    analyzer = OrderAnalyzer(
        actual_matrix=actual_grid.to_matrix(),
        ideal_matrix=ideal_grid.to_matrix(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    report_20 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )
    report_10 = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 10},
    )

    svg_20 = scene_grid_overlay_svg(
        scene=scene,
        report=report_20,
        layout_size=(300, 300),
        resolution=20,
        title="bridge overlay r20",
    )
    svg_10 = scene_grid_overlay_svg(
        scene=scene,
        report=report_10,
        layout_size=(300, 300),
        resolution=10,
        title="bridge overlay r10",
    )

    assert "<svg" in svg_20
    assert "t12" in svg_20
    assert "bbox" in svg_20
    assert "occupied" in svg_20
    assert "affordance" in svg_20
    assert "conflict" in svg_20
    assert "reachable" in svg_20
    assert "aisle" in svg_20
    assert "aisle_conflict" in svg_20
    assert "affordance_aisle_conflict" in svg_20
    assert 'data-bbox="t12:160.0,40.0,200.0,60.0"' in svg_20
    assert 'data-bbox="t12:160.0,40.0,200.0,60.0"' in svg_10
    assert svg_10.count('data-layer="sample-cell"') > svg_20.count('data-layer="sample-cell"')


def test_scene_grid_overlay_svg_rotates_oriented_entity_bbox():
    template = TableTemplate(size=(64, 44))
    grid = TableGrid(3, 3, fill=template)
    grid.place(2, 2, orientation=45)

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_matrix(),
        ideal_matrix=TableGrid(3, 3, fill=template).to_matrix(),
        layout_size=(360, 360),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    report = analyzer.report(
        features=("orientations",),
        include_affordance=True,
        affordance_options={"width": 360, "height": 360, "resolution": 20},
    )
    svg = scene_grid_overlay_svg(
        scene=scene,
        report=report,
        layout_size=(360, 360),
        resolution=20,
    )

    assert scene.get_entity("t33").orientation == pytest.approx(45)
    assert 'data-bbox="t33:' in svg
    assert 'points="292.9,261.8 338.2,307.1 307.1,338.2 261.8,292.9"' in svg
    assert "t33 bbox rot=45.0" in svg


def test_scene_model_uses_octa_center_positions_when_fit_to_layout():
    grid = [
        [Table(id="t1", size=(20, 10)), Table(id="t2", size=(20, 10))],
        [Table(id="t3", size=(20, 10)), Table(id="t4", size=(20, 10))],
    ]

    analyzer = OrderAnalyzer(
        actual_matrix=grid,
        ideal_matrix=grid,
        layout_size=(200, 100),
        fit_to_layout=True,
    )

    scene = analyzer._build_scene_model()

    assert scene.get_entity("t1").rect.cx == pytest.approx(50)
    assert scene.get_entity("t1").rect.cy == pytest.approx(25)
    assert scene.get_entity("t4").rect.cx == pytest.approx(150)
    assert scene.get_entity("t4").rect.cy == pytest.approx(75)


def test_order_analyzer_report_keeps_affordance_and_aisle_opt_in():
    grid = [[Table()]]

    report = OrderAnalyzer(actual_matrix=grid, ideal_matrix=grid).report(
        features=("shapes",)
    )

    assert "affordance" not in report
    assert "aisle" not in report


def test_affordance_aisle_demo_notebook_exists_and_mentions_key_outputs():
    notebook_path = Path("test/affordance_aisle_demo.ipynb")
    assert notebook_path.exists()

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook.get("cells", [])
    )

    assert "include_affordance=True" in source
    assert "affordance" in source
    assert "aisle" in source
    assert "conflict" in source
    assert "reachable" in source
    assert "OrderAnalyzer(" in source
    assert "_stim.Show()" in source
    assert "from order_analyzer import Chair, OrderAnalyzer, Table" in source
    assert "SceneModel(" not in source
    assert "matrix_to_svg" in source

    svg_output_count = 0
    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            if "image/svg+xml" in output.get("data", {}):
                svg_output_count += 1

    assert svg_output_count >= 6


def test_simple_3x3_table_affordance_demo_notebook_is_user_facing():
    notebook_path = Path("test/simple_3x3_table_affordance_demo.ipynb")
    assert notebook_path.exists()

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook.get("cells", [])
    )

    assert "TableTemplate" in source
    assert "TableGrid" in source
    assert 'grid.place(0, 1, align="right")' in source
    assert "grid.road(" in source
    assert "enable_road_network" in source
    assert "index=1" in source
    assert "enabled=False" in source
    assert "min_clearance" in source
    assert "to_layout()" in source
    assert "_stim.Show()" in source
    assert "include_affordance=True" in source
    assert "scene_grid_overlay_svg" in source
    assert "resolution comparison" in source
    assert "latent_grid_svg" in source
    assert "affordance.score" in source
    assert "continuous_conflicts" in source
    assert "deviance_cells" in source
    assert "continuous geometry bridge" in source
    assert "SpatialGridBackend" not in source

    svg_output_count = 0
    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            if "image/svg+xml" in output.get("data", {}):
                svg_output_count += 1

    assert svg_output_count >= 3
