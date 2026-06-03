import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.analyzer import OrderAnalyzer, _resolve_cell_boundingbox
from features.entities import Table


def test_calculate_order_backward_compatible():
    actual = [
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
    ]
    ideal = [
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
    ]

    analyzer = OrderAnalyzer(actual, ideal)
    score = analyzer.calculate_order(features=("shapes", "custom_attr"))

    assert isinstance(score, float)
    assert score == pytest.approx(1.0)


def test_report_includes_component_scores():
    actual = [
        [
            {
                "shape": "rect",
                "attr": "T",
                "role": "table",
                "group": "g1",
                "orientation": 0,
            },
            {
                "shape": "circle",
                "attr": "C",
                "role": "chair",
                "group": "g1",
                "orientation": 180,
            },
        ],
        [
            {
                "shape": "rect",
                "attr": "T",
                "role": "table",
                "group": "g2",
                "orientation": 0,
            },
            {
                "shape": "circle",
                "attr": "C",
                "role": "chair",
                "group": "g2",
                "orientation": 180,
            },
        ],
    ]
    ideal = [
        [{"shape": "rect", "attr": "T"}, {"shape": "circle", "attr": "C"}],
        [{"shape": "rect", "attr": "T"}, {"shape": "circle", "attr": "C"}],
    ]

    analyzer = OrderAnalyzer(actual, ideal)
    report = analyzer.report(features=("shapes", "custom_attr", "orientations"))

    assert "scores" in report
    assert "details" in report
    assert "weights" in report

    for key in ("base_order", "intra", "inter", "rel", "total"):
        assert key in report["scores"]

    assert "relation" in report["details"]
    assert "subscores" in report["details"]["relation"]


def test_deviance_shape_only_boolean_map():
    ideal = [
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
    ]
    actual = [
        [{"shape": "circle", "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "rect", "attr": "A"}, {"shape": "circle", "attr": "B"}],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("shapes",))

    assert report["deviance_by_feature"]["shapes"]["count"] == 1
    assert report["deviance_matrix"] == [[1, 0], [0, 0]]
    assert report["deviance_cells"] == [{"row": 0, "col": 0}]


def test_deviance_orientation_only_boolean_map():
    ideal = [
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
    ]
    actual = [
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 45},
        ],
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("orientations",))

    assert report["deviance_by_feature"]["orientations"]["count"] == 1
    assert report["deviance_matrix"] == [[0, 1], [0, 0]]
    assert report["deviance_cells"] == [{"row": 0, "col": 1}]


def test_deviance_multi_feature_or_aggregation():
    ideal = [
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
    ]
    actual = [
        [
            {"shape": "circle", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 45},
        ],
        [
            {"shape": "rect", "attr": "A", "orientation": 0},
            {"shape": "circle", "attr": "B", "orientation": 0},
        ],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("shapes", "orientations"))

    assert report["deviance_by_feature"]["shapes"]["count"] == 1
    assert report["deviance_by_feature"]["orientations"]["count"] == 1
    # OR aggregation at cell level: two different cells deviate on different features.
    assert report["deviance_matrix"] == [[1, 1], [0, 0]]
    assert report["deviance_cells"] == [{"row": 0, "col": 0}, {"row": 0, "col": 1}]


def test_schema_and_semantic_defaults_are_exposed():
    actual = [
        [{"shape": "rect"}, {"shape": "circle"}],
        [{"shape": "rect"}, {"shape": "circle"}],
    ]
    ideal = [
        [{"shape": "rect"}, {"shape": "circle"}],
        [{"shape": "rect"}, {"shape": "circle"}],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("shapes",))

    assert report["schema"]["version"] == "v1"
    assert "shape" in report["schema"]["required"]
    assert report["semantic"]["role_grid"] == [["table", "chair"], ["table", "chair"]]
    assert report["semantic"]["group_grid"] == [
        ["global", "global"],
        ["global", "global"],
    ]
    assert report["semantic"]["role_counts"]["table"] == 2
    assert report["semantic"]["role_counts"]["chair"] == 2


def test_non_rectangular_matrix_raises_value_error():
    actual = [
        [{"shape": "rect"}, {"shape": "circle"}],
        [{"shape": "rect"}],
    ]
    ideal = [
        [{"shape": "rect"}, {"shape": "circle"}],
        [{"shape": "rect"}, {"shape": "circle"}],
    ]

    with pytest.raises(ValueError):
        OrderAnalyzer(actual, ideal)


def test_matrix_size_mismatch_raises_value_error():
    actual = [
        [{"shape": "rect"}, {"shape": "circle"}],
        [{"shape": "rect"}, {"shape": "circle"}],
    ]
    ideal = [
        [{"shape": "rect"}, {"shape": "circle"}, {"shape": "rect"}],
        [{"shape": "rect"}, {"shape": "circle"}, {"shape": "rect"}],
    ]

    with pytest.raises(ValueError):
        OrderAnalyzer(actual, ideal)


def test_table_class_input_is_supported():
    actual = [
        [Table(attr="A"), Table(attr="A", orientation=90)],
        [Table(attr="A"), Table(attr="A")],
    ]
    ideal = [
        [Table(attr="A"), Table(attr="A")],
        [Table(attr="A"), Table(attr="A")],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("orientations",))

    assert report["n_rows"] == 2
    assert report["n_cols"] == 2
    assert report["deviance_by_feature"]["orientations"]["count"] == 1
    assert report["deviance_matrix"] == [[0, 1], [0, 0]]


def test_table_shape_property_affects_visual_shape_without_changing_role():
    ideal = [
        [Table(shape="rect", attr="A"), Table(shape="rect", attr="A")],
        [Table(shape="rect", attr="A"), Table(shape="rect", attr="A")],
    ]
    actual = [
        [Table(shape="rect", attr="A"), Table(shape="circle", attr="A")],
        [Table(shape="rect", attr="A"), Table(shape="rect", attr="A")],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("shapes",))

    assert report["deviance_by_feature"]["shapes"]["count"] == 1
    assert report["deviance_matrix"] == [[0, 1], [0, 0]]
    assert report["semantic"]["role_counts"]["table"] == 4


def test_absolute_size_resolution_for_rect_and_circle():
    rect_size = _resolve_cell_boundingbox(
        {"shape": "rect", "size": (30, 50)}, default_cell_size=(40, 80)
    )
    circle_size = _resolve_cell_boundingbox(
        {"shape": "circle", "size": (30, 50)}, default_cell_size=(40, 80)
    )

    assert rect_size == (30.0, 50.0)
    assert circle_size == (30.0, 30.0)


def test_circle_defaults_to_true_circle_with_non_square_cell_size():
    circle_size = _resolve_cell_boundingbox(
        {"shape": "circle"}, default_cell_size=(40, 80)
    )
    rect_size = _resolve_cell_boundingbox({"shape": "rect"}, default_cell_size=(40, 80))

    assert circle_size == (40.0, 40.0)
    assert rect_size == (40.0, 80.0)


def test_table_size_field_is_passed_to_cell_schema():
    cell = Table(shape="circle", size=24, attr="A").to_cell()

    assert cell["shape"] == "circle"
    assert cell["size"] == 24
    assert cell["role"] == "table"


def test_fixed_layout_derives_spacing_and_stimulus_size():
    grid = [
        [{"shape": "rect"}, {"shape": "rect"}],
        [{"shape": "rect"}, {"shape": "rect"}],
    ]

    analyzer = OrderAnalyzer(
        actual_matrix=grid,
        ideal_matrix=grid,
        layout_size=(1350, 850),
        fit_to_layout=True,
        unit_scale=0.1,
    )
    report = analyzer.report(features=("shapes",))

    assert analyzer.spacing == pytest.approx((42.0, 68.0))
    assert analyzer.stim_size == pytest.approx((135.0, 85.0))
    assert report["layout"]["spacing"] == [42, 68]
    assert report["layout"]["size"] == [135.0, 85.0]


def test_fixed_layout_grid_points_cover_layout_span():
    grid = [
        [{"shape": "rect"}, {"shape": "rect"}],
        [{"shape": "rect"}, {"shape": "rect"}],
    ]

    analyzer = OrderAnalyzer(
        actual_matrix=grid,
        ideal_matrix=grid,
        layout_size=(1350, 850),
        fit_to_layout=True,
        unit_scale=0.1,
    )
    analyzer._prepare()

    # Grid points are centered within each cell (allow small drift from int spacing rounding).
    assert analyzer._stim.positions.x == pytest.approx(
        [33.75, 101.25, 33.75, 101.25], abs=0.5
    )
    assert analyzer._stim.positions.y == pytest.approx(
        [21.25, 21.25, 63.75, 63.75], abs=0.5
    )


def test_positions_feature_counts_offset_deviance():
    ideal = [
        [{"shape": "rect", "attr": "A"}, {"shape": "rect", "attr": "A"}],
        [{"shape": "rect", "attr": "A"}, {"shape": "rect", "attr": "A"}],
    ]
    actual = [
        [
            {"shape": "rect", "attr": "A"},
            {"shape": "rect", "attr": "A", "x_offset": 8},
        ],
        [{"shape": "rect", "attr": "A"}, {"shape": "rect", "attr": "A"}],
    ]

    report = OrderAnalyzer(actual, ideal).report(features=("positions",))

    assert report["deviance_by_feature"]["positions"]["count"] == 1
    assert report["deviance_matrix"] == [[0, 1], [0, 0]]
    assert report["order"] == pytest.approx(0.75)
