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

from importlib import import_module

# Native adapter contracts must remain importable without eagerly loading OCTA.
_EXPORT_MODULES = {
    "OrderAnalyzer": ".analyzer",
    "Table": ".entities", "Chair": ".entities", "Entry": ".entities",
    "Road": ".entities", "TableTemplate": ".entities", "TableGrid": ".entities",
    "evaluate_scene": ".scene_evaluator",
    "export_adapter_payload_json": ".scene_evaluator",
    "scene_metric_overlay_svg": ".scene_evaluator",
    "validate_adapter_payload_json": ".scene_evaluator",
    "load_structured_svg_scene": ".scene_loader",
    "build_room_analysis_model": ".room_analysis_model",
}


def __getattr__(name: str):
    """Resolve each pre-existing public export only when a caller requests it."""
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_EXPORT_MODULES[name], __name__), name)
    globals()[name] = value
    return value

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
