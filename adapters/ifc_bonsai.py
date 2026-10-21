"""Read-only IFC4/Bonsai facts-to-Neutral-Scene adapter."""

from __future__ import annotations

from collections.abc import Mapping
import importlib
import math
from pathlib import Path
from typing import Any

if "." in (__package__ or ""):
    from ..features.scene_contract import (
        MISSING_GEOMETRY_UNCERTAINTY,
        NEUTRAL_SCENE_V2,
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        MeshGeometry3D,
        NeutralSceneV2,
        SourceOpening,
        SourceObject,
        SurfaceFact,
        UncertaintyRecord,
    )
else:
    from features.scene_contract import (
        MISSING_GEOMETRY_UNCERTAINTY,
        NEUTRAL_SCENE_V2,
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        MeshGeometry3D,
        NeutralSceneV2,
        SourceOpening,
        SourceObject,
        SurfaceFact,
        UncertaintyRecord,
    )


IFC_ADAPTER_VERSION = "ifc4-bonsai-adapter/0.1.0"
OM_FACT_REGISTRY = {
    "OM_Layout": frozenset({"Role"}),
    "OM_AnalysisProxy": frozenset(
        {
            "OM_SourceGlobalId",
            "OM_ProxyKind",
            "OM_AnalysisRole",
            "OM_Authoritative",
            "OM_VisibilityPolicy",
        }
    ),
    "OM_AnalysisRepresentation": frozenset(
        {
            "OM_SourceGlobalId",
            "OM_SubstituteKind",
            "OM_AnalysisRole",
            "OM_VisibilityPolicy",
        }
    ),
    "OM_Affordance": frozenset({"Purpose"}),
    "OM_Surface": frozenset(
        {"Color", "Colour", "Finish", "Texture", "Elevation", "Slope"}
    ),
}


class IfcDependencyUnavailable(RuntimeError):
    """Raised when a path-based IFC operation has no IfcOpenShell runtime."""


def _load_ifcopenshell() -> Any:
    """Load the optional IFC runtime only when a path operation needs it."""
    try:
        module = importlib.import_module("ifcopenshell")
        # IfcOpenShell does not expose geom until its optional submodule is
        # imported, so adapter behavior must not depend on caller import order.
        importlib.import_module("ifcopenshell.geom")
        return module
    except ImportError as error:
        raise IfcDependencyUnavailable(
            "IfcOpenShell is required for path-based IFC4 analysis"
        ) from error


def _open_source(source: object, ifc_module: Any | None) -> object:
    """Open a path through IfcOpenShell or retain an injected read-only backend."""
    if isinstance(source, (str, Path)):
        if ifc_module is False:
            raise IfcDependencyUnavailable(
                "IfcOpenShell is required for path-based IFC4 analysis"
            )
        module = ifc_module if ifc_module is not None else _load_ifcopenshell()
        return module.open(str(source))
    return source


def _schema(source: object) -> str:
    """Read and normalize the backend schema identifier."""
    value = getattr(source, "schema", None)
    if callable(value):
        value = value()
    if not isinstance(value, str):
        raise ValueError("IFC source must expose a schema string")
    return value.upper()


def _payload(source: object) -> Mapping[str, object]:
    """Read a pre-normalized backend payload without mutating the source."""
    payload = getattr(source, "payload", None)
    if not isinstance(payload, Mapping):
        raise ValueError(
            "IFC backend must expose normalized factual payload for this adapter"
        )
    return payload


def _is_native_ifc_file(source: object) -> bool:
    """Identify an IfcOpenShell-like read-only entity database."""
    return callable(getattr(source, "by_type", None)) and not hasattr(source, "payload")


def _ifc_unit_scale(unit: object, unit_module: Any) -> float:
    """Resolve one IFC named unit to metres through its authored conversion chain."""
    scale = 1.0
    current = unit
    # Conversion-based units may nest, so retain every authored factor until
    # the chain reaches the underlying SI unit.
    while callable(getattr(current, "is_a", None)) and current.is_a(
        "IfcConversionBasedUnit"
    ):
        unit_type = str(getattr(current, "UnitType", "") or "").upper()
        if unit_type != "LENGTHUNIT":
            raise ValueError("IFC conversion unit must have UnitType=LENGTHUNIT")
        factor = getattr(current, "ConversionFactor", None)
        value = getattr(getattr(factor, "ValueComponent", None), "wrappedValue", None)
        current = getattr(factor, "UnitComponent", None)
        if value is None or current is None:
            raise ValueError("IFC conversion-based length unit is incomplete")
        scale *= float(value)
    if not callable(getattr(current, "is_a", None)) or not current.is_a("IfcSIUnit"):
        unit_class = current.is_a() if callable(getattr(current, "is_a", None)) else type(current).__name__
        raise ValueError(
            f"IFC length unit {unit_class} cannot be converted to metres"
        )
    unit_type = str(getattr(current, "UnitType", "") or "").upper()
    if unit_type != "LENGTHUNIT":
        raise ValueError("IFC SI unit must have UnitType=LENGTHUNIT")
    scale *= float(unit_module.get_prefix_multiplier(getattr(current, "Prefix", None)))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("IFC length unit scale must be finite and positive")
    return scale


def _native_length_unit(
    source: object,
) -> tuple[str, float, bool, Mapping[str, object] | None]:
    """Read the project length token, metre scale, presence, and source metadata."""
    unit_module = importlib.import_module("ifcopenshell.util.unit")
    try:
        unit = unit_module.get_project_unit(source, "LENGTHUNIT")
    except IndexError:
        # IfcOpenShell's project helper assumes an IfcProject. Partial research
        # fixtures may still carry an explicit assignment, so preserve that fact.
        unit = next(
            (
                candidate
                for assignment in source.by_type("IfcUnitAssignment")
                for candidate in (getattr(assignment, "Units", ()) or ())
                if getattr(candidate, "UnitType", None) == "LENGTHUNIT"
            ),
            None,
        )
    if unit is None:
        # IFC length units are optional in incomplete research fixtures. The
        # fallback remains explicit rather than becoming an inferred source fact.
        return "m", 1.0, False, None

    name = str(getattr(unit, "Name", "") or "").upper()
    prefix = str(getattr(unit, "Prefix", "") or "").upper()
    prefix_tokens = {
        "ATTO": "am",
        "FEMTO": "fm",
        "PICO": "pm",
        "NANO": "nm",
        "MICRO": "um",
        "MILLI": "mm",
        "CENTI": "cm",
        "DECI": "dm",
        "": "m",
        "DECA": "dam",
        "HECTO": "hm",
        "KILO": "km",
        "MEGA": "Mm",
        "GIGA": "Gm",
        "TERA": "Tm",
        "PETA": "Pm",
        "EXA": "Em",
    }
    if name == "METRE" and prefix in prefix_tokens:
        token = prefix_tokens[prefix]
    elif name == "INCH":
        token = "in"
    elif name == "FOOT":
        token = "ft"
    else:
        token = "custom"

    # IfcOpenShell owns IFC unit semantics. Direct traversal covers valid
    # partial fixtures that omit IfcProject.UnitsInContext, for which its
    # project-level convenience scale intentionally falls back to one.
    scale = _ifc_unit_scale(unit, unit_module)
    metadata = {
        "ifc_class": unit.is_a(),
        "ifc_name": name,
        "ifc_prefix": prefix or None,
        "scale_to_metres": scale,
    }
    return token, scale, True, metadata


def _native_source_id(entity: object) -> str:
    """Prefer a stable IFC GlobalId and retain a deterministic STEP fallback."""
    global_id = getattr(entity, "GlobalId", None)
    if isinstance(global_id, str) and global_id:
        return global_id
    entity_id = getattr(entity, "id", None)
    if callable(entity_id):
        return f"ifc-step:{entity_id()}"
    raise ValueError("IFC product has neither GlobalId nor a STEP identifier")


def _native_container_type_facts(
    entity: object,
) -> tuple[tuple[str, ...], str | None, str | None]:
    """Read explicit spatial containment, storey, and occurrence-type relations."""
    container_refs: list[str] = []
    level_ref = None
    for relation in getattr(entity, "ContainedInStructure", ()) or ():
        container = getattr(relation, "RelatingStructure", None)
        if container is None:
            continue
        container_ref = f"ifc-object:{_native_source_id(container)}"
        container_refs.append(container_ref)
        if container.is_a() == "IfcBuildingStorey":
            level_ref = container_ref
    for relation in getattr(entity, "Decomposes", ()) or ():
        container = getattr(relation, "RelatingObject", None)
        if container is None or not callable(getattr(container, "is_a", None)):
            continue
        container_ref = f"ifc-object:{_native_source_id(container)}"
        if container_ref not in container_refs:
            container_refs.append(container_ref)
        if container.is_a() == "IfcBuildingStorey":
            level_ref = container_ref
    type_ref = None
    for relation in getattr(entity, "IsTypedBy", ()) or ():
        relating_type = getattr(relation, "RelatingType", None)
        if relating_type is not None:
            type_ref = f"ifc-type:{_native_source_id(relating_type)}"
            break
    return tuple(container_refs), level_ref, type_ref


def _native_property_value(prop: object) -> object:
    """Unwrap supported IFC property values into plain JSON-compatible facts."""
    if hasattr(prop, "NominalValue"):
        value = getattr(prop, "NominalValue", None)
    elif hasattr(prop, "EnumerationValues"):
        value = getattr(prop, "EnumerationValues", ()) or ()
    elif hasattr(prop, "ListValues"):
        value = getattr(prop, "ListValues", ()) or ()
    else:
        return None
    if isinstance(value, (tuple, list)):
        return [getattr(item, "wrappedValue", item) for item in value]
    return getattr(value, "wrappedValue", value)


def _is_forbidden_om_fact(property_set_name: str, property_name: str) -> bool:
    """Identify OM fields reserved for derived analysis rather than source facts."""
    analysis_tokens = (
        "analysis",
        "boundary",
        "region",
        "path",
        "trend",
        "order",
        "score",
        "weight",
        "strength",
        "inferred",
    )
    searchable = f"{property_set_name[3:]} {property_name}".lower()
    return any(token in searchable for token in analysis_tokens)


def _native_property_definition_sources(
    entity: object,
    property_set_name: str | None = None,
) -> tuple[tuple[object, str, str], ...]:
    """Return property sets with scope and owner in override order."""
    definitions: list[tuple[object, str, str]] = []
    # IFC types provide reusable defaults; processing them first lets authored
    # occurrence values override only the facts they explicitly redefine.
    for type_relation in getattr(entity, "IsTypedBy", ()) or ():
        relating_type = getattr(type_relation, "RelatingType", None)
        owner_id = _native_source_id(relating_type)
        definitions.extend(
            (definition, "type", owner_id)
            for definition in getattr(relating_type, "HasPropertySets", ()) or ()
        )
    for relation in getattr(entity, "IsDefinedBy", ()) or ():
        definition = getattr(relation, "RelatingPropertyDefinition", None)
        if definition is not None:
            definitions.append((definition, "occurrence", _native_source_id(entity)))
    return tuple(
        (definition, scope, owner_id)
        for definition, scope, owner_id in definitions
        if (
            definition is not None
            and callable(getattr(definition, "is_a", None))
            and definition.is_a() == "IfcPropertySet"
            and (
                property_set_name is None
                or getattr(definition, "Name", None) == property_set_name
            )
        )
    )


def _native_om_properties(
    entity: object,
    *,
    excluded_property_sets: frozenset[str] = frozenset(),
) -> tuple[dict[str, object], tuple[UncertaintyRecord, ...]]:
    """Extract non-structured OM_ facts and quarantine derived-analysis fields."""
    result: dict[str, object] = {}
    uncertainties: list[UncertaintyRecord] = []
    source_id = _native_source_id(entity)
    for definition, _, _ in _native_property_definition_sources(entity):
        name = getattr(definition, "Name", None)
        if not isinstance(name, str) or not name.startswith("OM_"):
            continue
        if name in excluded_property_sets:
            # Dedicated neutral records normalize these facts with their units
            # and provenance, so raw duplicates cannot contradict them.
            continue
        properties = dict(result.get(name, {}))
        for prop in getattr(definition, "HasProperties", ()) or ():
            property_name = getattr(prop, "Name", None)
            if isinstance(property_name, str) and property_name:
                registered = property_name in OM_FACT_REGISTRY.get(name, ())
                if not registered:
                    forbidden = _is_forbidden_om_fact(name, property_name)
                    uncertainties.append(
                        UncertaintyRecord(
                            code=(
                                "forbidden_om_analysis_fact"
                                if forbidden
                                else "unregistered_om_factual_property"
                            ),
                            message=(
                                "Unregistered OM_ field was excluded from IFC source facts."
                            ),
                            source_refs=(source_id,),
                            operation="ifc_om_property_extraction",
                            severity="warning",
                            details={
                                "adapter": IFC_ADAPTER_VERSION,
                                "property_set_name": name,
                                "property_name": property_name,
                            },
                        )
                    )
                    continue
                properties[property_name] = _native_property_value(prop)
        if properties:
            result[name] = properties
    return result, tuple(uncertainties)


def _is_authored_affordance_zone(entity: object) -> bool:
    """Require the complete IFC4 marker for one authored affordance zone."""
    return (
        getattr(entity, "PredefinedType", None) == "USERDEFINED"
        and getattr(entity, "ObjectType", None) == "OM_AFFORDANCE_ZONE"
    )


def _native_source_role(entity: object) -> str:
    """Normalize factual IFC product roles without assigning analytical meaning."""
    if entity.is_a("IfcFurniture"):
        return "furniture"
    if entity.is_a("IfcOpeningElement"):
        return "opening"
    if entity.is_a("IfcWall"):
        return "wall"
    if entity.is_a("IfcSlab"):
        return "slab"
    if entity.is_a("IfcDoor"):
        return "door"
    if entity.is_a("IfcColumn"):
        return "column"
    if entity.is_a("IfcBuildingElementProxy"):
        proxy_properties, _ = _native_om_properties(entity)
        if "OM_AnalysisProxy" in proxy_properties:
            return "analysis_substitute"
        return "object"
    if entity.is_a("IfcCovering") or entity.is_a("IfcSurfaceFeature"):
        return "surface"
    if entity.is_a("IfcSpatialZone"):
        return "affordance_zone" if _is_authored_affordance_zone(entity) else "spatial_zone"
    if entity.is_a("IfcSpace"):
        return "space"
    if entity.is_a("IfcSite") or entity.is_a("IfcBuilding") or entity.is_a(
        "IfcBuildingStorey"
    ):
        return "spatial_container"
    if entity.is_a("IfcGrid"):
        return "grid"
    return "object"


def _native_world_transform(
    entity: object,
    length_scale: float,
    source_id: str,
) -> tuple[
    tuple[tuple[float, float, float, float], ...],
    UncertaintyRecord | None,
]:
    """Resolve one IFC placement and disclose extraction failure separately."""
    identity = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    placement = getattr(entity, "ObjectPlacement", None)
    if placement is None:
        return identity, None
    try:
        placement_module = importlib.import_module("ifcopenshell.util.placement")
        matrix = placement_module.get_local_placement(placement)
        rows = [
            [float(matrix[row][column]) for column in range(4)] for row in range(4)
        ]
        # IFC placements store translation in project units while the basis is
        # dimensionless; only the translation column enters analysis metres.
        for row in range(3):
            rows[row][3] *= length_scale
        if not all(math.isfinite(component) for row in rows for component in row):
            raise ValueError("IFC placement matrix contains nonfinite values")
        return tuple(tuple(row) for row in rows), None
    except Exception as error:
        # Placement extraction must not prevent identity-bearing source facts
        # from reaching diagnostics when a partial IFC has invalid placement data.
        return identity, UncertaintyRecord(
            code="invalid_ifc_placement",
            message="IFC placement could not be resolved; identity fallback was used.",
            source_refs=(source_id,),
            operation="ifc_placement_extraction",
            severity="warning",
            details={
                "adapter": IFC_ADAPTER_VERSION,
                "failure_type": type(error).__name__,
                "failure_message": str(error),
            },
        )


def _native_mesh_record(
    entity: object,
    source_id: str,
    units: str,
    ifc_module: Any,
    representation: object | None = None,
) -> tuple[MeshGeometry3D | None, UncertaintyRecord | None]:
    """Tessellate one IFC product as world-coordinate transport geometry."""
    if getattr(entity, "Representation", None) is None:
        return None, _missing_geometry_uncertainty(
            source_id,
            "IFC product has no representation to tessellate.",
            details={"failure_type": "missing_representation"},
        )
    try:
        settings = ifc_module.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        # Keep the legacy backend call shape when no explicit representation is
        # selected; injected test backends and older IfcOpenShell wrappers use
        # the two-argument form.
        if representation is None:
            shape = ifc_module.geom.create_shape(settings, entity)
        else:
            shape = ifc_module.geom.create_shape(settings, entity, representation)
        raw_vertices = tuple(shape.geometry.verts)
        raw_faces = tuple(shape.geometry.faces)
    except Exception as error:
        # Geometry extraction is deliberately best-effort: unsupported IFC
        # representations must become explicit missing evidence, not fabricated meshes.
        return None, _missing_geometry_uncertainty(
            source_id,
            "IFC transport geometry tessellation failed.",
            details={
                "failure_type": type(error).__name__,
                "failure_message": str(error),
            },
        )
    if len(raw_vertices) % 3 or len(raw_faces) % 3:
        return None, _missing_geometry_uncertainty(
            source_id,
            "IFC tessellation returned malformed coordinate or face arrays.",
            details={
                "vertex_value_count": len(raw_vertices),
                "face_index_count": len(raw_faces),
            },
        )
    geometry = {
        "vertices": tuple(
            raw_vertices[index : index + 3] for index in range(0, len(raw_vertices), 3)
        ),
        "triangles": tuple(
            raw_faces[index : index + 3] for index in range(0, len(raw_faces), 3)
        ),
    }
    representation = getattr(entity, "Representation", None)
    product_representation = getattr(entity, "Representation", None)
    representations = tuple(
        getattr(product_representation, "Representations", ()) or ()
    )
    source_representation_id = None
    # IfcOpenShell geometry ids begin with the STEP id of the representation
    # actually tessellated, followed by style/layer/settings qualifiers.
    geometry_identity = str(getattr(shape.geometry, "id", "") or "")
    geometry_step_token = geometry_identity.partition("-")[0]
    candidate_ids = {
        candidate.id()
        for candidate in representations
        if callable(getattr(candidate, "id", None))
    }
    if geometry_step_token.isdigit() and int(geometry_step_token) in candidate_ids:
        source_representation_id = f"ifc-step:{geometry_step_token}"
    elif geometry_identity:
        source_representation_id = f"ifc-geometry:{geometry_identity}"
    elif len(candidate_ids) == 1:
        source_representation_id = f"ifc-step:{next(iter(candidate_ids))}"
    # IfcOpenShell world-coordinate tessellation returns SI coordinates even
    # when the authored IFC uses millimetres or another project length unit.
    try:
        mesh = _mesh_record(
            source_id,
            geometry,
            "m",
            source_representation_id=source_representation_id,
            coordinate_space="world",
            transform_applied=True,
        )
    except ValueError as error:
        return None, _missing_geometry_uncertainty(
            source_id,
            "IFC tessellation did not produce usable triangle geometry.",
            details={
                "failure_type": type(error).__name__,
                "failure_message": str(error),
            },
        )
    return mesh, None


def _missing_geometry_uncertainty(
    source_id: str,
    message: str,
    *,
    details: Mapping[str, object] | None = None,
) -> UncertaintyRecord:
    """Describe unavailable tessellation while retaining its IFC source identity."""
    return UncertaintyRecord(
        code=MISSING_GEOMETRY_UNCERTAINTY,
        message=message,
        source_refs=(source_id,),
        operation="ifc_geometry_extraction",
        severity="warning",
        details={"adapter": IFC_ADAPTER_VERSION, **dict(details or {})},
    )


def _native_curve_points(
    curve: object,
    length_scale: float,
    ifc_module: Any,
) -> tuple[tuple[tuple[float, float, float], ...], Mapping[str, object] | None]:
    """Extract an IFC curve as ordered local points or structured failure details."""
    if curve is None or not callable(getattr(curve, "is_a", None)):
        return (), {"failure_type": "missing_axis_curve"}
    if curve.is_a() == "IfcPolyline":
        points: list[tuple[float, float, float]] = []
        for point in getattr(curve, "Points", ()) or ():
            coordinates = tuple(getattr(point, "Coordinates", ()) or ())
            if len(coordinates) == 2:
                coordinates = (*coordinates, 0.0)
            if len(coordinates) != 3:
                return (), {"failure_type": "invalid_polyline_coordinate_count"}
            points.append(
                tuple(float(value) * length_scale for value in coordinates)
            )
        if len(points) < 2:
            return (), {"failure_type": "insufficient_polyline_points"}
        return tuple(points), None
    try:
        tessellation = ifc_module.geom.create_shape(
            ifc_module.geom.settings(),
            curve,
        )
        geometry = getattr(tessellation, "geometry", tessellation)
        raw_vertices = tuple(geometry.verts)
        raw_edges = tuple(geometry.edges)
    except Exception as error:
        return (), {
            "failure_type": type(error).__name__,
            "failure_message": str(error),
            "curve_type": curve.is_a(),
        }
    if len(raw_vertices) % 3 or len(raw_edges) % 2:
        return (), {
            "failure_type": "malformed_curve_tessellation",
            "curve_type": curve.is_a(),
        }
    vertices = tuple(
        tuple(
            # IfcOpenShell tessellation already normalizes native curve
            # coordinates to SI metres, unlike direct IfcPolyline access.
            float(raw_vertices[offset + component])
            for component in range(3)
        )
        for offset in range(0, len(raw_vertices), 3)
    )
    ordered_indices = _ordered_curve_vertex_indices(len(vertices), raw_edges)
    if ordered_indices is None:
        return (), {
            "failure_type": "disconnected_curve_tessellation",
            "curve_type": curve.is_a(),
        }
    return tuple(vertices[index] for index in ordered_indices), None


def _ordered_curve_vertex_indices(
    vertex_count: int,
    raw_edges: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Reconstruct one deterministic connected path from tessellated edge pairs."""
    if vertex_count < 2 or not raw_edges:
        return None
    adjacency: dict[int, list[int]] = {index: [] for index in range(vertex_count)}
    edges: set[tuple[int, int]] = set()
    for offset in range(0, len(raw_edges), 2):
        start, end = int(raw_edges[offset]), int(raw_edges[offset + 1])
        if start == end or not (0 <= start < vertex_count and 0 <= end < vertex_count):
            return None
        edge = (min(start, end), max(start, end))
        edges.add(edge)
        adjacency[start].append(end)
        adjacency[end].append(start)
    active = {index for index, neighbours in adjacency.items() if neighbours}
    if not active or any(len(adjacency[index]) not in (1, 2) for index in active):
        return None
    endpoints = sorted(index for index in active if len(adjacency[index]) == 1)
    if len(endpoints) not in (0, 2):
        return None
    current = endpoints[0] if endpoints else min(active)
    result = [current]
    unused = set(edges)
    while unused:
        candidates = sorted(
            neighbour
            for neighbour in adjacency[current]
            if (min(current, neighbour), max(current, neighbour)) in unused
        )
        if not candidates:
            return None
        next_vertex = candidates[0]
        unused.remove((min(current, next_vertex), max(current, next_vertex)))
        result.append(next_vertex)
        current = next_vertex
    return tuple(result) if set(result) >= active else None


def _transform_points(
    points: tuple[tuple[float, float, float], ...],
    matrix: tuple[tuple[float, float, float, float], ...],
) -> tuple[tuple[float, float, float], ...]:
    """Apply one resolved homogeneous transform to ordered curve points."""
    return tuple(
        tuple(
            sum(matrix[row][column] * point[column] for column in range(3))
            + matrix[row][3]
            for row in range(3)
        )
        for point in points
    )


def _native_group_records(source: object) -> tuple[AuthoredGroup, ...]:
    """Map explicit IFC grouping relations without inferring membership."""
    records: list[AuthoredGroup] = []
    for group in source.by_type("IfcGroup"):
        members: list[str] = []
        for relation in getattr(group, "IsGroupedBy", ()) or ():
            for member in getattr(relation, "RelatedObjects", ()) or ():
                members.append(f"ifc-object:{_native_source_id(member)}")
        source_id = _native_source_id(group)
        records.append(
            AuthoredGroup(
                id=f"ifc-group:{source_id}",
                source_id=source_id,
                member_refs=tuple(members),
                # IFC groups are generally unconstrained. Preserve the one
                # explicit layout role so downstream analysis can distinguish
                # authored furniture groups from arbitrary project groups.
                group_role=(
                    "furniture_group"
                    if getattr(group, "ObjectType", None) == "furniture_group"
                    else "ifc_group"
                ),
                provenance={"method": "ifc4_group_assignment", "schema": "IFC4"},
            )
        )
    return tuple(records)


def _native_grid_records(
    source: object,
    length_scale: float,
    ifc_module: Any,
) -> tuple[
    tuple[AuthoredGrid, ...],
    tuple[AuthoredGridAxis, ...],
    tuple[UncertaintyRecord, ...],
]:
    """Map IFC grid axes only when their authored curve is explicit."""
    grids: list[AuthoredGrid] = []
    axes: list[AuthoredGridAxis] = []
    uncertainties: list[UncertaintyRecord] = []
    for grid in source.by_type("IfcGrid"):
        grid_id = _native_source_id(grid)
        grid_transform, grid_placement_uncertainty = _native_world_transform(
            grid,
            length_scale,
            grid_id,
        )
        if grid_placement_uncertainty is not None:
            uncertainties.append(grid_placement_uncertainty)
        axis_refs: list[str] = []
        for collection_name in ("UAxes", "VAxes", "WAxes"):
            for axis in getattr(grid, collection_name, ()) or ():
                points, curve_error = _native_curve_points(
                    getattr(axis, "AxisCurve", None),
                    length_scale,
                    ifc_module,
                )
                if not points:
                    uncertainties.append(
                        UncertaintyRecord(
                            code="unsupported_grid_axis_curve",
                            message="IFC grid axis curve could not be extracted.",
                            source_refs=(f"ifc-step:{axis.id()}", grid_id),
                            operation="ifc_grid_axis_extraction",
                            severity="warning",
                            details={
                                "adapter": IFC_ADAPTER_VERSION,
                                **dict(curve_error or {}),
                            },
                        )
                    )
                    continue
                points = _transform_points(points, grid_transform)
                same_sense = bool(getattr(axis, "SameSense", True))
                if not same_sense:
                    points = tuple(reversed(points))
                step_id = axis.id()
                axis_id = f"ifc-grid-axis:{grid_id}:{step_id}"
                axis_refs.append(axis_id)
                axes.append(
                    AuthoredGridAxis(
                        id=axis_id,
                        source_id=f"ifc-step:{step_id}",
                        curve_points=points,
                        branch_identifier=None,
                        list_identifier=collection_name,
                        same_sense=same_sense,
                        provenance={
                            "method": "ifc4_grid_axis_curve",
                            "schema": "IFC4",
                            "axis_tag": getattr(axis, "AxisTag", None),
                        },
                    )
                )
        grids.append(
            AuthoredGrid(
                id=f"ifc-grid:{grid_id}",
                source_id=grid_id,
                axis_refs=tuple(axis_refs),
                provenance={"method": "ifc4_grid", "schema": "IFC4"},
            )
        )
    return tuple(grids), tuple(axes), tuple(uncertainties)


def _native_opening_records(
    source: object,
    geometry_by_source_id: Mapping[str, MeshGeometry3D],
) -> tuple[SourceOpening, ...]:
    """Map IFC4 void-opening relations without inferring usable passage width."""
    records: list[SourceOpening] = []
    for opening in source.by_type("IfcOpeningElement"):
        source_id = _native_source_id(opening)
        hosts: list[str] = []
        for relation in getattr(opening, "VoidsElements", ()) or ():
            host = getattr(relation, "RelatingBuildingElement", None)
            if host is not None:
                hosts.append(f"ifc-object:{_native_source_id(host)}")
        mesh = geometry_by_source_id.get(source_id)
        geometry_refs = (mesh.id,) if mesh is not None else ()
        uncertainties = ()
        if mesh is None:
            uncertainties = (
                _missing_geometry_uncertainty(
                    source_id,
                    "IFC opening has no extractable transport geometry.",
                ),
            )
        records.append(
            SourceOpening(
                id=f"ifc-opening:{source_id}",
                source_id=source_id,
                host_refs=tuple(hosts),
                geometry_refs=geometry_refs,
                opening_kind=opening.is_a(),
                provenance={"method": "ifc4_voids_element", "schema": "IFC4"},
                uncertainties=uncertainties,
            )
        )
    return tuple(records)


def _native_material_records(
    source: object,
) -> tuple[tuple[MaterialFact, ...], dict[str, tuple[str, ...]]]:
    """Map IFC material assignments without interpreting material names as optics."""
    element_module = importlib.import_module("ifcopenshell.util.element")
    records_by_id: dict[str, MaterialFact] = {}
    object_material_refs: dict[str, list[str]] = {}
    for product in source.by_type("IfcProduct"):
        source_id = _native_source_id(product)
        # Query occurrences rather than relationship targets so type-inherited
        # material selects are expanded and linked to the actual source object.
        for material in element_module.get_materials(product):
            material_source_id = _native_source_id(material)
            material_id = f"ifc-material:{material_source_id}"
            if material_id not in records_by_id:
                (
                    visible_transmittance,
                    optical_status,
                    raw_optical_value,
                ) = _native_material_visible_transmittance(material)
                viewport_transparency = _native_material_viewport_transparency(
                    material
                )
                if optical_status == "invalid":
                    uncertainties = (
                        UncertaintyRecord(
                            code="invalid_material_optical_evidence",
                            message="IFC material visible transmittance is invalid.",
                            source_refs=(material_source_id,),
                            operation="ifc_material_optical_extraction",
                            severity="warning",
                            details={
                                "adapter": IFC_ADAPTER_VERSION,
                                "raw_value": raw_optical_value,
                            },
                        ),
                    )
                elif optical_status == "missing":
                    uncertainties = (
                        UncertaintyRecord(
                            code="missing_material_optical_evidence",
                            message=(
                                "IFC material has no measured visible "
                                "transmittance evidence."
                            ),
                            source_refs=(material_source_id,),
                            operation="ifc_material_optical_extraction",
                            severity="info",
                            details={"adapter": IFC_ADAPTER_VERSION},
                        ),
                    )
                else:
                    uncertainties = ()
                records_by_id[material_id] = MaterialFact(
                    id=material_id,
                    source_id=material_source_id,
                    identity=getattr(material, "Name", None),
                    visible_transmittance=visible_transmittance,
                    viewport_transparency=viewport_transparency,
                    provenance={
                        "method": "ifc4_material_select_expansion",
                        "schema": "IFC4",
                        "visible_transmittance_source": (
                            "Pset_MaterialOptical.VisibleTransmittance"
                            if visible_transmittance is not None
                            else None
                        ),
                        "viewport_transparency_source": (
                            "IfcSurfaceStyleRendering.Transparency"
                            if viewport_transparency is not None
                            else None
                        ),
                    },
                    uncertainties=uncertainties,
                )
            refs = object_material_refs.setdefault(source_id, [])
            if material_id not in refs:
                refs.append(material_id)
    return (
        tuple(records_by_id.values()),
        {source_id: tuple(refs) for source_id, refs in object_material_refs.items()},
    )


def _optional_ratio(value: object) -> float | None:
    """Return a finite IFC ratio in [0, 1] without coercing invalid evidence."""
    value = getattr(value, "wrappedValue", value)
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return None
    return ratio if math.isfinite(ratio) and 0.0 <= ratio <= 1.0 else None


def _native_material_visible_transmittance(
    material: object,
) -> tuple[float | None, str, object]:
    """Read visible transmittance while distinguishing missing and invalid facts."""
    for property_set in getattr(material, "HasProperties", ()) or ():
        if getattr(property_set, "Name", None) != "Pset_MaterialOptical":
            continue
        for prop in getattr(property_set, "Properties", ()) or ():
            if getattr(prop, "Name", None) == "VisibleTransmittance":
                raw_value = getattr(prop, "NominalValue", None)
                diagnostic_value = getattr(raw_value, "wrappedValue", raw_value)
                if not isinstance(
                    diagnostic_value,
                    (str, int, float, bool, type(None)),
                ):
                    diagnostic_value = repr(diagnostic_value)
                measure_type = (
                    raw_value.is_a()
                    if callable(getattr(raw_value, "is_a", None))
                    else None
                )
                if measure_type not in {
                    "IfcRatioMeasure",
                    "IfcNormalisedRatioMeasure",
                    "IfcPositiveRatioMeasure",
                }:
                    return None, "invalid", diagnostic_value
                ratio = _optional_ratio(raw_value)
                if ratio is None:
                    return None, "invalid", diagnostic_value
                return ratio, "measured", diagnostic_value
    return None, "missing", None


def _native_material_viewport_transparency(material: object) -> float | None:
    """Read rendering transparency without promoting it to measured optics."""
    for definition in getattr(material, "HasRepresentation", ()) or ():
        for representation in getattr(definition, "Representations", ()) or ():
            for item in getattr(representation, "Items", ()) or ():
                for style in getattr(item, "Styles", ()) or ():
                    style_items = getattr(style, "Styles", ()) or ()
                    for style_item in style_items:
                        if style_item.is_a() == "IfcSurfaceStyleRendering":
                            ratio = _optional_ratio(
                                getattr(style_item, "Transparency", None)
                            )
                            if ratio is not None:
                                return ratio
    return None


def _native_surface_records(
    source: object,
    geometry_by_source_id: Mapping[str, MeshGeometry3D],
    length_scale: float,
) -> tuple[tuple[SurfaceFact, ...], dict[str, tuple[str, ...]]]:
    """Map explicit IFC surface products without converting them into mass."""
    unit_module = importlib.import_module("ifcopenshell.util.unit")
    records: list[SurfaceFact] = []
    object_surface_refs: dict[str, list[str]] = {}
    candidates: list[tuple[object, str]] = []
    for product in source.by_type("IfcCovering"):
        if getattr(product, "PredefinedType", None) == "FLOORING":
            candidates.append((product, "IfcCovering:FLOORING"))
    for product in source.by_type("IfcSurfaceFeature"):
        object_type = getattr(product, "ObjectType", None)
        if (
            getattr(product, "PredefinedType", None) == "USERDEFINED"
            and isinstance(object_type, str)
            and object_type.startswith("OM_")
        ):
            candidates.append((product, f"IfcSurfaceFeature:{object_type}"))
    for product, identity in candidates:
        source_id = _native_source_id(product)
        surface_id = f"ifc-surface:{source_id}"
        mesh = geometry_by_source_id.get(source_id)
        geometry_refs = (mesh.id,) if mesh is not None else ()
        host_refs: list[str] = []
        linked_source_ids = [source_id]
        for relation in getattr(product, "HasAssignments", ()) or ():
            if relation.is_a() != "IfcRelAssignsToProduct":
                continue
            host = getattr(relation, "RelatingProduct", None)
            if host is not None:
                host_source_id = _native_source_id(host)
                host_refs.append(f"ifc-object:{host_source_id}")
                linked_source_ids.append(host_source_id)
        for relation in getattr(product, "CoversElements", ()) or ():
            host = getattr(relation, "RelatingBuildingElement", None)
            if host is not None:
                host_source_id = _native_source_id(host)
                host_ref = f"ifc-object:{host_source_id}"
                if host_ref not in host_refs:
                    host_refs.append(host_ref)
                linked_source_ids.append(host_source_id)
        uncertainties: list[UncertaintyRecord] = []
        if mesh is None:
            uncertainties.append(
                _missing_geometry_uncertainty(
                    source_id,
                    "IFC surface product has no extractable transport geometry.",
                )
            )
        surface_values: dict[str, object] = {}
        surface_property_sources: dict[str, dict[str, object]] = {}
        elevation_scale_source = None
        elevation_scale_to_metres = None
        for definition, source_scope, owner_source_id in _native_property_definition_sources(
            product,
            property_set_name="OM_Surface",
        ):
            for prop in getattr(definition, "HasProperties", ()) or ():
                property_name = getattr(prop, "Name", None)
                if property_name not in {
                    "Color",
                    "Colour",
                    "Finish",
                    "Texture",
                    "Elevation",
                    "Slope",
                }:
                    continue
                normalized_name = "Color" if property_name == "Colour" else property_name
                value = _native_property_value(prop)
                if property_name == "Elevation":
                    nominal_value = getattr(prop, "NominalValue", None)
                    measure_type = (
                        nominal_value.is_a()
                        if callable(getattr(nominal_value, "is_a", None))
                        else None
                    )
                    if measure_type in {
                        "IfcLengthMeasure",
                        "IfcPositiveLengthMeasure",
                        "IfcNonNegativeLengthMeasure",
                    }:
                        property_unit = getattr(prop, "Unit", None)
                        try:
                            property_scale = (
                                _ifc_unit_scale(property_unit, unit_module)
                                if property_unit is not None
                                else length_scale
                            )
                        except ValueError:
                            value = None
                        else:
                            value = float(
                                getattr(nominal_value, "wrappedValue", nominal_value)
                            ) * property_scale
                            elevation_scale_source = (
                                "property_unit"
                                if property_unit is not None
                                else "project_unit"
                            )
                            elevation_scale_to_metres = property_scale
                    else:
                        value = None
                if value is None:
                    # An explicit but unusable occurrence value must not leave
                    # a misleading inherited default visible as the winner.
                    surface_values.pop(normalized_name, None)
                    surface_property_sources.pop(normalized_name, None)
                    if normalized_name == "Elevation":
                        elevation_scale_source = None
                        elevation_scale_to_metres = None
                    uncertainties.append(
                        UncertaintyRecord(
                            code="unsupported_om_surface_property",
                            message="OM_Surface property form could not be normalized.",
                            source_refs=(source_id,),
                            operation="ifc_surface_property_extraction",
                            severity="warning",
                            details={
                                "adapter": IFC_ADAPTER_VERSION,
                                "property_name": property_name,
                                "property_class": prop.is_a(),
                                "source_scope": source_scope,
                                "owner_source_id": owner_source_id,
                                "property_set_id": _native_source_id(definition),
                            },
                        )
                    )
                    continue
                surface_values[normalized_name] = value
                surface_property_sources[normalized_name] = {
                    "scope": source_scope,
                    "owner_source_id": owner_source_id,
                    "property_set_id": _native_source_id(definition),
                    "property_class": prop.is_a(),
                }
        # Explicit OM_Surface values are factual observations. Their perceptual
        # importance remains a later description/feature-model concern.
        records.append(
            SurfaceFact(
                id=surface_id,
                source_id=source_id,
                host_refs=tuple(host_refs),
                identity=identity,
                color=surface_values.get("Color"),
                finish=surface_values.get("Finish"),
                texture=surface_values.get("Texture"),
                elevation=surface_values.get("Elevation"),
                slope=surface_values.get("Slope"),
                geometry_refs=geometry_refs,
                provenance={
                    "method": "ifc4_surface_product",
                    "schema": "IFC4",
                    "elevation_unit": (
                        "m" if surface_values.get("Elevation") is not None else None
                    ),
                    "elevation_scale_source": elevation_scale_source,
                    "elevation_scale_to_metres": elevation_scale_to_metres,
                    "property_sources": surface_property_sources,
                },
                uncertainties=tuple(uncertainties),
            )
        )
        for linked_source_id in dict.fromkeys(linked_source_ids):
            refs = object_surface_refs.setdefault(linked_source_id, [])
            if surface_id not in refs:
                refs.append(surface_id)
    return (
        tuple(records),
        {source_id: tuple(refs) for source_id, refs in object_surface_refs.items()},
    )


def _native_affordance_reference_facts(
    zone: object,
) -> tuple[tuple[str, ...], tuple[UncertaintyRecord, ...]]:
    """Extract furniture references and audit every authored zone reference."""
    furniture_refs: list[str] = []
    uncertainties: list[UncertaintyRecord] = []
    source_id = _native_source_id(zone)
    for relation in getattr(zone, "ReferencesElements", ()) or ():
        for element in getattr(relation, "RelatedElements", ()) or ():
            element_source_id = _native_source_id(element)
            if element.is_a("IfcFurniture"):
                furniture_refs.append(f"ifc-object:{element_source_id}")
                continue
            uncertainties.append(
                UncertaintyRecord(
                    code="invalid_affordance_furniture_reference",
                    message=(
                        "Authored affordance reference does not identify IFC furniture."
                    ),
                    source_refs=(element_source_id, source_id),
                    operation="ifc_affordance_reference_extraction",
                    severity="warning",
                    details={
                        "adapter": IFC_ADAPTER_VERSION,
                        "source_class": element.is_a(),
                    },
                )
            )
    if not furniture_refs:
        uncertainties.append(
            UncertaintyRecord(
                code="missing_affordance_furniture_reference",
                message="Authored affordance has no valid IFC furniture reference.",
                source_refs=(source_id,),
                operation="ifc_affordance_reference_extraction",
                severity="warning",
                details={"adapter": IFC_ADAPTER_VERSION},
            )
        )
    return tuple(furniture_refs), tuple(uncertainties)


def _native_affordance_purpose_facts(
    zone: object,
) -> tuple[str | None, dict[str, object], tuple[UncertaintyRecord, ...]]:
    """Read only explicit OM_Affordance purpose and audit missing semantics."""
    source_id = _native_source_id(zone)
    om_properties, om_uncertainties = _native_om_properties(zone)
    uncertainties = list(om_uncertainties)
    affordance_facts = om_properties.get("OM_Affordance", {})
    authored_purpose = (
        affordance_facts.get("Purpose")
        if isinstance(affordance_facts, Mapping)
        else None
    )
    if isinstance(authored_purpose, str) and authored_purpose.strip():
        return authored_purpose, om_properties, tuple(uncertainties)
    uncertainties.append(
        UncertaintyRecord(
            code=(
                "missing_affordance_purpose"
                if authored_purpose is None
                else "invalid_affordance_purpose"
            ),
            message="Authored affordance has no usable explicit OM_Affordance purpose.",
            source_refs=(source_id,),
            operation="ifc_affordance_purpose_extraction",
            severity="warning",
            details={
                "adapter": IFC_ADAPTER_VERSION,
                "authored_value_type": type(authored_purpose).__name__,
            },
        )
    )
    return None, om_properties, tuple(uncertainties)


def _native_affordance_records(
    source: object,
    geometry_by_source_id: Mapping[str, MeshGeometry3D],
) -> tuple[AuthoredAffordanceZone, ...]:
    """Map only explicitly marked IFC spatial zones as authored affordances."""
    records: list[AuthoredAffordanceZone] = []
    for zone in source.by_type("IfcSpatialZone"):
        if not _is_authored_affordance_zone(zone):
            continue
        source_id = _native_source_id(zone)
        furniture_refs, uncertainties = _native_affordance_reference_facts(zone)
        purpose, om_properties, purpose_uncertainties = (
            _native_affordance_purpose_facts(zone)
        )
        mesh = geometry_by_source_id.get(source_id)
        if mesh is None or purpose is None:
            # An authored marker without geometry is retained as a source
            # uncertainty; incomplete task semantics are likewise unusable.
            continue
        uncertainty_list = list(uncertainties)
        uncertainty_list.extend(purpose_uncertainties)
        records.append(
            AuthoredAffordanceZone(
                id=f"ifc-affordance:{source_id}",
                source_id=source_id,
                geometry_refs=(mesh.id,),
                vertical_extent=(
                    min(vertex[2] for vertex in mesh.vertices),
                    max(vertex[2] for vertex in mesh.vertices),
                ),
                purpose=purpose,
                task_facts={
                    "ifc_object_type": getattr(zone, "ObjectType", None),
                    "ifc_predefined_type": getattr(zone, "PredefinedType", None),
                    **om_properties,
                },
                source_furniture_refs=tuple(furniture_refs),
                provenance={"method": "ifc4_authored_spatial_zone", "schema": "IFC4"},
                uncertainties=tuple(uncertainty_list),
            )
        )
    return tuple(records)


def _native_analysis_domain(
    source: object,
    source_id: str | None,
    geometry_by_source_id: Mapping[str, MeshGeometry3D],
) -> AnalysisDomain | None:
    """Resolve only an explicitly selected IFC spatial product as the domain."""
    if source_id is None:
        return None
    selected = next(
        (
            entity
            for entity in source.by_type("IfcSpatialElement")
            if _native_source_id(entity) == source_id
        ),
        None,
    )
    if selected is None:
        raise ValueError("analysis_domain_source_id must identify an IFC spatial element")
    mesh = geometry_by_source_id.get(source_id)
    if mesh is None:
        return AnalysisDomain(
            id=f"ifc-domain:{source_id}",
            geometry_refs=(),
            source_id=source_id,
            selection_method="explicit_ifc_source_id",
            provenance={"method": "ifc4_explicit_domain", "schema": "IFC4"},
            uncertainties=(
                _missing_geometry_uncertainty(
                    source_id,
                    "Explicit IFC analysis domain has no extractable geometry.",
                ),
            ),
        )
    return AnalysisDomain(
        id=f"ifc-domain:{source_id}",
        geometry_refs=(mesh.id,),
        source_id=source_id,
        selection_method="explicit_ifc_source_id",
        provenance={"method": "ifc4_explicit_domain", "schema": "IFC4"},
        uncertainties=(),
    )


def _scene_from_native_ifc(
    source: object,
    ifc_module: Any,
    analysis_domain_source_id: str | None,
) -> NeutralSceneV2:
    """Build a Neutral Scene from native IFC4 product facts without mutation."""
    units, length_scale, has_explicit_length_unit, unit_metadata = (
        _native_length_unit(source)
    )
    authored_groups = _native_group_records(source)
    authored_grids, authored_grid_axes, grid_uncertainties = _native_grid_records(
        source,
        length_scale,
        ifc_module,
    )
    materials, object_material_refs = _native_material_records(source)
    geometries: list[MeshGeometry3D] = []
    geometry_by_source_id: dict[str, MeshGeometry3D] = {}
    analysis_bindings: dict[str, tuple[str, str]] = {}
    extracted_products: list[
        tuple[object, str, tuple[str, ...], tuple[UncertaintyRecord, ...]]
    ] = []
    for entity in source.by_type("IfcProduct"):
        source_id = _native_source_id(entity)
        product_representation = getattr(entity, "Representation", None)
        representations = tuple(
            getattr(product_representation, "Representations", ()) or ()
        )
        body_representation = next(
            (
                candidate
                for candidate in representations
                if getattr(candidate, "RepresentationIdentifier", None) == "Body"
            ),
            None,
        )
        analysis_representation = next(
            (
                candidate
                for candidate in representations
                if getattr(candidate, "RepresentationIdentifier", None) == "Analysis"
            ),
            None,
        )
        mesh, geometry_uncertainty = _native_mesh_record(
            entity,
            source_id,
            units,
            ifc_module,
            body_representation,
        )
        if mesh is None:
            geometry_refs = ()
            uncertainties = (geometry_uncertainty,) if geometry_uncertainty else ()
        else:
            # Geometry references keep downstream consumers independent from
            # IfcOpenShell entities while preserving the stable source linkage.
            geometries.append(mesh)
            geometry_by_source_id[source_id] = mesh
            geometry_refs = (mesh.id,)
            uncertainties = ()
        extracted_products.append((entity, source_id, geometry_refs, uncertainties))
        if analysis_representation is not None:
            analysis_source_id = f"{source_id}:analysis"
            analysis_mesh, analysis_uncertainty = _native_mesh_record(
                entity,
                analysis_source_id,
                units,
                ifc_module,
                analysis_representation,
            )
            if analysis_mesh is not None:
                geometries.append(analysis_mesh)
                analysis_geometry_refs = (analysis_mesh.id,)
                analysis_uncertainties = ()
                # Keep Body on the owning object for source/audit inspection;
                # canonical trend consumers reach this separate target only
                # through the explicit typed binding below.
                analysis_bindings[source_id] = (
                    f"ifc-object:{analysis_source_id}",
                    analysis_mesh.id,
                )
            else:
                analysis_geometry_refs = ()
                analysis_uncertainties = (
                    (analysis_uncertainty,) if analysis_uncertainty else ()
                )
            extracted_products.append(
                (
                    entity,
                    analysis_source_id,
                    analysis_geometry_refs,
                    analysis_uncertainties,
                )
            )
    # Relationship records are built only after every product geometry has
    # been indexed, so facts can reference meshes independent of IFC entity order.
    openings = _native_opening_records(source, geometry_by_source_id)
    surfaces, object_surface_refs = _native_surface_records(
        source,
        geometry_by_source_id,
        length_scale,
    )
    object_group_refs: dict[str, list[str]] = {}
    for group in authored_groups:
        for member_ref in group.member_refs:
            object_group_refs.setdefault(member_ref, []).append(group.id)
    object_opening_refs: dict[str, list[str]] = {}
    for opening in openings:
        for host_ref in opening.host_refs:
            object_opening_refs.setdefault(host_ref, []).append(opening.id)
    source_objects: list[SourceObject] = []
    for entity, source_id, geometry_refs, uncertainties in extracted_products:
        source_class = entity.is_a()
        container_refs, level_ref, type_ref = _native_container_type_facts(entity)
        world_transform, placement_uncertainty = _native_world_transform(
            entity,
            length_scale,
            source_id,
        )
        object_uncertainties = uncertainties + (
            (placement_uncertainty,) if placement_uncertainty is not None else ()
        )
        om_properties, om_uncertainties = _native_om_properties(
            entity,
            excluded_property_sets=frozenset({"OM_Surface"}),
        )
        object_uncertainties += om_uncertainties
        source_role = (
            "analysis_substitute"
            if source_id.endswith(":analysis")
            else _native_source_role(entity)
        )
        source_properties = dict(om_properties)
        if source_role == "analysis_substitute":
            source_provenance_representation = "Analysis"
            source_properties.setdefault(
                "OM_AnalysisRepresentation",
                {
                    "OM_SourceGlobalId": source_id.removesuffix(":analysis"),
                    "OM_SubstituteKind": "MassPatch",
                    "OM_AnalysisRole": "analysis_geometry_substitute",
                    "OM_VisibilityPolicy": "analysis_only",
                },
            )
        else:
            source_provenance_representation = None
            binding = analysis_bindings.get(source_id)
            if binding is not None and source_role == "furniture":
                substitute_id, geometry_id = binding
                source_properties["OM_FunctionSubstitutes"] = [
                    {
                        "substitute_id": substitute_id,
                        "source_object_id": f"ifc-object:{source_id}",
                        "consumer": "trend",
                        "substitute_kind": "MassPatch",
                        "analysis_role": "analysis_geometry_substitute",
                        "representation_identifier": "Analysis",
                        "provenance": {
                            "source_global_id": source_id,
                            "extraction_method": "ifc4_analysis_representation",
                            "world_transform_applied": True,
                            "representation_identifier": "Analysis",
                            "geometry_refs": [geometry_id],
                        },
                    }
                ]
        source_objects.append(
            SourceObject(
                id=f"ifc-object:{source_id}",
                source_id=source_id,
                source_role=source_role,
                source_class=source_class,
                world_transform=world_transform,
                level_ref=level_ref,
                container_refs=container_refs,
                geometry_refs=geometry_refs,
                type_ref=type_ref,
                group_refs=tuple(
                    object_group_refs.get(f"ifc-object:{source_id}", ())
                ),
                material_refs=object_material_refs.get(source_id, ()),
                surface_refs=object_surface_refs.get(source_id, ()),
                opening_refs=tuple(
                    object_opening_refs.get(f"ifc-object:{source_id}", ())
                ),
                factual_properties=source_properties,
                provenance={
                    "method": "ifc4_extraction",
                    "schema": "IFC4",
                    "source_step_id": entity.id(),
                    "mesh_coordinate_space": "world" if geometry_refs else None,
                    "mesh_transform_applied": bool(geometry_refs),
                    "world_transform_semantics": "source_factual_placement",
                    **({"representation_identifier": source_provenance_representation} if source_provenance_representation else {}),
                },
                uncertainties=object_uncertainties,
            )
        )
    # Affordance geometry is authored input, but the neutral record must refer
    # to the already extracted transport mesh rather than the IFC entity.
    authored_affordances = _native_affordance_records(
        source,
        geometry_by_source_id,
    )
    analysis_domain = _native_analysis_domain(
        source,
        analysis_domain_source_id,
        geometry_by_source_id,
    )
    scene_uncertainties: list[UncertaintyRecord] = list(grid_uncertainties)
    if not has_explicit_length_unit:
        scene_uncertainties.append(
            UncertaintyRecord(
                code="missing_ifc_length_unit",
                message="IFC has no explicit project length unit; metre fallback was used.",
                source_refs=("ifc-source",),
                operation="ifc_unit_extraction",
                severity="warning",
                details={"adapter": IFC_ADAPTER_VERSION, "fallback_unit": "m"},
            )
        )
    elif units == "custom" and unit_metadata is not None:
        scene_uncertainties.append(
            UncertaintyRecord(
                code="noncanonical_ifc_length_unit",
                message=(
                    "IFC length scale was preserved, but its source unit has no "
                    "canonical Neutral Scene token."
                ),
                source_refs=("ifc-source",),
                operation="ifc_unit_extraction",
                severity="info",
                details={"adapter": IFC_ADAPTER_VERSION, **unit_metadata},
            )
        )
    if not authored_grids:
        scene_uncertainties.append(
            UncertaintyRecord(
                code="missing_authored_grid",
                message="IFC contains no explicit authored grid.",
                source_refs=("ifc-source",),
                operation="ifc_grid_extraction",
                severity="info",
                details={"adapter": IFC_ADAPTER_VERSION},
            )
        )
    elif not authored_grid_axes:
        scene_uncertainties.append(
            UncertaintyRecord(
                code="unusable_authored_grid",
                message="IFC grid contains no supported explicit axis curves.",
                source_refs=tuple(grid.source_id or grid.id for grid in authored_grids),
                operation="ifc_grid_extraction",
                severity="warning",
                details={"adapter": IFC_ADAPTER_VERSION},
            )
        )
    if analysis_domain is None:
        scene_uncertainties.append(
            UncertaintyRecord(
                code="missing_analysis_domain",
                message="No IFC spatial element was explicitly selected as analysis domain.",
                source_refs=("ifc-source",),
                operation="ifc_domain_selection",
                severity="info",
                details={"adapter": IFC_ADAPTER_VERSION},
            )
        )
    for zone in source.by_type("IfcSpatialZone"):
        if not _is_authored_affordance_zone(zone):
            continue
        zone_source_id = _native_source_id(zone)
        purpose, _, purpose_uncertainties = _native_affordance_purpose_facts(zone)
        if purpose is None:
            scene_uncertainties.extend(
                uncertainty
                for uncertainty in purpose_uncertainties
                if uncertainty.code
                in {"missing_affordance_purpose", "invalid_affordance_purpose"}
            )
        _, reference_uncertainties = _native_affordance_reference_facts(zone)
        if purpose is None or zone_source_id not in geometry_by_source_id:
            # Preserve semantic reference errors whenever the zone cannot
            # produce a usable neutral affordance record.
            scene_uncertainties.extend(reference_uncertainties)
        if zone_source_id not in geometry_by_source_id:
            scene_uncertainties.append(
                UncertaintyRecord(
                    code="unusable_authored_affordance",
                    message="Explicit IFC affordance marker has no usable geometry.",
                    source_refs=(zone_source_id,),
                    operation="ifc_affordance_extraction",
                    severity="warning",
                    details={"adapter": IFC_ADAPTER_VERSION},
                )
            )
    return _scene_from_records(
        units,
        source_objects,
        geometries,
        authored_groups=authored_groups,
        authored_grids=authored_grids,
        authored_grid_axes=authored_grid_axes,
        openings=openings,
        materials=materials,
        surfaces=surfaces,
        authored_affordances=authored_affordances,
        analysis_units="m",
        analysis_domain=analysis_domain,
        uncertainties=tuple(scene_uncertainties),
    )


def _scene_from_records(
    units: str,
    source_objects: list[SourceObject],
    geometries: list[MeshGeometry3D],
    *,
    authored_groups: tuple[AuthoredGroup, ...] = (),
    authored_grids: tuple[AuthoredGrid, ...] = (),
    authored_grid_axes: tuple[AuthoredGridAxis, ...] = (),
    openings: tuple[SourceOpening, ...] = (),
    materials: tuple[MaterialFact, ...] = (),
    surfaces: tuple[SurfaceFact, ...] = (),
    authored_affordances: tuple[AuthoredAffordanceZone, ...] = (),
    analysis_units: str | None = None,
    analysis_domain: AnalysisDomain | None = None,
    uncertainties: tuple[UncertaintyRecord, ...] = (),
) -> NeutralSceneV2:
    """Assemble source facts into the common IFC Neutral Scene context."""
    context = AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2,
        source_schema="IFC4",
        adapter_version=IFC_ADAPTER_VERSION,
        source_length_unit=units,
        analysis_length_unit=analysis_units or units,
        world_coordinate_system={"method": "ifc_placement_resolution"},
        level_references=tuple(
            dict.fromkeys(
                item.level_ref for item in source_objects if item.level_ref is not None
            )
        ),
        analysis_plane=AnalysisPlane(
            name="ifc-world-plan",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=1e-6,
        topology_tolerance=1e-6,
        walking_body_profiles=(),
        visual_height_bands=(),
        capability_flags={
            "height": bool(geometries),
            "optical": any(
                material.visible_transmittance is not None for material in materials
            ),
            "viewport_transparency": any(
                material.viewport_transparency is not None for material in materials
            ),
            "authored_groups": bool(authored_groups),
            "authored_grid": bool(authored_grid_axes),
            "authored_affordance": bool(authored_affordances),
            "analysis_domain": bool(
                analysis_domain is not None and analysis_domain.geometry_refs
            ),
        },
        input_mode="ifc",
    )
    return NeutralSceneV2(
        context=context,
        analysis_domain=analysis_domain,
        source_objects=tuple(source_objects),
        geometries=tuple(geometries),
        authored_groups=authored_groups,
        authored_grids=authored_grids,
        authored_grid_axes=authored_grid_axes,
        openings=openings,
        materials=materials,
        surfaces=surfaces,
        authored_affordances=authored_affordances,
        uncertainties=uncertainties,
    )


def _vector(value: object, label: str) -> tuple[float, float, float]:
    """Validate one finite three-dimensional coordinate."""
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError(f"{label} must contain three coordinates")
    result = tuple(float(component) for component in value)
    if not all(math.isfinite(component) for component in result):
        raise ValueError(f"{label} must contain finite coordinates")
    return result


def _mesh_record(
    source_id: str,
    geometry: Mapping[str, object],
    units: str,
    *,
    source_representation_id: str | None = None,
    coordinate_space: str = "source",
    transform_applied: bool = False,
) -> MeshGeometry3D:
    """Convert one normalized IFC representation into a transport mesh."""
    raw_vertices = geometry.get("vertices", ())
    raw_triangles = geometry.get("triangles", ())
    if not isinstance(raw_vertices, (tuple, list)) or not isinstance(
        raw_triangles, (tuple, list)
    ):
        raise ValueError(f"{source_id}.geometry vertices and triangles must be sequences")
    if not raw_vertices or not raw_triangles:
        raise ValueError(f"{source_id}.geometry is empty")
    vertices = tuple(
        _vector(vertex, f"{source_id}.geometry.vertices[{index}]")
        for index, vertex in enumerate(raw_vertices)
    )
    triangles = []
    for triangle_index, triangle in enumerate(raw_triangles):
        label = f"{source_id}.geometry.triangle[{triangle_index}]"
        if not isinstance(triangle, (tuple, list)) or len(triangle) != 3:
            raise ValueError(f"{label} must contain exactly three indices")
        indices = []
        for vertex_index in triangle:
            if isinstance(vertex_index, bool) or not isinstance(vertex_index, int):
                raise ValueError(f"{label} must contain integer indices")
            if vertex_index < 0 or vertex_index >= len(vertices):
                raise ValueError(f"{label} index is outside vertices")
            indices.append(vertex_index)
        triangles.append(tuple(indices))
    is_manifold, is_closed = _triangle_topology_flags(tuple(triangles))
    # Edge incidence derives topology from the tessellation itself. This avoids
    # both IFC-class guesses and the false unknowns that suppress height bands.
    return MeshGeometry3D(
        id=f"ifc-mesh:{source_id}",
        vertices=vertices,
        triangle_indices=tuple(triangles),
        normals=(),
        is_manifold=is_manifold,
        is_closed=is_closed,
        local_to_world_provenance={
            "method": "ifc4_read_only_extraction",
            "source_global_id": source_id,
            "coordinate_space": coordinate_space,
            "transform_applied": transform_applied,
        },
        source_representation_id=source_representation_id or source_id,
        tessellation_settings={
            "backend": "IfcOpenShell",
            "mode": "transport",
            "coordinate_space": coordinate_space,
            "transform_applied": transform_applied,
        },
        units=units,
    )


def _triangle_topology_flags(
    triangles: tuple[tuple[int, int, int], ...],
) -> tuple[bool, bool]:
    """Derive conservative manifold and closed flags from triangle connectivity."""
    normalized_triangles = [tuple(sorted(triangle)) for triangle in triangles]
    if len(set(normalized_triangles)) != len(normalized_triangles):
        return False, False
    edge_counts: dict[tuple[int, int], int] = {}
    edge_to_triangles: dict[tuple[int, int], list[int]] = {}
    for triangle_index, triangle in enumerate(triangles):
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
            edge_to_triangles.setdefault(edge, []).append(triangle_index)
    if not edge_counts or any(count > 2 for count in edge_counts.values()):
        return False, False

    # Edge-connected components may be separate solids, but sharing a vertex
    # would make the tessellation non-manifold at that touching point.
    adjacency = [[] for _ in triangles]
    for edge_triangles in edge_to_triangles.values():
        for first in edge_triangles:
            adjacency[first].extend(
                second for second in edge_triangles if second != first
            )
    components: list[set[int]] = []
    unseen = set(range(len(triangles)))
    while unseen:
        root = unseen.pop()
        component = {root}
        stack = [root]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    component_vertices = [
        {vertex for triangle_index in component for vertex in triangles[triangle_index]}
        for component in components
    ]
    for index, vertices in enumerate(component_vertices):
        if any(vertices.intersection(other) for other in component_vertices[index + 1 :]):
            return False, False
    return (
        True,
        all(count == 2 for count in edge_counts.values()),
    )


def _scene_from_source(
    source: object,
    ifc_module: Any | None = None,
    analysis_domain_source_id: str | None = None,
) -> NeutralSceneV2:
    """Build Neutral Scene v2 from normalized IFC facts only."""
    if _schema(source) != "IFC4":
        raise ValueError("IFC4 adapter accepts only the IFC4 schema")
    if _is_native_ifc_file(source):
        module = ifc_module if ifc_module is not None else _load_ifcopenshell()
        return _scene_from_native_ifc(source, module, analysis_domain_source_id)
    if analysis_domain_source_id is not None:
        raise ValueError(
            "analysis_domain_source_id requires a native IFC source, not normalized payload"
        )
    payload = _payload(source)
    units = payload.get("source_length_unit", "m")
    if not isinstance(units, str):
        raise ValueError("IFC source_length_unit must be a string")
    objects = payload.get("objects", ())
    if not isinstance(objects, (tuple, list)):
        raise ValueError("IFC payload objects must be an ordered sequence")

    geometries = []
    source_objects = []
    for index, item in enumerate(objects):
        if not isinstance(item, Mapping):
            raise ValueError(f"IFC payload objects[{index}] must be a mapping")
        source_id = item.get("global_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"IFC payload objects[{index}] requires global_id")
        geometry = item.get("geometry")
        geometry_refs = ()
        uncertainties = ()
        if isinstance(geometry, Mapping):
            try:
                mesh = _mesh_record(source_id, geometry, units)
            except ValueError as error:
                if "geometry is empty" not in str(error):
                    raise
                uncertainties = (
                    UncertaintyRecord(
                        code=MISSING_GEOMETRY_UNCERTAINTY,
                        message="IFC representation has no transport triangles or vertices.",
                        source_refs=(source_id,),
                        operation="ifc_geometry_extraction",
                        severity="warning",
                        details={"adapter": IFC_ADAPTER_VERSION},
                    ),
                )
            else:
                geometries.append(mesh)
                geometry_refs = (mesh.id,)
        elif geometry is None:
            # IFC source identity remains useful even when tessellation is
            # unavailable; retain it with an explicit, non-zero uncertainty.
            uncertainties = (
                UncertaintyRecord(
                    code=MISSING_GEOMETRY_UNCERTAINTY,
                    message="IFC representation could not be extracted as transport geometry.",
                    source_refs=(source_id,),
                    operation="ifc_geometry_extraction",
                    severity="warning",
                    details={"adapter": IFC_ADAPTER_VERSION},
                ),
            )
        else:
            raise ValueError(f"IFC payload objects[{index}].geometry must be a mapping or null")
        source_objects.append(
            SourceObject(
                id=f"ifc-object:{source_id}",
                source_id=source_id,
                source_role="furniture"
                if item.get("ifc_class") == "IfcFurniture"
                else "object",
                source_class=item.get("ifc_class"),
                geometry_refs=geometry_refs,
                provenance={
                    "method": "ifc4_read_only_extraction",
                    "schema": "IFC4",
                },
                uncertainties=uncertainties,
            )
        )

    return _scene_from_records(units, source_objects, geometries)


def load_ifc_neutral_scene(
    source: str | Path | object,
    *,
    ifc_module: Any | None = None,
    analysis_domain_source_id: str | None = None,
) -> NeutralSceneV2:
    """Read IFC4 facts into Neutral Scene v2 without source mutation or analysis."""
    opened = _open_source(source, ifc_module)
    return _scene_from_source(opened, ifc_module, analysis_domain_source_id)


__all__ = [
    "IFC_ADAPTER_VERSION",
    "IfcDependencyUnavailable",
    "load_ifc_neutral_scene",
]
