from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

EDGE_KEYS = ("top", "right", "bottom", "left")


@dataclass(frozen=True)
class AffordanceProfile:
    # Profile = default rule set. Instances can override fields through
    # resolve_affordance_profile(..., override=entity.affordance).
    usable_edges: tuple[str, ...] = EDGE_KEYS
    edge_depth: float | dict[str, float] = 0.0
    min_clearance: float = 0.0
    min_aisle_width: float = 0.0
    merge_policy: str = "union"
    coverage_threshold: float = 1.0

    def depth_for(self, edge: str) -> float:
        # Edge-specific depth supports asymmetric affordance zones, while a
        # scalar depth keeps the common/default case compact.
        if edge not in self.usable_edges:
            return 0.0
        if isinstance(self.edge_depth, dict):
            return float(self.edge_depth.get(edge, 0.0))
        return float(self.edge_depth)


@dataclass(frozen=True)
class AisleProfile:
    # Aisle profile is intentionally small in batch 1. Width/reachability are
    # enough for MVP scoring, and bottleneck ratio leaves room for soft warnings.
    min_width: float = 0.0
    reachability_required: bool = True
    bottleneck_soft_ratio: float = 0.8


DEFAULT_AFFORDANCE_PROFILES = {
    # Defaults are deliberately conservative placeholders. Later batches can
    # tune these per furniture type without changing the public resolver API.
    "furniture.default": AffordanceProfile(edge_depth=0.0),
    "table.default": AffordanceProfile(edge_depth=60.0, min_clearance=0.0),
    "chair.default": AffordanceProfile(
        usable_edges=("front",),
        edge_depth={"front": 40.0},
        min_clearance=0.0,
    ),
    "armchair.default": AffordanceProfile(edge_depth=15.0, min_clearance=0.0),
    "podium.default": AffordanceProfile(
        usable_edges=("front",),
        edge_depth={"front": 80.0},
        min_clearance=0.0,
    ),
}

DEFAULT_AISLE_PROFILES = {
    "furniture.default": AisleProfile(min_width=60.0),
    "table.default": AisleProfile(min_width=80.0),
    "chair.default": AisleProfile(min_width=60.0),
    "armchair.default": AisleProfile(min_width=60.0),
    "podium.default": AisleProfile(min_width=80.0),
}


def _merge_profile(profile: Any, override: dict[str, Any] | None) -> Any:
    if not override:
        return profile
    # dataclasses.replace preserves the profile type and only swaps explicit
    # instance-level override fields.
    return replace(profile, **override)


def resolve_affordance_profile(
    type_id: str,
    override: dict[str, Any] | None = None,
) -> AffordanceProfile:
    base = DEFAULT_AFFORDANCE_PROFILES.get(
        type_id,
        DEFAULT_AFFORDANCE_PROFILES["furniture.default"],
    )
    return _merge_profile(base, override)


def resolve_aisle_profile(
    type_id: str,
    override: dict[str, Any] | None = None,
) -> AisleProfile:
    base = DEFAULT_AISLE_PROFILES.get(
        type_id,
        DEFAULT_AISLE_PROFILES["furniture.default"],
    )
    return _merge_profile(base, override)
