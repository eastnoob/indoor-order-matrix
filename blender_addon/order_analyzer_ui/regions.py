"""Strict, plugin-owned persistence for confirmed analysis regions."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from collections.abc import Iterable, Mapping


SCHEMA_VERSION = 1
_STATUSES = {"preview", "confirmed", "historical", "stale", "recheck", "removed"}


def _canonical(value: object) -> str:
    """Encode JSON facts deterministically for a stable manifest digest."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Mapping[str, object]) -> str:
    """Hash manifest facts without trusting Blender object identity."""
    body = {key: value[key] for key in value if key != "digest"}
    return sha256(_canonical(body).encode("utf-8")).hexdigest()


def _ring(raw: Iterable[Iterable[float]], field: str) -> tuple[tuple[float, float], ...]:
    """Validate one closed finite XY ring and preserve its authored order."""
    points = []
    for point in raw:
        point = tuple(point)
        if len(point) != 2 or not all(type(item) in (int, float) and math.isfinite(float(item)) for item in point):
            raise ValueError(f"{field} must contain finite XY points")
        points.append((float(point[0]), float(point[1])))
    if len(points) < 4 or points[0] != points[-1]:
        raise ValueError(f"{field} must be a closed ring")
    return tuple(points)


def _rings(raw: Iterable[Iterable[Iterable[float]]], field: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Validate a polygon shell and any holes."""
    rings = tuple(_ring(item, f"{field}[{index}]") for index, item in enumerate(raw))
    if not rings:
        raise ValueError(f"{field} must contain one shell")
    return rings


def _plain_rings(rings):
    """Convert validated rings to JSON lists."""
    return [[[float(x), float(y)] for x, y in ring] for ring in rings]


def _vector3(value, field: str) -> tuple[float, float, float]:
    """Validate one finite world-space origin vector used by the GPU overlay."""
    point = tuple(value)
    if len(point) != 3 or not all(type(item) in (int, float) and math.isfinite(float(item)) for item in point):
        raise ValueError(f"{field} must contain three finite coordinates")
    return tuple(float(item) for item in point)


def _basis3(value, field: str) -> tuple[tuple[float, float, float], ...]:
    """Validate a right-handed orthonormal plane basis without requiring Blender."""
    basis = tuple(_vector3(axis, f"{field}[{index}]") for index, axis in enumerate(value))
    if len(basis) != 3:
        raise ValueError(f"{field} must contain three axes")
    for axis in basis:
        if not math.isclose(sum(component * component for component in axis), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"{field} axes must be unit length")
    for first in range(3):
        for second in range(first + 1, 3):
            if not math.isclose(sum(basis[first][index] * basis[second][index] for index in range(3)), 0.0,
                                rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"{field} must be orthogonal")
    x_axis, y_axis, normal = basis
    determinant = sum(normal[index] * (
        x_axis[(index + 1) % 3] * y_axis[(index + 2) % 3]
        - x_axis[(index + 2) % 3] * y_axis[(index + 1) % 3]) for index in range(3))
    if not math.isclose(determinant, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"{field} must be right-handed")
    return basis


def _plain_vector(value):
    """Convert one validated vector to JSON-compatible scalar values."""
    return [float(item) for item in value]


def _plain_basis(value):
    """Convert one validated basis to JSON-compatible nested lists."""
    return [_plain_vector(axis) for axis in value]


def build_region_record(*, region_id: str, name: str, storey_ref: str | None, plane_uuid: str,
                        plane_revision: int, source_id: str | None, geometry_refs: Iterable[str],
                        outline, holes=(), status: str = "confirmed", confirmation: Mapping | None = None,
                        source_revision: str | None = None, support_source_id: str | None = None,
                        selected_wall_refs: Iterable[str] = (),
                        plane_origin=(0.0, 0.0, 0.0), plane_binding=None, space_binding=None,
                        plane_basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))) -> dict[str, object]:
    """Build one immutable-friendly region record from trusted plain facts."""
    if not isinstance(region_id, str) or not region_id.strip():
        raise ValueError("region_id is required")
    if not isinstance(name, str):
        raise ValueError("name must be text")
    if not isinstance(plane_uuid, str) or not plane_uuid.strip():
        raise ValueError("plane_uuid is required")
    if type(plane_revision) is not int or plane_revision < 1:
        raise ValueError("plane_revision must be positive")
    if status not in _STATUSES:
        raise ValueError("unknown region status")
    shell = _ring(outline[0], "outline") if isinstance(outline, (tuple, list)) and outline and not isinstance(outline[0][0], (tuple, list)) else None
    all_rings = _rings(outline if shell is None else (shell,), "outline")
    hole_rings = _rings(holes, "holes") if holes else ()
    origin = _vector3(plane_origin, "plane_origin")
    basis = _basis3(plane_basis, "plane_basis")
    selected_refs = tuple(sorted(str(item) for item in selected_wall_refs))
    if (len(selected_refs) != len(set(selected_refs))
            or any(not item.startswith("ifc-object:") or not item.removeprefix("ifc-object:").strip()
                   for item in selected_refs)):
        raise ValueError("selected_wall_refs must contain unique canonical IFC object references")
    composition = {}
    if plane_binding is not None or space_binding is not None:
        from adapters import blender_analysis_result_wire as wire
        composition = {key: wire.plain(value) for key, value in (
            ("plane_binding", plane_binding), ("space_binding", space_binding)) if value is not None}
        observed_project = (plane_binding or space_binding)["project_global_id"]
        wire.validate_compositions(composition, {"project_source_identity": {"project_global_id": observed_project},
            "plane_uuid": plane_uuid, "plane_revision": plane_revision, "domain_identity": {"source_id": source_id}})
        if space_binding is not None and space_binding["storey_ref"] != storey_ref:
            raise ValueError("space composition storey differs from Region")
    return {
        "region_id": region_id,
        "name": name,
        "storey_ref": storey_ref,
        "plane_uuid": plane_uuid,
        "plane_revision": plane_revision,
        "plane_origin": _plain_vector(origin),
        "plane_basis": _plain_basis(basis),
        "source_id": source_id,
        "geometry_refs": tuple(str(item) for item in geometry_refs),
        "outline": _plain_rings(all_rings),
        "holes": _plain_rings(hole_rings),
        "source_revision": source_revision,
        "support_source_id": support_source_id,
        "selected_wall_refs": selected_refs,
        "status": status,
        "confirmation": dict(confirmation or {}),
        **composition,
    }


def _record_plain(record: Mapping[str, object]) -> dict[str, object]:
    """Validate and normalize a record before persistence or comparison."""
    required = {"region_id", "name", "plane_uuid", "plane_revision", "outline", "holes", "status"}
    if not required <= set(record):
        raise ValueError("region record is missing required fields")
    normalized = build_region_record(
        region_id=str(record["region_id"]), name=str(record["name"]), storey_ref=record.get("storey_ref"),
        plane_uuid=str(record["plane_uuid"]), plane_revision=record["plane_revision"],
        source_id=record.get("source_id"), geometry_refs=record.get("geometry_refs", ()),
        outline=record["outline"], holes=record.get("holes", ()), status=str(record["status"]),
        confirmation=record.get("confirmation", {}), source_revision=record.get("source_revision"),
        support_source_id=record.get("support_source_id"),
        selected_wall_refs=record.get("selected_wall_refs", ()),
        plane_origin=record.get("plane_origin", (0.0, 0.0, 0.0)),
        plane_binding=record.get("plane_binding"), space_binding=record.get("space_binding"),
        plane_basis=record.get("plane_basis", ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))),
    )
    return normalized


def encode_manifest(records: Iterable[Mapping[str, object]], *, active_region_id: str | None = None,
                    storey_ref: str | None = None) -> str:
    """Serialize region records with a manifest-level integrity digest."""
    body = {"schema_version": SCHEMA_VERSION, "active_region_id": active_region_id,
            "storey_ref": storey_ref, "records": [_record_plain(item) for item in records]}
    body["digest"] = _digest(body)
    return _canonical(body)


def decode_manifest(text_body: str) -> dict[str, object]:
    """Validate a saved region manifest and expose it as display-only history."""
    if not isinstance(text_body, str):
        raise TypeError("region manifest must be text")
    try:
        raw = json.loads(text_body)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid region manifest JSON") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported region manifest schema")
    if raw.get("digest") != _digest(raw):
        raise ValueError("region manifest digest mismatch")
    records = []
    for item in raw.get("records", ()):
        record = _record_plain(item)
        if record["status"] in {"confirmed", "preview"}:
            record["status"] = "historical"
        if record.get("plane_binding") is not None or record.get("space_binding") is not None:
            record["status"] = "recheck"
            record["review"] = "requires_recheck"
        record["confirmation"] = {}
        records.append(record)
    return {"schema_version": SCHEMA_VERSION, "active_region_id": raw.get("active_region_id"),
            "storey_ref": raw.get("storey_ref"), "records": records, "digest": raw["digest"]}


def upsert_record(records: Iterable[Mapping[str, object]], record: Mapping[str, object]):
    """Replace a matching source/outline record or append a new one."""
    incoming = _record_plain(record)
    existing = [_record_plain(item) for item in records]
    key = (incoming.get("source_id"), incoming.get("storey_ref"), incoming["plane_uuid"],
           incoming["selected_wall_refs"], incoming["outline"], incoming["holes"])
    for index, item in enumerate(existing):
        item_key = (item.get("source_id"), item.get("storey_ref"), item["plane_uuid"],
                    item["selected_wall_refs"], item["outline"], item["holes"])
        if key == item_key:
            incoming["region_id"] = item["region_id"]
            existing[index] = incoming
            return tuple(existing), item["region_id"]
    existing.append(incoming)
    return tuple(existing), incoming["region_id"]


def remove_record(records: Iterable[Mapping[str, object]], region_id: str):
    """Remove one display record while leaving other region history untouched."""
    return tuple(item for item in records if item.get("region_id") != region_id)

