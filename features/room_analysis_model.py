from __future__ import annotations

from statistics import mean


CONTRACT = {"id": "room_analysis_model", "version": 1}


def build_room_analysis_model(scene: dict, matrix: dict) -> dict:
    """Build the static room analysis model from neutral scene and matrix data."""
    metrics = _metric_records(matrix)
    return {
        "contract": dict(CONTRACT),
        "source": matrix.get("source") or scene.get("source"),
        "base_layer": _base_layer(scene),
        "object_layer": _object_layer(scene, matrix),
        "region_layer": _region_layer(scene, matrix),
        "network_layer": _network_layer(matrix),
        "reference_layer": _reference_layer(scene, matrix),
        "metric_layer": {"metrics": metrics},
        "summary_layer": {"summaries": _summary_records(metrics, matrix)},
    }


def _base_layer(scene: dict) -> dict:
    """Return the room-level coordinate and boundary records."""
    width, height = scene.get("size", (0.0, 0.0))
    return {
        "room": {
            "id": "room",
            "bounds": {"width": width, "height": height},
            "boundaries": list(scene.get("boundaries", [])),
        }
    }


def _object_layer(scene: dict, matrix: dict) -> dict:
    """Return furniture and operational object records already built upstream."""
    return {
        "objects": list(scene.get("objects", [])),
        "furniture_affordance_extents": list(
            matrix.get("furniture_affordance_extents", [])
        ),
        "furniture_groups": list(matrix.get("furniture_groups", [])),
        "entries": list(scene.get("entries", [])),
        "columns": list(scene.get("columns", [])),
    }


def _region_layer(scene: dict, matrix: dict) -> dict:
    """Return activity regions and whole-room fallback scopes."""
    scopes = list(matrix.get("region_position_grammar", {}).get("scopes", []))
    return {
        "activity_regions": list(scene.get("regions", [])),
        "position_scopes": scopes,
        "room_scopes": [scope for scope in scopes if scope.get("kind") == "room_scope"],
    }


def _network_layer(matrix: dict) -> dict:
    """Return spatial graph records without reclassifying their semantics."""
    return {
        "spatial_networks": list(matrix.get("spatial_networks", [])),
        "inferred_region_gap_path_graph": matrix.get("inferred_region_gap_path_graph", {}),
        "negative_space_graph": matrix.get("negative_space_graph", {}),
    }


def _reference_layer(scene: dict, matrix: dict) -> dict:
    """Return independent reference systems for later alignment metrics."""
    return {
        "boundary_semantics": list(matrix.get("boundary_semantics", [])),
        "column_grid": matrix.get("column_grid", {}),
        "column_axes": list(scene.get("column_axes", [])),
        "boundaries": list(scene.get("boundaries", [])),
    }


def _metric_records(matrix: dict) -> list[dict]:
    """Convert current matrix rows into static model metric records."""
    records = []
    for row in matrix.get("rows", []):
        if row.get("metric") in {"P_position_fit", "P_position_confidence"}:
            # Position rows carry per-scope evidence; expose those scopes as the
            # model targets instead of keeping one opaque row-level target.
            records.extend(_position_metric_records(row))
            continue
        if row.get("view_id") == "column_alignment":
            expanded = _column_grid_metric_records(row)
            if expanded:
                records.extend(expanded)
                continue
        records.append(_row_metric_record(row))
    return records


def _position_metric_records(row: dict) -> list[dict]:
    """Convert position grammar rows into scope-targeted metric records."""
    metric = row.get("metric")
    value_key = "position-fit" if metric == "P_position_fit" else "position-confidence"
    records = []
    for item in row.get("region_position_grammar_evidence", []):
        target_id = item.get("subject_id") or item.get("id") or metric
        target_kind = item.get("subject_kind") or "activity_region"
        value = item.get(value_key)
        records.append(
            {
                "metric": metric,
                "family": row.get("view_id"),
                "target_layer": _scope_target_layer(target_kind),
                "target_id": target_id,
                "value": value,
                "status": row.get("status", "computed"),
                "geometry": None,
                "anchor": None,
                "reference": item.get("position-system-id"),
                "confidence": item.get("position-confidence"),
                "method": row.get("method"),
                # Existing evidence still uses old field names internally; strip
                # experiment-facing names at the model boundary.
                "evidence": _without_subject_id(item),
                "uncertainty": row.get("uncertainty"),
            }
        )
    return records


def _column_grid_metric_records(row: dict) -> list[dict]:
    """Expand column-grid rows into concrete model-targeted metric records."""
    metric = row.get("metric")
    if metric == "object_column_axis_phase_alignment":
        return [
            _evidence_metric_record(
                row,
                target_layer="Furniture",
                target_id=item["object_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("object_axis_phase_evidence", [])
        ]
    if metric == "object_column_bay_local_position_coverage":
        return [
            _evidence_metric_record(
                row,
                target_layer="Furniture",
                target_id=item["object_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("object_bay_local_position_evidence", [])
        ]
    if metric == "column_grid_C_local_profile":
        return [
            _evidence_metric_record(
                row,
                target_layer="ActivityRegion",
                target_id=item["region_id"],
                value=item.get("frame_agreement"),
                evidence=item,
            )
            for item in row.get("column_grid_evidence", {}).get("local_profiles", [])
        ]
    if metric == "column_grid_C_global":
        return [
            _evidence_metric_record(
                row,
                target_layer="ActivityRegion",
                target_id=item["region_id"],
                value=item.get("agreement"),
                evidence=item,
            )
            for item in row.get("column_grid_evidence", {}).get("global_relations", [])
        ]
    if metric == "column_grid_inter_region_alignment":
        return [
            _evidence_metric_record(
                row,
                target_layer="SpatialNetwork",
                target_id=item["target_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("inter_region_column_grid_evidence", [])
        ]
    return []


def _evidence_metric_record(
    row: dict,
    *,
    target_layer: str,
    target_id: str,
    value,
    evidence: dict,
) -> dict:
    """Build one metric record from a row-level evidence item."""
    return {
        "metric": row.get("metric"),
        "family": row.get("view_id"),
        "target_layer": target_layer,
        "target_id": target_id,
        "value": value,
        "status": row.get("status", "computed"),
        "geometry": None,
        "anchor": None,
        "reference": row.get("column_grid_evidence") or row.get("column_axis_evidence"),
        "confidence": row.get("confidence"),
        "method": row.get("method"),
        "evidence": evidence,
        "uncertainty": row.get("uncertainty"),
    }


def _row_metric_record(row: dict) -> dict:
    """Convert a matrix row into one model-targeted metric record."""
    return {
        "metric": row.get("metric"),
        "family": row.get("view_id"),
        "target_layer": _row_target_layer(row),
        "target_id": _row_target_id(row),
        "value": row.get("score"),
        "status": row.get("status", "computed"),
        "geometry": _row_geometry(row),
        "anchor": None,
        "reference": _row_reference(row),
        "confidence": row.get("confidence"),
        "method": row.get("method"),
        "evidence": row.get("evidence"),
        "uncertainty": row.get("uncertainty"),
    }


def _summary_records(metrics: list[dict], matrix: dict) -> list[dict]:
    """Summarize metric values by family without calibrating final perception."""
    by_family: dict[str, list[float]] = {}
    for metric in metrics:
        value = metric.get("value")
        if metric.get("status") == "computed" and _is_number(value):
            by_family.setdefault(metric.get("family") or "unknown", []).append(value)

    summaries = [
        {
            "id": f"summary_{family}",
            "family": family,
            "value_mean": round(mean(values), 4),
            "metric_count": len(values),
            "method": "mean_of_model_metric_values_by_family",
        }
        for family, values in sorted(by_family.items())
    ]
    summaries.append(
        {
            "id": "summary_score_matrix",
            "family": "score_matrix",
            "value": matrix.get("score_matrix"),
            "method": "existing_score_matrix_projection",
        }
    )
    return summaries


def _scope_target_layer(kind: str) -> str:
    """Map position grammar scope kinds into model layer names."""
    if kind == "room_scope":
        return "RoomScope"
    return "ActivityRegion"


def _row_target_layer(row: dict) -> str:
    """Infer the static target layer for an existing metric row."""
    metric = row.get("metric", "")
    family = row.get("view_id", "")
    if "boundary" in metric or "boundary" in family:
        return "ReferenceSystem"
    if family == "column_alignment" and metric.startswith("column_grid_"):
        return "ReferenceSystem"
    if family == "path_connectivity" or "gap_path" in metric or "negative_space" in metric:
        return "SpatialNetwork"
    if family == "region_alignment" or metric.startswith("region_"):
        return "ActivityRegion"
    if "object" in metric:
        return "Furniture"
    if "group" in metric:
        return "FurnitureGroup"
    return "Room"


def _row_target_id(row: dict) -> str:
    """Return a stable coarse target id for row-level metrics."""
    layer = _row_target_layer(row)
    if layer == "ActivityRegion":
        return "activity_regions"
    if layer == "SpatialNetwork":
        return "spatial_networks"
    if layer == "ReferenceSystem":
        return "reference_systems"
    if layer == "Furniture":
        return "furniture"
    if layer == "FurnitureGroup":
        return "furniture_groups"
    return "room"


def _row_geometry(row: dict):
    """Return geometry evidence when a row exposes one compact geometry field."""
    for key in (
        "region_axis_evidence",
        "inferred_region_gap_path_evidence",
        "inferred_region_candidate_evidence",
        "inferred_region_evidence",
    ):
        if key in row:
            return row[key]
    return None


def _row_reference(row: dict):
    """Return the independent reference evidence attached to a metric row."""
    for key in ("column_axis_evidence", "column_grid_evidence", "boundary_axis_evidence"):
        if key in row:
            return row[key]
    return None


def _without_subject_id(item: dict) -> dict:
    """Copy evidence while dropping legacy experiment-facing key names."""
    return {key: value for key, value in item.items() if key != "subject_id"}


def _is_number(value) -> bool:
    """Return whether a metric value can participate in simple summaries."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
