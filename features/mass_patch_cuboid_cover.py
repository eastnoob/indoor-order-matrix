"""Deterministic upright occupancy sampling for low-count MassPatch covers."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import math
from typing import Iterable

from .geometry_substitutes import MassPatch
from .geometry_views import _point_inside_closed_mesh
from .scene_contract import MeshGeometry3D


@dataclass(frozen=True)
class CuboidCoverConfig:
    """Sampling limits used to build and simplify one object geometry."""

    pitch: float = 0.1
    max_cells: int = 250_000
    max_patches: int = 128

    def __post_init__(self) -> None:
        """Validate finite sampling values before allocating a grid."""
        if not math.isfinite(float(self.pitch)) or float(self.pitch) <= 0.0:
            raise ValueError("pitch must be finite and positive")
        if isinstance(self.max_cells, bool) or int(self.max_cells) <= 0:
            raise ValueError("max_cells must be a positive integer")
        if isinstance(self.max_patches, bool) or int(self.max_patches) <= 0:
            raise ValueError("max_patches must be a positive integer")
        object.__setattr__(self, "pitch", float(self.pitch))
        object.__setattr__(self, "max_cells", int(self.max_cells))
        object.__setattr__(self, "max_patches", int(self.max_patches))


@dataclass(frozen=True)
class OccupancyGrid3D:
    """A finite world-coordinate grid of occupied and empty sample cells."""

    origin: tuple[float, float, float]
    pitch: float
    shape: tuple[int, int, int]
    occupied_cells: frozenset[tuple[int, int, int]]
    uncertain: bool = False
    source_mesh_id: str = ""

    @property
    def occupied_count(self) -> int:
        """Return the number of cells classified as physically occupied."""
        return len(self.occupied_cells)

    @property
    def cell_count(self) -> int:
        """Return the total number of cells in the bounded sample grid."""
        return self.shape[0] * self.shape[1] * self.shape[2]

    @property
    def empty_count(self) -> int:
        """Return the number of cells not classified as physically occupied."""
        return self.cell_count - self.occupied_count

    def cell_index(self, point: tuple[float, float, float]) -> tuple[int, int, int] | None:
        """Map a world point to its containing cell, or return None outside."""
        indices = tuple(
            int(math.floor((float(point[index]) - self.origin[index]) / self.pitch))
            for index in range(3)
        )
        if any(
            indices[index] < 0 or indices[index] >= self.shape[index]
            for index in range(3)
        ):
            return None
        return indices

    def is_occupied(self, point: tuple[float, float, float]) -> bool:
        """Return whether the cell containing a world point is occupied."""
        index = self.cell_index(point)
        return index in self.occupied_cells if index is not None else False

    def cell_center(self, index: tuple[int, int, int]) -> tuple[float, float, float]:
        """Return the world-coordinate center of one grid cell."""
        return tuple(
            self.origin[axis] + (index[axis] + 0.5) * self.pitch
            for axis in range(3)
        )


def _mesh_bounds(mesh: MeshGeometry3D) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return finite minimum and maximum coordinates for a source mesh."""
    if not mesh.vertices:
        raise ValueError("mesh must contain vertices")
    minimum = tuple(min(float(vertex[axis]) for vertex in mesh.vertices) for axis in range(3))
    maximum = tuple(max(float(vertex[axis]) for vertex in mesh.vertices) for axis in range(3))
    if any(not math.isfinite(value) for value in (*minimum, *maximum)):
        raise ValueError("mesh vertices must be finite")
    return minimum, maximum


def _grid_shape(
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    pitch: float,
    max_cells: int,
) -> tuple[int, int, int]:
    """Compute a bounded cell shape without silently exceeding the budget."""
    shape = tuple(
        max(1, int(math.ceil((maximum[axis] - minimum[axis]) / pitch)))
        for axis in range(3)
    )
    cell_count = shape[0] * shape[1] * shape[2]
    if cell_count > max_cells:
        raise ValueError(
            f"occupancy grid requires {cell_count} cells, exceeding max_cells={max_cells}"
        )
    return shape


def _all_cell_indices(shape: tuple[int, int, int]) -> Iterable[tuple[int, int, int]]:
    """Yield deterministic integer coordinates for a finite grid."""
    for z in range(shape[2]):
        for y in range(shape[1]):
            for x in range(shape[0]):
                yield (x, y, z)


def build_upright_occupancy(
    mesh: MeshGeometry3D,
    config: CuboidCoverConfig,
) -> OccupancyGrid3D:
    """Sample a closed source mesh into an upright world-coordinate grid."""
    if not isinstance(mesh, MeshGeometry3D):
        raise TypeError("mesh must be a MeshGeometry3D")
    minimum, maximum = _mesh_bounds(mesh)
    shape = _grid_shape(minimum, maximum, config.pitch, config.max_cells)
    occupied: set[tuple[int, int, int]] = set()
    uncertain = mesh.is_closed is not True or mesh.is_manifold is not True

    # Empty cells are intentionally sampled and retained: they are the only
    # inexpensive representation that can preserve chair-leg and hollow gaps.
    for index in _all_cell_indices(shape):
        center = tuple(
            minimum[axis] + (index[axis] + 0.5) * config.pitch
            for axis in range(3)
        )
        if not uncertain and _point_inside_closed_mesh(
            _mass_patch_for_sampling(mesh),
            center,
        ):
            occupied.add(index)
    return OccupancyGrid3D(
        origin=minimum,
        pitch=config.pitch,
        shape=shape,
        occupied_cells=frozenset(occupied),
        uncertain=uncertain,
        source_mesh_id=mesh.id,
    )


def _mass_patch_for_sampling(mesh: MeshGeometry3D) -> MassPatch:
    """Create a minimal local patch for the existing point classifier."""
    return MassPatch(
        id=f"sampling:{mesh.id}",
        source_geometry_id=mesh.id,
        vertices=tuple(mesh.vertices),
        triangle_indices=tuple(mesh.triangle_indices),
        is_manifold=mesh.is_manifold,
        is_closed=mesh.is_closed,
        provenance={"method": "occupancy_sampling"},
    )


def cuboid_from_grid_bounds(
    grid: OccupancyGrid3D,
    bounds: tuple[int, int, int, int, int, int],
) -> MassPatch:
    """Build one closed upright cuboid from inclusive grid bounds."""
    x0, x1, y0, y1, z0, z1 = bounds
    if not (0 <= x0 <= x1 < grid.shape[0]):
        raise ValueError("invalid x bounds")
    if not (0 <= y0 <= y1 < grid.shape[1]):
        raise ValueError("invalid y bounds")
    if not (0 <= z0 <= z1 < grid.shape[2]):
        raise ValueError("invalid z bounds")
    minimum = tuple(
        grid.origin[axis] + lower * grid.pitch
        for axis, lower in enumerate((x0, y0, z0))
    )
    maximum = tuple(
        grid.origin[axis] + (upper + 1) * grid.pitch
        for axis, upper in enumerate((x1, y1, z1))
    )
    vertices = (
        (minimum[0], minimum[1], minimum[2]),
        (maximum[0], minimum[1], minimum[2]),
        (maximum[0], maximum[1], minimum[2]),
        (minimum[0], maximum[1], minimum[2]),
        (minimum[0], minimum[1], maximum[2]),
        (maximum[0], minimum[1], maximum[2]),
        (maximum[0], maximum[1], maximum[2]),
        (minimum[0], maximum[1], maximum[2]),
    )
    triangles = (
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    )
    return MassPatch(
        id=f"{grid.source_mesh_id}:cuboid:{x0},{x1},{y0},{y1},{z0},{z1}",
        source_geometry_id=grid.source_mesh_id,
        vertices=vertices,
        triangle_indices=triangles,
        is_manifold=True,
        is_closed=True,
        provenance={
            "method": "upright_occupancy_cuboid",
            "source_mesh_id": grid.source_mesh_id,
            "grid_origin": grid.origin,
            "grid_pitch": grid.pitch,
            "grid_bounds": bounds,
        },
    )


def _bounds_cells(
    bounds: tuple[int, int, int, int, int, int],
) -> frozenset[tuple[int, int, int]]:
    """Return all integer cells inside inclusive cuboid bounds."""
    x0, x1, y0, y1, z0, z1 = bounds
    return frozenset(
        (x, y, z)
        for z in range(z0, z1 + 1)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
    )


def _occupied_components(
    occupied: frozenset[tuple[int, int, int]],
) -> tuple[frozenset[tuple[int, int, int]], ...]:
    """Split occupied cells into deterministic six-neighbor components."""
    remaining = set(occupied)
    components = []
    while remaining:
        seed = min(remaining)
        queue = deque([seed])
        remaining.remove(seed)
        component = {seed}
        while queue:
            cell = queue.popleft()
            for axis in range(3):
                for direction in (-1, 1):
                    neighbor = list(cell)
                    neighbor[axis] += direction
                    neighbor_tuple = tuple(neighbor)
                    if neighbor_tuple in remaining:
                        remaining.remove(neighbor_tuple)
                        component.add(neighbor_tuple)
                        queue.append(neighbor_tuple)
        components.append(frozenset(component))
    return tuple(sorted(components, key=lambda cells: min(cells)))


def _cells_bounds(
    cells: frozenset[tuple[int, int, int]],
) -> tuple[int, int, int, int, int, int]:
    """Return inclusive bounds around a non-empty cell set."""
    return (
        min(cell[0] for cell in cells),
        max(cell[0] for cell in cells),
        min(cell[1] for cell in cells),
        max(cell[1] for cell in cells),
        min(cell[2] for cell in cells),
        max(cell[2] for cell in cells),
    )


def _bounds_volume(bounds: tuple[int, int, int, int, int, int]) -> int:
    """Return the number of integer cells inside inclusive bounds."""
    return (
        (bounds[1] - bounds[0] + 1)
        * (bounds[3] - bounds[2] + 1)
        * (bounds[5] - bounds[4] + 1)
    )


def _best_component_split(
    cells: frozenset[tuple[int, int, int]],
    bounds: tuple[int, int, int, int, int, int],
) -> tuple[frozenset[tuple[int, int, int]], frozenset[tuple[int, int, int]]] | None:
    """Choose the split that minimizes the two resulting occupied envelopes."""
    best = None
    for axis in range(3):
        lower = bounds[axis * 2]
        upper = bounds[axis * 2 + 1]
        for cut in range(lower, upper):
            first = frozenset(cell for cell in cells if cell[axis] <= cut)
            second = frozenset(cell for cell in cells if cell[axis] > cut)
            if not first or not second:
                continue
            first_bounds = _cells_bounds(first)
            second_bounds = _cells_bounds(second)
            key = (
                _bounds_volume(first_bounds) + _bounds_volume(second_bounds),
                max(_bounds_volume(first_bounds), _bounds_volume(second_bounds)),
                axis,
                cut,
            )
            if best is None or key < best[0]:
                best = (key, first, second)
    return None if best is None else (best[1], best[2])


def _decompose_component(
    cells: frozenset[tuple[int, int, int]],
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    """Recursively partition one occupied component into compact boxes."""
    bounds = _cells_bounds(cells)
    if _bounds_volume(bounds) == len(cells):
        return (bounds,)
    split = _best_component_split(cells, bounds)
    if split is None:
        return tuple(
            (
                cell[0], cell[0],
                cell[1], cell[1],
                cell[2], cell[2],
            )
            for cell in sorted(cells)
        )
    return _decompose_component(split[0]) + _decompose_component(split[1])


def _component_aabb_candidates(
    mesh: MeshGeometry3D,
) -> tuple[MassPatch, ...]:
    """Build one upright AABB candidate for each factual mesh component."""
    import numpy as np
    import trimesh

    valid_faces = []
    for face in mesh.triangle_indices:
        first, second, third = (mesh.vertices[index] for index in face)
        edge_one = tuple(second[axis] - first[axis] for axis in range(3))
        edge_two = tuple(third[axis] - first[axis] for axis in range(3))
        cross = (
            edge_one[1] * edge_two[2] - edge_one[2] * edge_two[1],
            edge_one[2] * edge_two[0] - edge_one[0] * edge_two[2],
            edge_one[0] * edge_two[1] - edge_one[1] * edge_two[0],
        )
        if sum(value * value for value in cross) > 0.0:
            valid_faces.append(face)
    source = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=float),
        faces=np.asarray(valid_faces, dtype=int),
        process=False,
    )
    source.merge_vertices()
    components = list(source.split(only_watertight=False))
    components.sort(
        key=lambda component: (
            tuple(float(value) for value in component.bounds[0]),
            tuple(float(value) for value in component.bounds[1]),
        )
    )
    candidates = []
    for index, component in enumerate(components):
        minimum = tuple(float(value) for value in component.bounds[0])
        maximum = tuple(float(value) for value in component.bounds[1])
        candidates.append(
            _box_patch_from_coordinates(
                mesh.id,
                minimum,
                maximum,
                {
                    "method": "component_upright_aabb",
                    "source_mesh_id": mesh.id,
                    "source_component_index": index,
                },
            )
        )
    return tuple(candidates)


def maximal_upright_cuboid_candidates(
    grid: OccupancyGrid3D,
    config: CuboidCoverConfig,
) -> tuple[MassPatch, ...]:
    """Enumerate deterministic occupied-cell cuboid candidates."""
    if grid.uncertain or not grid.occupied_cells:
        return ()
    bounds_set = {
        bounds
        for component in _occupied_components(grid.occupied_cells)
        for bounds in _decompose_component(component)
    }
    ordered_bounds = sorted(bounds_set, key=lambda bounds: (-_bounds_volume(bounds), bounds))
    return tuple(
        cuboid_from_grid_bounds(grid, bounds)
        for bounds in ordered_bounds
        if len(_bounds_cells(bounds)) > 0
    )


def greedy_cuboid_cover(
    grid: OccupancyGrid3D,
    config: CuboidCoverConfig,
) -> tuple[MassPatch, ...]:
    """Select a bounded low-count cover over occupied grid cells."""
    candidates = maximal_upright_cuboid_candidates(grid, config)
    remaining = set(grid.occupied_cells)
    selected = []
    while remaining and candidates and len(selected) < config.max_patches:
        ranked = []
        for candidate in candidates:
            bounds = tuple(candidate.provenance["grid_bounds"])
            covered = _bounds_cells(bounds)
            newly_covered = len(covered & remaining)
            if newly_covered:
                ranked.append(
                    (
                        -newly_covered,
                        -len(covered),
                        bounds,
                        candidate,
                    )
                )
        if not ranked:
            break
        ranked.sort(key=lambda item: item[:3])
        chosen = ranked[0][3]
        selected.append(chosen)
        remaining.difference_update(
            _bounds_cells(tuple(chosen.provenance["grid_bounds"]))
        )
    return tuple(selected)


def cuboid_collection_from_mesh(
    mesh: MeshGeometry3D,
    config: CuboidCoverConfig,
) -> tuple[MassPatch, ...]:
    """Build an initial low-count cuboid collection for one source mesh."""
    component_candidates = _component_aabb_candidates(mesh)
    # Factual source components are the safest low-count decomposition for
    # ordinary furniture parts such as a seat, back, or separate leg.
    if component_candidates:
        return component_candidates[: config.max_patches]
    grid = build_upright_occupancy(mesh, config)
    if grid.uncertain:
        return ()
    return greedy_cuboid_cover(grid, config)


def _box_patch_from_coordinates(
    source_id: str,
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    provenance: dict[str, object],
) -> MassPatch:
    """Build one closed axis-aligned patch from coordinate bounds."""
    vertices = (
        (minimum[0], minimum[1], minimum[2]),
        (maximum[0], minimum[1], minimum[2]),
        (maximum[0], maximum[1], minimum[2]),
        (minimum[0], maximum[1], minimum[2]),
        (minimum[0], minimum[1], maximum[2]),
        (maximum[0], minimum[1], maximum[2]),
        (maximum[0], maximum[1], maximum[2]),
        (minimum[0], maximum[1], maximum[2]),
    )
    triangles = (
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    )
    return MassPatch(
        id=f"{source_id}:split:{minimum}:{maximum}",
        source_geometry_id=source_id,
        vertices=vertices,
        triangle_indices=triangles,
        is_manifold=True,
        is_closed=True,
        provenance=provenance,
    )


def split_cuboid_patch(
    patch: MassPatch,
) -> tuple[MassPatch, MassPatch] | None:
    """Split an axis-aligned cuboid along its longest dimension."""
    if len(patch.vertices) < 8:
        return None
    minimum = tuple(
        min(float(vertex[axis]) for vertex in patch.vertices)
        for axis in range(3)
    )
    maximum = tuple(
        max(float(vertex[axis]) for vertex in patch.vertices)
        for axis in range(3)
    )
    axis = max(
        range(3),
        key=lambda index: (
            maximum[index] - minimum[index],
            -index,
        ),
    )
    midpoint = (minimum[axis] + maximum[axis]) / 2.0
    if math.isclose(midpoint, minimum[axis]) or math.isclose(midpoint, maximum[axis]):
        return None
    first_maximum = list(maximum)
    first_maximum[axis] = midpoint
    second_minimum = list(minimum)
    second_minimum[axis] = midpoint
    base_provenance = {
        **dict(patch.provenance),
        "method": "upright_cuboid_split",
        "split_axis": axis,
        "split_coordinate": midpoint,
    }
    return (
        _box_patch_from_coordinates(
            patch.source_geometry_id,
            minimum,
            tuple(first_maximum),
            {**base_provenance, "split_side": "lower"},
        ),
        _box_patch_from_coordinates(
            patch.source_geometry_id,
            tuple(second_minimum),
            maximum,
            {**base_provenance, "split_side": "upper"},
        ),
    )


__all__ = [
    "CuboidCoverConfig",
    "OccupancyGrid3D",
    "build_upright_occupancy",
    "cuboid_from_grid_bounds",
    "maximal_upright_cuboid_candidates",
    "greedy_cuboid_cover",
    "cuboid_collection_from_mesh",
    "split_cuboid_patch",
]
