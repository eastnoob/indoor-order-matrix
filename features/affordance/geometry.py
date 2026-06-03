from __future__ import annotations

from collections.abc import Iterable

from .models import AffordanceBand, Polygon, SpatialEntity
from .profiles import AffordanceProfile, resolve_affordance_profile


def build_affordance_polygon(
    entity: SpatialEntity,
    edge: str,
    depth: float,
) -> Polygon:
    # `edge` is local to the furniture. The band is created in furniture-local
    # coordinates, then rotated into scene space with the owning entity.
    rect = entity.rect
    if edge == "top":
        return Polygon.from_local_rect(
            cx=rect.cx,
            cy=rect.cy,
            width=rect.width,
            height=depth,
            orientation=entity.orientation,
            local_cy=-rect.height / 2 - depth / 2,
        )
    if edge == "right":
        return Polygon.from_local_rect(
            cx=rect.cx,
            cy=rect.cy,
            width=depth,
            height=rect.height,
            orientation=entity.orientation,
            local_cx=rect.width / 2 + depth / 2,
        )
    if edge == "bottom":
        return Polygon.from_local_rect(
            cx=rect.cx,
            cy=rect.cy,
            width=rect.width,
            height=depth,
            orientation=entity.orientation,
            local_cy=rect.height / 2 + depth / 2,
        )
    if edge == "left":
        return Polygon.from_local_rect(
            cx=rect.cx,
            cy=rect.cy,
            width=depth,
            height=rect.height,
            orientation=entity.orientation,
            local_cx=-rect.width / 2 - depth / 2,
        )
    return entity.footprint or Polygon.from_local_rect(
        cx=rect.cx,
        cy=rect.cy,
        width=rect.width,
        height=rect.height,
        orientation=entity.orientation,
    )


def build_affordance_band(
    entity: SpatialEntity,
    profile: AffordanceProfile,
    edge: str,
) -> AffordanceBand | None:
    # A zero-depth edge means "not active"; callers can simply skip None.
    depth = profile.depth_for(edge)
    if depth <= 0:
        return None
    polygon = build_affordance_polygon(entity, edge, depth)
    return AffordanceBand(
        id=f"{entity.id}.{edge}.affordance",
        owner_id=entity.id,
        edge=edge,
        rect=polygon.bounds,
        polygon=polygon,
        metadata={"type_id": entity.type_id},
    )


def build_affordance_bands(
    entities: Iterable[SpatialEntity],
) -> list[AffordanceBand]:
    bands: list[AffordanceBand] = []
    for entity in entities:
        profile = resolve_affordance_profile(entity.type_id, entity.affordance)
        for edge in profile.usable_edges:
            band = build_affordance_band(entity, profile, edge)
            if band is not None:
                bands.append(band)
    return bands
