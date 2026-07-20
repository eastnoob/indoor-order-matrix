"""
使用示例：

    actual = [
        [{"shape": "rect",   "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "circle", "attr": "B"}, {"shape": "rect",   "attr": "A"}],
    ]
    ideal = [
        [{"shape": "rect",   "attr": "A"}, {"shape": "circle", "attr": "B"}],
        [{"shape": "rect",   "attr": "A"}, {"shape": "circle", "attr": "B"}],
    ]

    from order_analyzer.analyzer import OrderAnalyzer
    result = OrderAnalyzer(actual, ideal).report(features=("shapes", "custom_attr"))
    print(result)
    # {"n_rows":2, "n_cols":2, "n_cells":4, "deviants":2, "order":0.5}
"""

from .analyzer import OrderAnalyzer
from .entities import Chair, Entry, Road, Table, TableGrid, TableTemplate
from .scene_evaluator import (
    evaluate_scene,
    export_adapter_payload_json,
    scene_metric_overlay_svg,
    validate_adapter_payload_json,
)
from .scene_loader import load_structured_svg_scene
from .room_analysis_model import build_room_analysis_model

__all__ = [
    "OrderAnalyzer",
    "Table",
    "Chair",
    "Entry",
    "Road",
    "TableTemplate",
    "TableGrid",
    "evaluate_scene",
    "export_adapter_payload_json",
    "load_structured_svg_scene",
    "scene_metric_overlay_svg",
    "validate_adapter_payload_json",
    "build_room_analysis_model",
]
