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

__all__ = ["OrderAnalyzer", "Table", "Chair", "Entry", "Road", "TableTemplate", "TableGrid"]
