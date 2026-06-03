from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .continuous_conflict import ContinuousConflictEvaluator, sample_overlap_cells
from .geometry import build_affordance_polygon
from .grid_backend import SpatialGridBackend
from .models import Rect, SceneModel, SpatialEntity
from .profiles import AffordanceProfile, resolve_affordance_profile, resolve_aisle_profile


def _edge_band(rect: Rect, edge: str, depth: float) -> Rect:
    # Edge bands are external strips only. They intentionally exclude the
    # furniture body, otherwise coverage would be diluted by occupied body cells.
    if edge == "top":
        return Rect(
            cx=rect.cx,
            cy=rect.top - depth / 2,
            width=rect.width,
            height=depth,
        )
    if edge == "right":
        return Rect(
            cx=rect.right + depth / 2,
            cy=rect.cy,
            width=depth,
            height=rect.height,
        )
    if edge == "bottom":
        return Rect(
            cx=rect.cx,
            cy=rect.bottom + depth / 2,
            width=rect.width,
            height=depth,
        )
    if edge == "left":
        return Rect(
            cx=rect.left - depth / 2,
            cy=rect.cy,
            width=depth,
            height=rect.height,
        )
    return rect


def _matrix_counts(matrix: list[list[object]]) -> list[list[int]]:
    return [
        [len(value) if isinstance(value, set) else int(bool(value)) for value in row]
        for row in matrix
    ]


def _matrix_positive_cells(matrix: list[list[int]]) -> set[tuple[int, int]]:
    return {
        (row_index, col_index)
        for row_index, row in enumerate(matrix)
        for col_index, value in enumerate(row)
        if value
    }


def _entry_matrix(
    grid: SpatialGridBackend,
    entries: list[tuple[int, int]],
) -> list[list[int]]:
    # Entries are debug-only sampled start cells for BFS reachability.
    matrix = [[0 for _ in range(grid.n_cols)] for _ in range(grid.n_rows)]
    for row, col in entries:
        if 0 <= row < grid.n_rows and 0 <= col < grid.n_cols:
            matrix[row][col] = 1
    return matrix


@dataclass(frozen=True)
class _EdgeCoverage:
    edge: str
    required_cells: set[tuple[int, int]]
    conflict_cells: set[tuple[int, int]]

    @property
    def coverage(self) -> float:
        if not self.required_cells:
            return 1.0
        effective_count = len(self.required_cells - self.conflict_cells)
        return effective_count / len(self.required_cells)


class AffordanceEvaluator:
    def __init__(self, *, width: float, height: float, resolution: float = 50) -> None:
        self.width = width
        self.height = height
        self.resolution = resolution

    def evaluate(self, scene: SceneModel, continuous: dict | None = None) -> dict:
        grid = SpatialGridBackend(
            width=self.width,
            height=self.height,
            resolution=self.resolution,
        )
        for entity in scene.entities:
            grid.mark_occupied(entity.id, entity.footprint or entity.rect)

        objects = {}
        violations = []
        coverages = []

        for entity in scene.entities:
            profile = resolve_affordance_profile(entity.type_id, entity.affordance)
            edge_coverages = self._mark_entity_affordance(grid, entity, profile)

            required_cells = set().union(
                *(edge.required_cells for edge in edge_coverages)
            ) if edge_coverages else set()
            conflict_cells = set().union(
                *(edge.conflict_cells for edge in edge_coverages)
            ) if edge_coverages else set()
            coverage = (
                len(required_cells - conflict_cells) / len(required_cells)
                if required_cells
                else 1.0
            )
            blocked_edges = [
                edge.edge
                for edge in edge_coverages
                if edge.required_cells and edge.coverage < 1.0
            ]

            objects[entity.id] = {
                "coverage": round(coverage, 4),
                "required_cells": len(required_cells),
                "effective_cells": len(required_cells - conflict_cells),
                "required_area": round(len(required_cells) * grid.resolution**2, 4),
                "effective_area": round(
                    len(required_cells - conflict_cells) * grid.resolution**2,
                    4,
                ),
                "blocked_edges": blocked_edges,
            }
            coverages.append(coverage)

            if coverage < profile.coverage_threshold:
                violations.append(
                    {
                        "type": "affordance_coverage_low",
                        "severity": "soft",
                        "object_ids": [entity.id],
                        "required": profile.coverage_threshold,
                        "actual": round(coverage, 4),
                        "blocked_edges": blocked_edges,
                        "suggestion_hint": "increase_clearance",
                    }
                )

        if continuous is not None:
            violations.extend(continuous.get("affordance_violations", []))

        return {
            "enabled": True,
            "backend": "grid",
            "score": round(mean(coverages), 4) if coverages else 1.0,
            "objects": objects,
            "violations": violations,
            "debug": {
                "occupied": _matrix_counts(grid.debug_matrix("occupied_by")),
                "affordance": _matrix_counts(grid.debug_matrix("affordance_for")),
                "conflict": _matrix_counts(grid.debug_matrix("conflict_for")),
                "continuous_conflicts": (
                    continuous.get("debug", {}).get("affordance", [])
                    if continuous is not None
                    else []
                ),
            },
        }

    def _mark_entity_affordance(
        self,
        grid: SpatialGridBackend,
        entity: SpatialEntity,
        profile: AffordanceProfile,
    ) -> list[_EdgeCoverage]:
        edge_coverages = []
        for edge in profile.usable_edges:
            depth = profile.depth_for(edge)
            if depth <= 0:
                continue
            band = build_affordance_polygon(entity, edge, depth)
            required_cells = set(grid.iter_indices_in_polygon(band))
            if not required_cells:
                continue
            grid.mark_affordance(entity.id, band)
            grid.mark_conflicts()
            conflict_cells = set(grid.cells_with("conflict_for", entity.id))
            edge_coverages.append(
                _EdgeCoverage(
                    edge=edge,
                    required_cells=required_cells,
                    conflict_cells=required_cells & conflict_cells,
                )
            )
        return edge_coverages


class AisleEvaluator:
    def __init__(
        self,
        *,
        width: float,
        height: float,
        resolution: float = 50,
        entries: list[tuple[int, int]] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.resolution = resolution
        self.entries = entries

    def evaluate(
        self,
        scene: SceneModel,
        affordance_debug: dict | None = None,
        continuous: dict | None = None,
    ) -> dict:
        grid = SpatialGridBackend(
            width=self.width,
            height=self.height,
            resolution=self.resolution,
        )
        for entity in scene.entities:
            grid.mark_occupied(entity.id, entity.footprint or entity.rect)

        entries = self.entries or self._default_entries(grid)
        grid.compute_reachability(entries)
        affordance_cells = self._affordance_reference_cells(
            grid,
            scene,
            affordance_debug,
        )

        reachable_objects = []
        unreachable_objects = []
        objects = {}
        bottlenecks = []
        road_data = self._mark_scene_road_and_clearance_bands(
            grid,
            scene,
            affordance_cells,
            continuous,
        )
        # Once explicit RoadBand/ClearanceBand geometry exists, circulation is
        # evaluated from that geometry. The older object-centered halo remains
        # only as fallback for scenes that have no road model yet.
        use_object_halo_fallback = not scene.road_bands and not scene.clearance_bands
        for entity in scene.entities:
            if entity.role == "obstacle":
                continue
            profile = resolve_aisle_profile(entity.type_id, entity.aisle)
            if not profile.reachability_required:
                continue
            if use_object_halo_fallback:
                aisle_data = self._mark_entity_reserved_corridor(
                    grid,
                    entity,
                    profile.min_width,
                    affordance_cells,
                )
            else:
                # Keep per-object reporting shape stable while avoiding the
                # legacy halo conflicts that would duplicate RoadNetwork logic.
                aisle_data = {
                    "aisle_cells": set(),
                    "blocked_cells": set(),
                    "affordance_conflict_cells": set(),
                }
            if self._entity_reachable(grid, entity):
                reachable_objects.append(entity.id)
            else:
                unreachable_objects.append(entity.id)
                bottlenecks.append(
                    {
                        "type": "unreachable_object",
                        "severity": "hard",
                        "object_ids": [entity.id],
                        "suggestion_hint": "open_aisle_path",
                    }
                )

            objects[entity.id] = {
                "aisle_cells": len(aisle_data["aisle_cells"]),
                "blocked_aisle_cells": len(aisle_data["blocked_cells"]),
                "affordance_conflict_cells": len(aisle_data["affordance_conflict_cells"]),
            }
            if aisle_data["blocked_cells"]:
                bottlenecks.append(
                    {
                        "type": "aisle_blocked",
                        "severity": "hard",
                        "object_ids": [entity.id],
                        "blocked_cells": len(aisle_data["blocked_cells"]),
                        "suggestion_hint": "increase_corridor_clearance",
                    }
                )
            if aisle_data["affordance_conflict_cells"]:
                bottlenecks.append(
                    {
                        "type": "affordance_aisle_conflict",
                        "severity": "soft",
                        "object_ids": [entity.id],
                        "conflict_cells": len(aisle_data["affordance_conflict_cells"]),
                        "suggestion_hint": "separate_affordance_from_aisle",
                    }
                )

        if continuous is not None:
            bottlenecks.extend(continuous.get("aisle_bottlenecks", []))
        else:
            for band_id, data in road_data["clearance"].items():
                if data["blocked_cells"]:
                    bottlenecks.append(
                        {
                            "type": "clearance_blocked",
                            "severity": "hard",
                            "object_ids": [band_id],
                            "blocked_cells": len(data["blocked_cells"]),
                            "suggestion_hint": "increase_clearance_band",
                        }
                    )
                if data["affordance_conflict_cells"]:
                    bottlenecks.append(
                        {
                            "type": "road_affordance_conflict",
                            "severity": "soft",
                            "object_ids": [band_id],
                            "conflict_cells": len(data["affordance_conflict_cells"]),
                            "suggestion_hint": "separate_road_from_affordance",
                        }
                    )

        total = len(reachable_objects) + len(unreachable_objects)
        reachable_score = len(reachable_objects) / total if total else 1.0
        aisle_cells = sum(obj["aisle_cells"] for obj in objects.values()) + sum(
            len(data["cells"]) for data in road_data["clearance"].values()
        )
        blocked_cells = sum(obj["blocked_aisle_cells"] for obj in objects.values()) + sum(
            len(data["blocked_cells"]) for data in road_data["clearance"].values()
        )
        overlap_cells = sum(obj["affordance_conflict_cells"] for obj in objects.values()) + sum(
            len(data["affordance_conflict_cells"])
            for data in road_data["clearance"].values()
        )
        # RoadNetwork conflicts use continuous geometry for stable scoring;
        # sampled cells below remain an explanation layer and may vary by resolution.
        if continuous is not None and scene.clearance_bands:
            hard_sources = {
                item["source_id"]
                for item in continuous.get("debug", {}).get("aisle", [])
                if item["type"] == "clearance_blocked"
            }
            soft_sources = {
                item["source_id"]
                for item in continuous.get("debug", {}).get("aisle", [])
                if item["type"] == "road_affordance_conflict"
            }
            conflict_penalty = (
                len(hard_sources) + 0.5 * len(soft_sources)
            ) / max(1, len(scene.clearance_bands))
        else:
            # Hard occupied blockage is weighted more than soft affordance overlap.
            # The denominator stays at least 1 to keep empty/no-aisle scenes stable.
            conflict_penalty = (blocked_cells + 0.5 * overlap_cells) / max(1, aisle_cells)
        score = max(0.0, reachable_score * (1.0 - conflict_penalty))
        grid.mark_aisle_conflicts()
        if continuous is None:
            grid.mark_clearance_conflicts()

        return {
            "enabled": True,
            "backend": "grid",
            "score": round(score, 4),
            "objects": objects,
            "roads": {
                road_id: {"road_cells": len(cells)}
                for road_id, cells in road_data["roads"].items()
            },
            "clearance": {
                band_id: {
                    "clearance_cells": len(data["cells"]),
                    "blocked_cells": len(data["blocked_cells"]),
                    "affordance_conflict_cells": len(data["affordance_conflict_cells"]),
                }
                for band_id, data in road_data["clearance"].items()
            },
            "reachable_objects": reachable_objects,
            "unreachable_objects": unreachable_objects,
            "bottlenecks": bottlenecks,
            "debug": {
                "reachable": _matrix_counts(grid.debug_matrix("reachable")),
                "entries": _entry_matrix(grid, entries),
                "aisle": _matrix_counts(grid.debug_matrix("aisle_for")),
                "aisle_conflict": _matrix_counts(grid.debug_matrix("aisle_conflict_for")),
                "road": _matrix_counts(grid.debug_matrix("road_for")),
                "clearance": _matrix_counts(grid.debug_matrix("clearance_for")),
                "clearance_conflict": _matrix_counts(
                    grid.debug_matrix("clearance_conflict_for")
                ),
                "continuous_conflicts": (
                    continuous.get("debug", {}).get("aisle", [])
                    if continuous is not None
                    else []
                ),
            },
        }

    def _default_entries(self, grid: SpatialGridBackend) -> list[tuple[int, int]]:
        # MVP entrance assumption: circulation enters from the left boundary.
        return [(row, 0) for row in range(grid.n_rows)]

    def _entity_reachable(
        self,
        grid: SpatialGridBackend,
        entity: SpatialEntity,
    ) -> bool:
        # Reachability is tested in a one-cell halo around the object, because
        # occupied body cells themselves are intentionally not traversable.
        halo = entity.rect.expanded(
            left=grid.resolution,
            right=grid.resolution,
            top=grid.resolution,
            bottom=grid.resolution,
        )
        for row, col in grid.iter_indices_in_rect(halo):
            cell = grid.cells[row][col]
            if cell.reachable and entity.id not in cell.occupied_by:
                return True
        return False

    def _mark_entity_reserved_corridor(
        self,
        grid: SpatialGridBackend,
        entity: SpatialEntity,
        min_width: float,
        affordance_cells: set[tuple[int, int]],
    ) -> dict[str, set[tuple[int, int]]]:
        # MVP corridor = bbox halo. This is intentionally a sampled evaluation
        # reservation, not a geometric path/skeleton; polygon corridors come later.
        width = max(float(min_width), grid.resolution)
        halo = entity.rect.expanded(left=width, right=width, top=width, bottom=width)
        raw_cells = set(grid.iter_indices_in_rect(halo))
        if entity.footprint is not None:
            body_cells = set(grid.iter_indices_in_polygon(entity.footprint))
        else:
            body_cells = set(grid.iter_indices_in_rect(entity.rect))
        aisle_cells = raw_cells - body_cells
        blocked_cells = set()

        for row, col in aisle_cells:
            cell = grid.cells[row][col]
            blockers = cell.occupied_by - {entity.id}
            if blockers:
                blocked_cells.add((row, col))

        free_or_reachable_cells = {
            (row, col)
            for row, col in aisle_cells
            if not grid.cells[row][col].occupied_by or grid.cells[row][col].reachable
        }
        for row, col in free_or_reachable_cells:
            grid.cells[row][col].aisle_for.add(entity.id)

        # Affordance/aisle overlap is a soft conflict even if the cell is free:
        # the same sampled area is asked to serve two incompatible purposes.
        affordance_conflict_cells = aisle_cells & affordance_cells
        for row, col in affordance_conflict_cells:
            grid.cells[row][col].aisle_for.add(entity.id)
            grid.cells[row][col].aisle_conflict_for.add(entity.id)

        return {
            "aisle_cells": aisle_cells,
            "blocked_cells": blocked_cells,
            "affordance_conflict_cells": affordance_conflict_cells,
        }

    def _mark_scene_road_and_clearance_bands(
        self,
        grid: SpatialGridBackend,
        scene: SceneModel,
        affordance_cells: set[tuple[int, int]],
        continuous: dict | None = None,
    ) -> dict[str, dict]:
        # RoadBand/ClearanceBand are continuous geometry. This method only marks
        # their sampled cells so scoring/debug layers can explain conflicts.
        road_cells_by_id = {}
        clearance_data_by_id = {}

        for band in scene.road_bands:
            cells = set(grid.iter_indices_in_rect(band.rect))
            road_cells_by_id[band.id] = cells
            grid.mark_road(band.id, band.rect)

        for band in scene.clearance_bands:
            cells = set(grid.iter_indices_in_rect(band.rect))
            grid.mark_clearance(band.id, band.rect)
            if continuous is None:
                blocked_cells = {
                    (row, col)
                    for row, col in cells
                    if grid.cells[row][col].occupied_by
                }
                affordance_conflict_cells = cells & affordance_cells
                for row, col in blocked_cells | affordance_conflict_cells:
                    grid.cells[row][col].clearance_conflict_for.add(band.id)
            else:
                blocked_cells = set()
                affordance_conflict_cells = set()
            clearance_data_by_id[band.id] = {
                "cells": cells,
                "blocked_cells": blocked_cells,
                "affordance_conflict_cells": affordance_conflict_cells,
            }

        if continuous is not None:
            self._rasterize_continuous_clearance_conflicts(
                grid,
                continuous,
                clearance_data_by_id,
            )

        return {
            "roads": road_cells_by_id,
            "clearance": clearance_data_by_id,
        }

    def _rasterize_continuous_clearance_conflicts(
        self,
        grid: SpatialGridBackend,
        continuous: dict,
        clearance_data_by_id: dict[str, dict],
    ) -> None:
        for conflict in continuous.get("conflicts", []):
            if conflict.type not in {"clearance_blocked", "road_affordance_conflict"}:
                continue
            cells = sample_overlap_cells(
                grid,
                conflict.source_shape,
                conflict.target_shape,
            )
            if not cells:
                continue
            for row, col in cells:
                grid.cells[row][col].clearance_conflict_for.add(conflict.source_id)
            if conflict.source_id in clearance_data_by_id:
                key = (
                    "blocked_cells"
                    if conflict.type == "clearance_blocked"
                    else "affordance_conflict_cells"
                )
                clearance_data_by_id[conflict.source_id][key].update(cells)

    def _affordance_reference_cells(
        self,
        grid: SpatialGridBackend,
        scene: SceneModel,
        affordance_debug: dict | None,
    ) -> set[tuple[int, int]]:
        if affordance_debug is not None:
            cells = _matrix_positive_cells(affordance_debug.get("affordance", []))
            for row, col in cells:
                if 0 <= row < grid.n_rows and 0 <= col < grid.n_cols:
                    # Use a synthetic owner because report debug is count-only;
                    # aisle only needs to know that this sampled cell is claimed.
                    grid.cells[row][col].affordance_for.add("__affordance__")
            return cells

        cells: set[tuple[int, int]] = set()
        for entity in scene.entities:
            profile = resolve_affordance_profile(entity.type_id, entity.affordance)
            for edge in profile.usable_edges:
                depth = profile.depth_for(edge)
                if depth <= 0:
                    continue
                band = build_affordance_polygon(entity, edge, depth)
                band_cells = set(grid.iter_indices_in_polygon(band))
                cells.update(band_cells)
                grid.mark_affordance("__affordance__", band)
        return cells


def evaluate_spatial_access(
    scene: SceneModel,
    *,
    width: float,
    height: float,
    resolution: float = 50,
) -> dict:
    continuous = ContinuousConflictEvaluator().evaluate(scene)
    affordance = AffordanceEvaluator(
        width=width,
        height=height,
        resolution=resolution,
    ).evaluate(scene, continuous=continuous)
    aisle = AisleEvaluator(
        width=width,
        height=height,
        resolution=resolution,
    ).evaluate(scene, affordance_debug=affordance.get("debug"), continuous=continuous)
    return {
        "affordance": affordance,
        "aisle": aisle,
    }
