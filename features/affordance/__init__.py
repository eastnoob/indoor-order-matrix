from .continuous_conflict import (
    ContinuousConflictEvaluator,
    geometry_overlaps,
    sample_overlap_cells,
)
from .evaluator import AffordanceEvaluator, AisleEvaluator, evaluate_spatial_access
from .geometry import (
    build_affordance_band,
    build_affordance_bands,
    build_affordance_polygon,
)
from .grid_backend import GridCell, SpatialGridBackend
from .models import (
    AffordanceBand,
    ClearanceBand,
    Furniture,
    GridFrame,
    Polygon,
    Rect,
    RoadBand,
    SceneModel,
    SpatialEntity,
)
from .profiles import (
    EDGE_KEYS,
    AffordanceProfile,
    AisleProfile,
    resolve_affordance_profile,
    resolve_aisle_profile,
)
from .visualization import resolution_comparison_svg, scene_grid_overlay_svg

__all__ = [
    "EDGE_KEYS",
    "AffordanceProfile",
    "AffordanceEvaluator",
    "AffordanceBand",
    "AisleProfile",
    "AisleEvaluator",
    "ClearanceBand",
    "ContinuousConflictEvaluator",
    "Furniture",
    "GridCell",
    "GridFrame",
    "Polygon",
    "Rect",
    "RoadBand",
    "SceneModel",
    "SpatialEntity",
    "SpatialGridBackend",
    "build_affordance_band",
    "build_affordance_bands",
    "build_affordance_polygon",
    "evaluate_spatial_access",
    "geometry_overlaps",
    "resolution_comparison_svg",
    "resolve_affordance_profile",
    "resolve_aisle_profile",
    "sample_overlap_cells",
    "scene_grid_overlay_svg",
]
