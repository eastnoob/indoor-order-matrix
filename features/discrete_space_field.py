"""Read conditional v1 eye-plane evidence without generating geometry or fields."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath


def _check(condition: bool, message: str) -> None:
    """Reject incompatible evidence rather than substituting an empty result."""
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    """Require a finite number while keeping booleans distinct from numbers."""
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    _check(finite, f"Invalid {label}")
    return value


def _reject_constant(value: str) -> None:
    """Reject JSON extensions that would carry nonfinite evidence."""
    raise ValueError(f"Nonfinite JSON constant: {value}")


def _json_float(value: str) -> float:
    """Reject a finite-looking JSON literal if conversion overflows to infinity."""
    return _number(float(value), "JSON float")


def _json(payload: bytes) -> dict:
    """Decode a UTF-8 object, also rejecting overflowing JSON float literals."""
    result = json.loads(
        payload.decode("utf-8"), parse_constant=_reject_constant,
        parse_float=_json_float,
    )
    _check(isinstance(result, dict), "Expected a JSON object")
    return result


def _reference(reference: dict) -> None:
    """Check recorded fingerprint structure without opening external sources."""
    _check(isinstance(reference, dict), "Invalid file reference")
    _check(isinstance(reference["path"], str) and bool(reference["path"]), "Missing reference path")
    _check(type(reference["bytes"]) is int and reference["bytes"] >= 0, "Invalid reference bytes")
    digest = reference["sha256"]
    _check(isinstance(digest, str) and len(digest) == 64
           and all(c in "0123456789abcdef" for c in digest), "Invalid reference SHA-256")


def _payload(package: Path, manifest: dict, filename: str) -> tuple[dict, dict]:
    """Verify one fixed sibling payload without following a manifest path."""
    entries = [r for r in manifest["artifacts"]
               if PurePosixPath(r["path"].replace("\\", "/")).name == filename]
    _check(len(entries) == 1, f"Expected one manifest entry for {filename}")
    reference = entries[0]
    _reference(reference)
    recorded = PurePosixPath(reference["path"].replace("\\", "/"))
    _check(not recorded.is_absolute() and ".." not in recorded.parts
           and ":" not in reference["path"], f"Invalid package reference: {filename}")
    # The historical paths remain provenance; only the supplied directory is read.
    raw = (package / filename).read_bytes()
    _check(len(raw) == reference["bytes"]
           and hashlib.sha256(raw).hexdigest() == reference["sha256"],
           f"Payload fingerprint mismatch: {filename}")
    return _json(raw), reference


def _domain_bounds(geometry: dict) -> tuple[float, float, float, float]:
    """Read coordinate bounds solely to check the serialized lattice arithmetic."""
    _check(geometry["type"] in ("Polygon", "MultiPolygon"), "Unsupported domain coordinate layout")
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    points = [point for polygon in polygons for ring in polygon for point in ring]
    _check(bool(points), "Missing domain coordinates")
    for point in points:
        _check(isinstance(point, list) and len(point) == 2, "Invalid domain XY coordinate")
        _number(point[0], "domain x")
        _number(point[1], "domain y")
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def _validate_variant(variant: dict, field: dict, source_ids: set[str], bounds: tuple) -> None:
    """Check point states and indices without recomputing geometric membership."""
    spacing = _number(variant["spacing_m"], "spacing_m")
    _check(spacing > 0, "spacing_m must be positive")
    offset = variant["origin_offset_m"]
    _check(isinstance(offset, list) and len(offset) == 2, "Invalid origin_offset_m")
    for value in offset:
        _number(value, "origin offset")
    samples = variant["samples"]
    _check(isinstance(samples, list) and bool(samples), "Missing indexed samples")
    seen = set()
    states = Counter()
    in_domain = 0
    for sample in samples:
        indices = sample["cell_i"], sample["cell_j"]
        _check(all(type(i) is int for i in indices), "Lattice indices must be integers")
        _check(indices not in seen, "Duplicate lattice index")
        seen.add(indices)
        for axis, key in enumerate(("x_m", "y_m")):
            value = _number(sample[key], key)
            step = (indices[axis] + 0.5) * spacing
            expected = _number(bounds[axis] + offset[axis] + step, "lattice coordinate")
            # Eight ULPs of the operands cover multiplication/addition rounding;
            # this checks serialization arithmetic, never occupancy or geometry.
            roundoff = 8 * sum(math.ulp(v) for v in (bounds[axis], offset[axis], step, expected))
            _check(abs(value - expected) <= roundoff, f"Inconsistent lattice coordinate: {key}")
            _check(bounds[axis] <= value <= bounds[axis + 2], "Sample outside lattice extent")
        _check(_number(sample["world_z_m"], "sample height") == field["primary_plane_world_z_m"],
               "Sample height mismatch")
        for key in ("domain_mask", "qualified_occupied_subset_mask", "unresolved_source_support_mask",
                    "section_boundary_ambiguity_mask", "unknown_mask"):
            _check(type(sample[key]) is bool, f"Invalid boolean mask: {key}")
        ids = sample["unresolved_source_ids"]
        _check(isinstance(ids, list) and all(isinstance(sid, str) and sid in source_ids for sid in ids)
               and len(ids) == len(set(ids)), "Invalid unresolved source IDs")
        _check(sample["unresolved_source_support_mask"] == bool(ids), "Unresolved support/IDs mismatch")
        value = sample["occupancy_value"]
        _check(value is None or type(value) is bool, "Occupancy must be true/false/null")
        inside = sample["domain_mask"]
        positive = sample["qualified_occupied_subset_mask"]
        _check(not positive or field["raw_qualified_occupied_area_m2"] > 0, "Positive sample without raw subset")
        ambiguity = bool(ids) or sample["section_boundary_ambiguity_mask"]
        expected = True if positive else None if not inside or ambiguity else False
        _check(value is expected, "Inconsistent tri-state occupancy")
        _check(inside or not (positive or ambiguity), "Outside sample carries interior evidence")
        _check(sample["unknown_mask"] is (inside and value is None), "Unknown mask mismatch")
        free = None if value is None else not value
        _check(sample["known_free_under_qualification"] is free, "Conditional empty mask mismatch")
        state = ("outside_domain" if not inside else "established_occupied" if positive
                 else "unknown" if value is None else "established_empty_under_qualification")
        _check(sample["status"] == state, "Sample status mismatch")
        states[state] += 1
        in_domain += inside
        boundary_distance = sample["distance_to_domain_boundary_m"]
        subset_distance = sample["distance_to_raw_qualified_occupied_subset_m"]
        for distance in (boundary_distance, subset_distance):
            if distance is not None:
                _check(_number(distance, "distance") >= 0, "Negative distance")
        _check((boundary_distance is not None) == inside, "Domain distance availability mismatch")
        _check((subset_distance is not None) == (inside and field["raw_qualified_occupied_area_m2"] > 0),
               "Raw subset distance availability mismatch")
        _check(sample["complete_physical_clearance_m"] is None, "Complete physical clearance is unavailable")
    _check(type(variant["sample_count"]) is int and variant["sample_count"] == len(samples), "Sample count mismatch")
    _check(type(variant["domain_sample_count"]) is int and variant["domain_sample_count"] == in_domain,
           "Domain sample count mismatch")
    _check(isinstance(variant["status_counts"], dict)
           and all(type(count) is int for count in variant["status_counts"].values())
           and variant["status_counts"] == dict(states), "Status counts mismatch")


def _validate_field(field: dict, sections: dict) -> None:
    """Validate the v1 qualification boundary and preserve source evidence verbatim."""
    _check(field["schema"] == "b3-primary-eye-plane-discrete-field/v1", "Unsupported field schema")
    _check(sections["schema"] == "b3-primary-eye-source-sections/v1", "Unsupported source-section schema")
    for key in ("status", "plane_rule"):
        _check(isinstance(field[key], str) and bool(field[key]), f"Missing {key}")
    _check(field["units"] == "m" and field["frame"]["units"] == "m", "Expected metre frame")
    plane = field["frame"]["plane"]
    _check(isinstance(plane["name"], str) and bool(plane["name"]), "Missing frame name")
    for vector in [plane["origin"], *plane["basis"]]:
        _check(isinstance(vector, list) and len(vector) == 3, "Invalid frame vector")
        for value in vector:
            _number(value, "frame coordinate")
    _check(len(plane["basis"]) == 3, "Invalid frame basis")
    # Historical scope cut and primary query height are separate metadata.
    for key in ("datum_m", "cut_height_m"):
        _number(field["frame"][key], key)
    datum = field["floor_datum"]
    _check(type(field["storey_step"]) is int and field["storey_step"] > 0
           and datum["storey_step"] == field["storey_step"], "Storey binding mismatch")
    for key in ("source", "reference", "storey_global_id"):
        _check(isinstance(datum[key], str) and bool(datum[key]), f"Missing datum {key}")
    height = _number(field["primary_plane_world_z_m"], "primary height")
    _check(_number(datum["value_m"], "floor datum") == 0.0
           and _number(field["eye_height_offset_m"], "eye offset") == 1.6
           and height == 1.6 and sections["primary_plane_world_z_m"] == height, "Eye-plane height mismatch")
    for key in ("source_revision", "frame_id", "request_id", "candidate_identity"):
        identity = field["scope_binding"][key]
        _check(isinstance(identity, str) and len(identity) == 64
               and all(c in "0123456789abcdef" for c in identity), f"Invalid scope {key}")
    for key in ("sources", "code"):
        _check(isinstance(field[key], list) and bool(field[key]), f"Missing {key} provenance")
        for reference in field[key]:
            _reference(reference)
    _check(isinstance(field["algorithm"]["identity"], str) and bool(field["algorithm"]["identity"]),
           "Missing algorithm identity")
    _check(isinstance(field["source_integrity"], dict) and isinstance(field["channel_contract"], dict)
           and bool(field["channel_contract"]), "Missing qualification metadata")
    _check(field["complete_occupancy_geometry"] is None, "Complete occupancy is unavailable in this contract")
    _check(_number(field["raw_qualified_occupied_area_m2"], "raw subset area") >= 0, "Negative subset area")
    records = sections["records"]
    _check(isinstance(records, list) and bool(records), "Missing source records")
    source_ids = set()
    for record in records:
        _check(isinstance(record["id"], str) and bool(record["id"])
               and record["id"] not in source_ids, "Missing or duplicate source ID")
        _check(isinstance(record["status"], str) and bool(record["status"]), "Missing source status")
        source_ids.add(record["id"])
    _check(isinstance(field["variants"], list) and bool(field["variants"]), "Missing lattice variants")
    bounds = _domain_bounds(field["domain_geometry"])
    choices = set()
    for variant in field["variants"]:
        _validate_variant(variant, field, source_ids, bounds)
        choice = variant["spacing_m"], tuple(variant["origin_offset_m"])
        _check(choice not in choices, "Duplicate lattice variant")
        choices.add(choice)


def load_discrete_space_field(package_dir: str | Path, *, spacing_m: float, origin_offset_m: tuple) -> dict:
    """Load verified conditional v1 samples for one explicitly selected lattice.

    Return existing dictionaries under ``field``, ``variant``, ``source_sections``
    and ``artifact_manifest``. Manifest hashes establish internal consistency,
    not owner acceptance or source completeness. External refs are not opened.
    File errors propagate; incompatible evidence raises ValueError. No geometry,
    interpolation, clearance or live confirmation is computed by this function.
    """
    _check(_number(spacing_m, "requested spacing") > 0, "Requested spacing must be positive")
    _check(isinstance(origin_offset_m, (tuple, list)) and len(origin_offset_m) == 2, "Invalid requested offset")
    for value in origin_offset_m:
        _number(value, "requested offset")
    package = Path(package_dir)
    try:
        manifest = _json((package / "artifact_manifest.json").read_bytes())
        _check(manifest["schema"] == "b3-primary-eye-artifacts/v1", "Unsupported artifact manifest schema")
        _check(isinstance(manifest["artifacts"], list), "Missing manifest artifacts")
        field, field_ref = _payload(package, manifest, "field_samples.json")
        sections, sections_ref = _payload(package, manifest, "source_sections.json")
        _check(PurePosixPath(field_ref["path"].replace("\\", "/")).parent
               == PurePosixPath(sections_ref["path"].replace("\\", "/")).parent,
               "Payloads belong to different recorded packages")
        _check(field["source_sections"] == sections_ref, "Source-section reference mismatch")
        _validate_field(field, sections)
        matching = [v for v in field["variants"] if v["spacing_m"] == spacing_m
                    and tuple(v["origin_offset_m"]) == tuple(origin_offset_m)]
        _check(len(matching) == 1, "Requested lattice is unavailable")
        return {"field": {k: v for k, v in field.items() if k != "variants"},
                "variant": matching[0], "source_sections": sections, "artifact_manifest": manifest}
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as error:
        raise ValueError(f"Malformed discrete field package: {error}") from error
