"""
OrderAnalyzer package entry point.
"""

from importlib import import_module

# Keep adapter and headless imports independent of OCTA's renderer.
_EXPORT_MODULES = {
    "OrderAnalyzer": ".features.analyzer",
    "Table": ".features.entities", "Chair": ".features.entities",
    "Entry": ".features.entities", "Road": ".features.entities",
    "TableTemplate": ".features.entities", "TableGrid": ".features.entities",
}


def __getattr__(name: str):
    """Resolve each existing package export only when it is requested."""
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_EXPORT_MODULES[name], __name__), name)
    globals()[name] = value
    return value

__all__ = ["OrderAnalyzer", "Table", "Chair", "Entry", "Road", "TableTemplate", "TableGrid"]
