"""Tests for union semantics over MassPatch records owned by one object."""

from __future__ import annotations

from ..features.geometry_substitutes import mass_patch_from_mesh
from ..features.mass_patch_collection import (
    collection_occludes,
    collection_overlap_report,
    merge_vertical_intervals,
    union_plan_geometry,
    vertical_intervals_at_collection,
)
from .test_geometry_substitutes import _box_mesh


def _box_patch(
    *,
    patch_id: str,
    offset_x: float = 0.0,
    top: float = 1.0,
) -> object:
    """Build one translated box patch for collection tests."""
    mesh = _box_mesh(mesh_id=patch_id, top=top)
    vertices = tuple(
        (x + offset_x, y, z)
        for x, y, z in mesh.vertices
    )
    return mass_patch_from_mesh(
        mesh.__class__(
            **{
                **mesh.__dict__,
                "vertices": vertices,
            }
        )
    )


def test_plan_union_counts_overlapping_boxes_once():
    """Overlapping patch footprints contribute one occupied plan union."""
    patches = (
        _box_patch(patch_id="left"),
        _box_patch(patch_id="right", offset_x=1.0),
    )

    geometry = union_plan_geometry(patches)

    assert geometry is not None
    assert geometry.area == 6.0


def test_height_union_merges_overlapping_intervals():
    """Overlapping vertical spans are returned as one occupied interval."""
    assert merge_vertical_intervals(((0.0, 1.0), (0.8, 2.0))) == ((0.0, 2.0),)


def test_collection_height_query_merges_patch_intervals():
    """A shared plan point sees the union of the member patch heights."""
    patches = (
        _box_patch(patch_id="low", top=1.0),
        _box_patch(patch_id="high", top=2.0),
    )

    result = vertical_intervals_at_collection(patches, (1.0, 1.0))

    assert result.intervals == ((0.0, 2.0),)


def test_collection_occlusion_is_boolean():
    """Duplicate member hits do not turn boolean occlusion into a count."""
    patches = (
        _box_patch(patch_id="left"),
        _box_patch(patch_id="right", offset_x=1.0),
    )

    assert collection_occludes(patches, {"point": (1.5, 1.0)}) is True


def test_overlap_report_keeps_overlap_separate_from_union_area():
    """Overlap diagnostics expose double coverage without changing union area."""
    patches = (
        _box_patch(patch_id="left"),
        _box_patch(patch_id="right", offset_x=1.0),
    )

    report = collection_overlap_report(patches)

    assert report["patch_count"] == 2
    assert report["overlap_pair_count"] == 1
    assert report["union_plan_area"] == 6.0
    assert report["member_plan_area_sum"] == 8.0
