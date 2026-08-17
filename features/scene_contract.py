"""Pure-Python Neutral Scene v2 records and strict JSON serialization."""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
import math
from types import MappingProxyType
from typing import Callable, Mapping, TypeAlias, TypeVar, cast


NEUTRAL_SCENE_V2 = "neutral-scene-v2"
MISSING_GEOMETRY_UNCERTAINTY = "missing_geometry"
ALLOWED_INPUT_MODES = frozenset({"ifc", "blender_geometry", "hybrid", "svg"})
ALLOWED_LENGTH_UNITS = frozenset(
    {
        "am",
        "fm",
        "pm",
        "nm",
        "um",
        "mm",
        "cm",
        "dm",
        "m",
        "dam",
        "hm",
        "km",
        "Mm",
        "Gm",
        "Tm",
        "Pm",
        "Em",
        "in",
        "ft",
        "custom",
    }
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
FrozenJsonValue: TypeAlias = (
    JsonScalar
    | tuple["FrozenJsonValue", ...]
    | Mapping[str, "FrozenJsonValue"]
)
Vector3: TypeAlias = tuple[float, float, float]
Matrix3: TypeAlias = tuple[Vector3, Vector3, Vector3]
Matrix4: TypeAlias = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]

RecordType = TypeVar("RecordType", bound="_Record")
Converter: TypeAlias = Callable[[object, str], object]


def _child(path: str, name: str) -> str:
    """Append a named field to a record path."""
    return f"{path}.{name}" if path else name


def _item(path: str, index: int) -> str:
    """Append a sequence index to a record path."""
    return f"{path}[{index}]"


def _json_value(value: object, path: str) -> JsonValue:
    """Convert standard containers to JSON values and reject raw application objects."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path or '<root>'} contains a non-finite float")
        return value
    if isinstance(value, _Record):
        return {
            record_field.name: _json_value(
                getattr(value, record_field.name),
                _child(path, record_field.name),
            )
            for record_field in fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path or '<root>'} has unsupported key type "
                    f"{type(key).__name__}"
                )
            result[key] = _json_value(nested, _child(path, key))
        return result
    if isinstance(value, (list, tuple)):
        return [_json_value(nested, _item(path, index)) for index, nested in enumerate(value)]
    raise TypeError(f"{path or '<root>'} has unsupported type {type(value).__name__}")


def _freeze_json(value: object, path: str) -> FrozenJsonValue:
    """Copy and recursively freeze one open JSON value at record construction."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path or '<root>'} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, FrozenJsonValue] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path or '<root>'} has unsupported key type "
                    f"{type(key).__name__}"
                )
            frozen[key] = _freeze_json(nested, _child(path, key))
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(nested, _item(path, index))
            for index, nested in enumerate(value)
        )
    raise TypeError(f"{path or '<root>'} has unsupported type {type(value).__name__}")


class _Record:
    """Shared JSON handoff for the concrete Neutral Scene records."""

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize this record recursively to JSON-compatible standard types."""
        payload = _json_value(self, "")
        return cast(dict[str, JsonValue], payload)


def _load(
    record_type: type[RecordType],
    data: object,
    path: str,
    converters: Mapping[str, Converter] | None = None,
) -> RecordType:
    """Strictly rebuild one concrete dataclass while retaining nested error paths."""
    payload = _json_value(data, path)
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must be a mapping, got {type(data).__name__}")

    record_fields = fields(record_type)
    expected = tuple(record_field.name for record_field in record_fields)
    required = {
        record_field.name
        for record_field in record_fields
        if record_field.default is MISSING
        and record_field.default_factory is MISSING
    }
    missing = [name for name in expected if name in required and name not in payload]
    if missing:
        raise ValueError(f"{path} is missing field {missing[0]}")
    unexpected = [name for name in payload if name not in expected]
    if unexpected:
        raise ValueError(f"{path} has unexpected field {unexpected[0]}")

    values: dict[str, object] = dict(payload)
    for name, converter in (converters or {}).items():
        if name in values:
            values[name] = converter(values[name], _child(path, name))
    try:
        return record_type(**values)
    except ValueError as error:
        raise ValueError(_qualified_error(str(error), path, expected)) from None


def _qualified_error(message: str, path: str, field_names: tuple[str, ...]) -> str:
    """Replace a constructor's local field prefix with its enclosing record path."""
    location, separator, detail = message.partition(" ")
    for field_name in field_names:
        direct = location == field_name or location.startswith(
            (f"{field_name}.", f"{field_name}[")
        )
        marker = f".{field_name}"
        nested_index = location.find(marker)
        if direct:
            suffix = location[len(field_name):]
        elif nested_index >= 0:
            suffix = location[nested_index + len(marker):]
        else:
            continue
        qualified = f"{_child(path, field_name)}{suffix}"
        return f"{qualified}{separator}{detail}"
    return f"{path}: {message}"


def _record_converter(
    record_type: type[RecordType],
    converters: Mapping[str, Converter] | None = None,
) -> Converter:
    """Build a nested converter for one concrete record type."""
    def convert(value: object, path: str) -> RecordType:
        """Rebuild one nested concrete record at its enclosing payload path."""
        return _load(record_type, value, path, converters)

    return convert


def _optional_record_converter(
    record_type: type[RecordType],
    converters: Mapping[str, Converter] | None = None,
) -> Converter:
    """Build a converter for a nullable nested record."""
    def convert(value: object, path: str) -> RecordType | None:
        """Keep null distinct from a present nested record."""
        if value is None:
            return None
        return _load(record_type, value, path, converters)

    return convert


def _record_sequence_converter(
    record_type: type[RecordType],
    converters: Mapping[str, Converter] | None = None,
) -> Converter:
    """Build an ordered nested-record sequence converter."""
    def convert(value: object, path: str) -> tuple[RecordType, ...]:
        """Rebuild records in source order at precise indexed paths."""
        if not isinstance(value, list):
            raise ValueError(f"{path} must be an ordered record sequence")
        return tuple(
            _load(record_type, nested, _item(path, index), converters)
            for index, nested in enumerate(value)
        )

    return convert
def _stable_id(value: object, path: str, *, optional: bool = False) -> str | None:
    """Validate a required or optional stable string identifier."""
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string id")
    return value


def _text(value: object, path: str, *, optional: bool = False) -> str | None:
    """Validate a required or optional non-empty text fact."""
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _refs(value: object, path: str) -> tuple[str, ...]:
    """Validate and freeze an ordered sequence of stable references."""
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{path} must be an ordered sequence of string ids")
    result: list[str] = []
    for index, reference in enumerate(value):
        validated = _stable_id(reference, _item(path, index))
        assert validated is not None
        result.append(validated)
    return tuple(result)


def _number(value: object, path: str, *, positive: bool = False) -> float:
    """Validate a finite number, optionally requiring strict positivity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    try:
        result = float(value)
    except OverflowError:
        raise ValueError(f"{path} must be a finite number") from None
    if not math.isfinite(result) or (positive and result <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise ValueError(f"{path} must be a {qualifier} number")
    return result


def _vector(value: object, path: str) -> Vector3:
    """Validate and freeze one finite three-dimensional vector."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{path} must contain exactly three finite numbers")
    return cast(
        Vector3,
        tuple(_number(component, _item(path, index)) for index, component in enumerate(value)),
    )


def _matrix(value: object, path: str, size: int) -> tuple[tuple[float, ...], ...]:
    """Validate and freeze a finite square matrix."""
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{path} must be a finite {size}x{size} matrix")
    result: list[tuple[float, ...]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, (list, tuple)) or len(row) != size:
            raise ValueError(f"{path} must be a finite {size}x{size} matrix")
        result.append(
            tuple(
                _number(component, _item(_item(path, row_index), column_index))
                for column_index, component in enumerate(row)
            )
        )
    return tuple(result)


def _json_object(value: object, path: str) -> Mapping[str, FrozenJsonValue]:
    """Copy and recursively freeze an open factual JSON object."""
    result = _freeze_json(value, path)
    if not isinstance(result, Mapping):
        raise ValueError(f"{path} must be a JSON object")
    return result


def _json_sequence(value: object, path: str) -> tuple[FrozenJsonValue, ...]:
    """Copy and recursively freeze an ordered sequence of open JSON facts."""
    result = _freeze_json(value, path)
    if not isinstance(result, tuple):
        raise ValueError(f"{path} must be an ordered JSON sequence")
    return result


def _unit(value: object, path: str) -> str:
    """Validate one canonical length-unit token without transforming coordinates."""
    if not isinstance(value, str) or value not in ALLOWED_LENGTH_UNITS:
        raise ValueError(f"{path} must be one of {sorted(ALLOWED_LENGTH_UNITS)}")
    return value


def _ratio(value: object, path: str) -> float | None:
    """Validate an optional objective ratio in the closed unit interval."""
    if value is None:
        return None
    result = _number(value, path)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{path} must be between 0 and 1")
    return result


def _record_tuple(
    value: object,
    record_type: type[RecordType],
    path: str,
) -> tuple[RecordType, ...]:
    """Validate and freeze already-constructed nested records."""
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{path} must be an ordered record sequence")
    for index, record in enumerate(value):
        if not isinstance(record, record_type):
            raise ValueError(f"{_item(path, index)} must be {record_type.__name__}")
    return tuple(value)


@dataclass(frozen=True)
class AnalysisPlane(_Record):
    """Named analysis plane with a finite origin and orthonormal basis."""

    __hash__ = None

    name: str
    origin: Vector3
    basis: Matrix3

    def __post_init__(self) -> None:
        """Validate the plane origin and reject scale or shear in its basis."""
        object.__setattr__(self, "name", _text(self.name, "analysis_plane.name"))
        object.__setattr__(self, "origin", _vector(self.origin, "analysis_plane.origin"))
        basis = _matrix(self.basis, "analysis_plane.basis", 3)
        for index, axis in enumerate(basis):
            length = math.sqrt(sum(component * component for component in axis))
            if not math.isclose(length, 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"analysis_plane.basis[{index}] must be unit length")
        for first in range(3):
            for second in range(first + 1, 3):
                dot = sum(basis[first][index] * basis[second][index] for index in range(3))
                if not math.isclose(dot, 0.0, rel_tol=0.0, abs_tol=1e-9):
                    raise ValueError("analysis_plane.basis must be orthonormal")
        object.__setattr__(self, "basis", basis)

    @classmethod
    def from_dict(cls, data: object) -> AnalysisPlane:
        """Reconstruct and validate an analysis-plane mapping."""
        return _load(cls, data, "analysis_plane")


@dataclass(frozen=True)
class UncertaintyRecord(_Record):
    """Unavailable or uncertain evidence without an inferred score."""

    __hash__ = None

    code: str
    message: str
    source_refs: tuple[str, ...]
    operation: str
    severity: str
    details: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate uncertainty identity, references, operation, and details."""
        object.__setattr__(self, "code", _text(self.code, "uncertainty.code"))
        object.__setattr__(self, "message", _text(self.message, "uncertainty.message"))
        object.__setattr__(self, "source_refs", _refs(self.source_refs, "uncertainty.source_refs"))
        object.__setattr__(self, "operation", _text(self.operation, "uncertainty.operation"))
        object.__setattr__(self, "severity", _text(self.severity, "uncertainty.severity"))
        object.__setattr__(self, "details", _json_object(self.details, "uncertainty.details"))

    @classmethod
    def from_dict(cls, data: object) -> UncertaintyRecord:
        """Reconstruct and validate an uncertainty mapping."""
        return _load(cls, data, "uncertainty")


@dataclass(frozen=True)
class AnalysisContext(_Record):
    """Source, coordinate, tolerance, capability, and query context."""

    __hash__ = None

    contract_version: str
    source_schema: str
    adapter_version: str
    source_length_unit: str
    analysis_length_unit: str
    world_coordinate_system: Mapping[str, FrozenJsonValue]
    level_references: tuple[str, ...]
    analysis_plane: AnalysisPlane
    geometry_tolerance: float
    topology_tolerance: float
    walking_body_profiles: tuple[FrozenJsonValue, ...]
    visual_height_bands: tuple[FrozenJsonValue, ...]
    capability_flags: Mapping[str, bool]
    input_mode: str

    def __post_init__(self) -> None:
        """Validate the complete versioned adapter handoff context."""
        if self.contract_version != NEUTRAL_SCENE_V2:
            raise ValueError(f"contract_version must be exactly {NEUTRAL_SCENE_V2!r}")
        object.__setattr__(self, "source_schema", _text(self.source_schema, "source_schema"))
        object.__setattr__(self, "adapter_version", _text(self.adapter_version, "adapter_version"))
        object.__setattr__(self, "source_length_unit", _unit(self.source_length_unit, "context.source_length_unit"))
        object.__setattr__(self, "analysis_length_unit", _unit(self.analysis_length_unit, "context.analysis_length_unit"))
        object.__setattr__(self, "world_coordinate_system", _json_object(self.world_coordinate_system, "world_coordinate_system"))
        object.__setattr__(self, "level_references", _refs(self.level_references, "level_references"))
        if not isinstance(self.analysis_plane, AnalysisPlane):
            raise ValueError("analysis_plane must be an AnalysisPlane")
        object.__setattr__(self, "geometry_tolerance", _number(self.geometry_tolerance, "geometry_tolerance", positive=True))
        object.__setattr__(self, "topology_tolerance", _number(self.topology_tolerance, "topology_tolerance", positive=True))
        object.__setattr__(self, "walking_body_profiles", _json_sequence(self.walking_body_profiles, "walking_body_profiles"))
        object.__setattr__(self, "visual_height_bands", _json_sequence(self.visual_height_bands, "visual_height_bands"))
        if not isinstance(self.capability_flags, Mapping) or not all(
            isinstance(name, str) and isinstance(available, bool)
            for name, available in self.capability_flags.items()
        ):
            raise ValueError("capability_flags must map string names to booleans")
        object.__setattr__(
            self,
            "capability_flags",
            MappingProxyType(dict(self.capability_flags)),
        )
        if not isinstance(self.input_mode, str) or self.input_mode not in ALLOWED_INPUT_MODES:
            raise ValueError(f"context.input_mode must be one of {sorted(ALLOWED_INPUT_MODES)}")

    @classmethod
    def from_dict(cls, data: object) -> AnalysisContext:
        """Reconstruct and validate an analysis-context mapping."""
        return _load(
            cls,
            data,
            "context",
            {"analysis_plane": _record_converter(AnalysisPlane)},
        )


@dataclass(frozen=True)
class AnalysisDomain(_Record):
    """Explicit spatial extent selected for analysis."""

    __hash__ = None

    id: str
    geometry_refs: tuple[str, ...]
    source_id: str | None
    selection_method: str
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate domain identity, geometry, selection, and evidence."""
        object.__setattr__(self, "id", _stable_id(self.id, "analysis_domain.id"))
        object.__setattr__(self, "geometry_refs", _refs(self.geometry_refs, "analysis_domain.geometry_refs"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "analysis_domain.source_id", optional=True))
        object.__setattr__(self, "selection_method", _text(self.selection_method, "analysis_domain.selection_method"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "analysis_domain.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "analysis_domain.uncertainties"))

    @classmethod
    def from_dict(cls, data: object) -> AnalysisDomain:
        """Reconstruct and validate an analysis-domain mapping."""
        return _load(
            cls,
            data,
            "analysis_domain",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


_IDENTITY_4: Matrix4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


@dataclass(frozen=True)
class SourceObject(_Record):
    """Source identity, placement, relationships, and factual references."""

    __hash__ = None

    id: str
    source_id: str | None = None
    source_role: str | None = None
    source_class: str | None = None
    world_transform: Matrix4 = _IDENTITY_4
    level_ref: str | None = None
    container_refs: tuple[str, ...] = ()
    geometry_refs: tuple[str, ...] = ()
    type_ref: str | None = None
    group_refs: tuple[str, ...] = ()
    material_refs: tuple[str, ...] = ()
    surface_refs: tuple[str, ...] = ()
    opening_refs: tuple[str, ...] = ()
    authored_local_frame: Mapping[str, FrozenJsonValue] | None = None
    factual_properties: Mapping[str, FrozenJsonValue] = field(
        default_factory=dict
    )
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate object identity, transform, references, and open facts."""
        object.__setattr__(self, "id", _stable_id(self.id, "source_object.id"))
        for name in ("source_id", "level_ref", "type_ref"):
            object.__setattr__(self, name, _stable_id(getattr(self, name), f"source_object.{name}", optional=True))
        for name in ("source_role", "source_class"):
            object.__setattr__(self, name, _text(getattr(self, name), f"source_object.{name}", optional=True))
        object.__setattr__(self, "world_transform", _matrix(self.world_transform, "world_transform", 4))
        for name in ("container_refs", "geometry_refs", "group_refs", "material_refs", "surface_refs", "opening_refs"):
            object.__setattr__(self, name, _refs(getattr(self, name), f"source_object.{name}"))
        if self.authored_local_frame is not None:
            object.__setattr__(self, "authored_local_frame", _json_object(self.authored_local_frame, "source_object.authored_local_frame"))
        object.__setattr__(
            self,
            "factual_properties",
            _json_object(
                self.factual_properties,
                "source_object.factual_properties",
            ),
        )
        object.__setattr__(self, "provenance", _json_object(self.provenance, "source_object.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "source_object.uncertainties"))
        if not self.geometry_refs and not any(
            uncertainty.code == MISSING_GEOMETRY_UNCERTAINTY
            for uncertainty in self.uncertainties
        ):
            raise ValueError(
                "source_object.geometry_refs must contain a reference or "
                f"uncertainties must include {MISSING_GEOMETRY_UNCERTAINTY}"
            )

    @classmethod
    def from_dict(cls, data: object) -> SourceObject:
        """Reconstruct and validate a source-object mapping."""
        return _load(
            cls,
            data,
            "source_object",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


@dataclass(frozen=True)
class MeshGeometry3D(_Record):
    """Triangulated source geometry used for transport and later queries."""

    __hash__ = None

    id: str
    vertices: tuple[Vector3, ...]
    triangle_indices: tuple[tuple[int, int, int], ...]
    normals: tuple[Vector3, ...]
    is_manifold: bool | None
    is_closed: bool | None
    local_to_world_provenance: Mapping[str, FrozenJsonValue]
    source_representation_id: str | None
    tessellation_settings: Mapping[str, FrozenJsonValue]
    units: str

    def __post_init__(self) -> None:
        """Validate finite mesh data, diagnostics, provenance, and units."""
        object.__setattr__(self, "id", _stable_id(self.id, "mesh.id"))
        if not isinstance(self.vertices, (list, tuple)):
            raise ValueError("vertices must be an ordered sequence")
        vertices = tuple(_vector(vertex, _item("vertices", index)) for index, vertex in enumerate(self.vertices))
        object.__setattr__(self, "vertices", vertices)
        if not isinstance(self.triangle_indices, (list, tuple)):
            raise ValueError("triangle_indices must be an ordered sequence")
        triangles: list[tuple[int, int, int]] = []
        for triangle_index, triangle in enumerate(self.triangle_indices):
            path = _item("triangle_indices", triangle_index)
            if not isinstance(triangle, (list, tuple)) or len(triangle) != 3:
                raise ValueError(f"{path} must contain exactly three indices")
            indices: list[int] = []
            for index in triangle:
                if isinstance(index, bool) or not isinstance(index, int):
                    raise ValueError(f"{path} must contain integer indices")
                if index < 0 or index >= len(vertices):
                    raise ValueError(f"{path} index {index} is outside vertices")
                indices.append(index)
            triangles.append(cast(tuple[int, int, int], tuple(indices)))
        object.__setattr__(self, "triangle_indices", tuple(triangles))
        if not isinstance(self.normals, (list, tuple)):
            raise ValueError("normals must be an ordered sequence")
        object.__setattr__(self, "normals", tuple(_vector(normal, _item("normals", index)) for index, normal in enumerate(self.normals)))
        for name in ("is_manifold", "is_closed"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean or null")
        object.__setattr__(self, "local_to_world_provenance", _json_object(self.local_to_world_provenance, "local_to_world_provenance"))
        object.__setattr__(self, "source_representation_id", _stable_id(self.source_representation_id, "source_representation_id", optional=True))
        object.__setattr__(self, "tessellation_settings", _json_object(self.tessellation_settings, "tessellation_settings"))
        object.__setattr__(self, "units", _unit(self.units, "mesh.units"))

    @classmethod
    def from_dict(cls, data: object) -> MeshGeometry3D:
        """Reconstruct and validate a mesh-geometry mapping."""
        return _load(cls, data, "mesh")


@dataclass(frozen=True)
class MaterialFact(_Record):
    """Material identity and separate physical and viewport optical facts."""

    __hash__ = None

    id: str
    source_id: str | None
    identity: str | None
    visible_transmittance: float | None
    viewport_transparency: float | None
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate material identity, optical observations, and evidence."""
        object.__setattr__(self, "id", _stable_id(self.id, "material.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "material.source_id", optional=True))
        object.__setattr__(self, "identity", _text(self.identity, "material.identity", optional=True))
        object.__setattr__(self, "visible_transmittance", _ratio(self.visible_transmittance, "material.visible_transmittance"))
        object.__setattr__(self, "viewport_transparency", _ratio(self.viewport_transparency, "material.viewport_transparency"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "material.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "material.uncertainties"))

    @classmethod
    def from_dict(cls, data: object) -> MaterialFact:
        """Reconstruct and validate a material-fact mapping."""
        return _load(
            cls,
            data,
            "material",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


@dataclass(frozen=True)
class SurfaceFact(_Record):
    """Surface identity, appearance, elevation, slope, and geometry facts."""

    __hash__ = None

    id: str
    source_id: str | None
    host_refs: tuple[str, ...]
    identity: str | None
    color: FrozenJsonValue
    finish: FrozenJsonValue
    texture: FrozenJsonValue
    elevation: FrozenJsonValue
    slope: FrozenJsonValue
    geometry_refs: tuple[str, ...]
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate surface identity, references, facts, and uncertainty."""
        object.__setattr__(self, "id", _stable_id(self.id, "surface.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "surface.source_id", optional=True))
        object.__setattr__(self, "host_refs", _refs(self.host_refs, "surface.host_refs"))
        object.__setattr__(self, "identity", _text(self.identity, "surface.identity", optional=True))
        for name in ("color", "finish", "texture", "elevation", "slope"):
            object.__setattr__(self, name, _freeze_json(getattr(self, name), f"surface.{name}"))
        object.__setattr__(self, "geometry_refs", _refs(self.geometry_refs, "surface.geometry_refs"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "surface.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "surface.uncertainties"))

    @classmethod
    def from_dict(cls, data: object) -> SurfaceFact:
        """Reconstruct and validate a surface-fact mapping."""
        return _load(
            cls,
            data,
            "surface",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


@dataclass(frozen=True)
class AuthoredGroup(_Record):
    """Explicit source grouping relationship without inferred membership."""

    __hash__ = None

    id: str
    source_id: str | None
    member_refs: tuple[str, ...]
    group_role: str
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate authored group identity, members, role, and provenance."""
        object.__setattr__(self, "id", _stable_id(self.id, "authored_group.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "authored_group.source_id", optional=True))
        object.__setattr__(self, "member_refs", _refs(self.member_refs, "authored_group.member_refs"))
        object.__setattr__(self, "group_role", _text(self.group_role, "authored_group.group_role"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "authored_group.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> AuthoredGroup:
        """Reconstruct and validate an authored-group mapping."""
        return _load(cls, data, "authored_group")


@dataclass(frozen=True)
class AuthoredGridAxis(_Record):
    """Explicit source grid axis with ordered curve geometry and identifiers."""

    __hash__ = None

    id: str
    source_id: str | None
    curve_points: tuple[Vector3, ...]
    branch_identifier: str | None
    list_identifier: str | None
    same_sense: bool | None = None
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate axis identity, curve points, labels, and provenance."""
        object.__setattr__(self, "id", _stable_id(self.id, "authored_grid_axis.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "authored_grid_axis.source_id", optional=True))
        if not isinstance(self.curve_points, (list, tuple)) or len(self.curve_points) < 2:
            raise ValueError("authored_grid_axis.curve_points needs at least two points")
        object.__setattr__(self, "curve_points", tuple(_vector(point, _item("authored_grid_axis.curve_points", index)) for index, point in enumerate(self.curve_points)))
        for name in ("branch_identifier", "list_identifier"):
            object.__setattr__(self, name, _text(getattr(self, name), f"authored_grid_axis.{name}", optional=True))
        if self.same_sense is not None and not isinstance(self.same_sense, bool):
            raise ValueError("authored_grid_axis.same_sense must be a boolean or null")
        object.__setattr__(self, "provenance", _json_object(self.provenance, "authored_grid_axis.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> AuthoredGridAxis:
        """Reconstruct and validate an authored-grid-axis mapping."""
        return _load(cls, data, "authored_grid_axis")


@dataclass(frozen=True)
class AuthoredGrid(_Record):
    """Explicit source grid referencing separately addressable axes."""

    __hash__ = None

    id: str
    source_id: str | None
    axis_refs: tuple[str, ...]
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate grid identity, ordered axis references, and provenance."""
        object.__setattr__(self, "id", _stable_id(self.id, "authored_grid.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "authored_grid.source_id", optional=True))
        object.__setattr__(self, "axis_refs", _refs(self.axis_refs, "authored_grid.axis_refs"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "authored_grid.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> AuthoredGrid:
        """Reconstruct and validate an authored-grid mapping."""
        return _load(cls, data, "authored_grid")


@dataclass(frozen=True)
class AuthoredAffordanceZone(_Record):
    """Explicit functional use geometry supplied by the source author."""

    __hash__ = None

    id: str
    geometry_refs: tuple[str, ...]
    vertical_extent: tuple[float, float]
    purpose: str
    task_facts: Mapping[str, FrozenJsonValue]
    source_furniture_refs: tuple[str, ...]
    source_id: str | None = None
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate affordance geometry, vertical extent, purpose, and evidence."""
        object.__setattr__(self, "id", _stable_id(self.id, "authored_affordance.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "authored_affordance.source_id", optional=True))
        object.__setattr__(self, "geometry_refs", _refs(self.geometry_refs, "authored_affordance.geometry_refs"))
        if not isinstance(self.vertical_extent, (list, tuple)) or len(self.vertical_extent) != 2:
            raise ValueError("authored_affordance.vertical_extent must contain two values")
        extent = (
            _number(self.vertical_extent[0], "authored_affordance.vertical_extent[0]"),
            _number(self.vertical_extent[1], "authored_affordance.vertical_extent[1]"),
        )
        if extent[1] < extent[0]:
            raise ValueError("authored_affordance.vertical_extent must be ordered")
        object.__setattr__(self, "vertical_extent", extent)
        object.__setattr__(self, "purpose", _text(self.purpose, "authored_affordance.purpose"))
        object.__setattr__(self, "task_facts", _json_object(self.task_facts, "authored_affordance.task_facts"))
        object.__setattr__(self, "source_furniture_refs", _refs(self.source_furniture_refs, "authored_affordance.source_furniture_refs"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "authored_affordance.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "authored_affordance.uncertainties"))

    @classmethod
    def from_dict(cls, data: object) -> AuthoredAffordanceZone:
        """Reconstruct and validate an authored-affordance mapping."""
        return _load(
            cls,
            data,
            "authored_affordance",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


@dataclass(frozen=True)
class SourceOpening(_Record):
    """Explicit source opening and its host and geometry references."""

    __hash__ = None

    id: str
    source_id: str | None
    host_refs: tuple[str, ...]
    geometry_refs: tuple[str, ...]
    opening_kind: str
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate opening identity, hosts, geometry, kind, and evidence."""
        object.__setattr__(self, "id", _stable_id(self.id, "opening.id"))
        object.__setattr__(self, "source_id", _stable_id(self.source_id, "opening.source_id", optional=True))
        object.__setattr__(self, "host_refs", _refs(self.host_refs, "opening.host_refs"))
        object.__setattr__(self, "geometry_refs", _refs(self.geometry_refs, "opening.geometry_refs"))
        object.__setattr__(self, "opening_kind", _text(self.opening_kind, "opening.opening_kind"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "opening.provenance"))
        object.__setattr__(self, "uncertainties", _record_tuple(self.uncertainties, UncertaintyRecord, "opening.uncertainties"))

    @classmethod
    def from_dict(cls, data: object) -> SourceOpening:
        """Reconstruct and validate a source-opening mapping."""
        return _load(
            cls,
            data,
            "opening",
            {"uncertainties": _record_sequence_converter(UncertaintyRecord)},
        )


@dataclass(frozen=True)
class NeutralSceneV2(_Record):
    """Top-level source-independent aggregate for Neutral Scene v2 facts."""

    __hash__ = None

    context: AnalysisContext
    analysis_domain: AnalysisDomain | None = None
    source_objects: tuple[SourceObject, ...] = ()
    geometries: tuple[MeshGeometry3D, ...] = ()
    materials: tuple[MaterialFact, ...] = ()
    surfaces: tuple[SurfaceFact, ...] = ()
    authored_groups: tuple[AuthoredGroup, ...] = ()
    authored_grids: tuple[AuthoredGrid, ...] = ()
    authored_grid_axes: tuple[AuthoredGridAxis, ...] = ()
    authored_affordances: tuple[AuthoredAffordanceZone, ...] = ()
    openings: tuple[SourceOpening, ...] = ()
    uncertainties: tuple[UncertaintyRecord, ...] = ()

    def __post_init__(self) -> None:
        """Validate nested record types while preserving source ordering."""
        if not isinstance(self.context, AnalysisContext):
            raise ValueError("context must be an AnalysisContext")
        if self.analysis_domain is not None and not isinstance(self.analysis_domain, AnalysisDomain):
            raise ValueError("analysis_domain must be an AnalysisDomain or null")
        record_fields: tuple[tuple[str, type[_Record]], ...] = (
            ("source_objects", SourceObject),
            ("geometries", MeshGeometry3D),
            ("materials", MaterialFact),
            ("surfaces", SurfaceFact),
            ("authored_groups", AuthoredGroup),
            ("authored_grids", AuthoredGrid),
            ("authored_grid_axes", AuthoredGridAxis),
            ("authored_affordances", AuthoredAffordanceZone),
            ("openings", SourceOpening),
            ("uncertainties", UncertaintyRecord),
        )
        for name, record_type in record_fields:
            object.__setattr__(self, name, _record_tuple(getattr(self, name), record_type, name))

    @classmethod
    def from_dict(cls, data: object) -> NeutralSceneV2:
        """Reconstruct and validate a complete Neutral Scene v2 mapping."""
        uncertainty_items = _record_sequence_converter(UncertaintyRecord)
        with_uncertainty = {"uncertainties": uncertainty_items}
        return _load(
            cls,
            data,
            "neutral_scene",
            {
                "context": _record_converter(
                    AnalysisContext,
                    {"analysis_plane": _record_converter(AnalysisPlane)},
                ),
                "analysis_domain": _optional_record_converter(
                    AnalysisDomain, with_uncertainty
                ),
                "source_objects": _record_sequence_converter(
                    SourceObject, with_uncertainty
                ),
                "geometries": _record_sequence_converter(MeshGeometry3D),
                "materials": _record_sequence_converter(
                    MaterialFact, with_uncertainty
                ),
                "surfaces": _record_sequence_converter(
                    SurfaceFact, with_uncertainty
                ),
                "authored_groups": _record_sequence_converter(AuthoredGroup),
                "authored_grids": _record_sequence_converter(AuthoredGrid),
                "authored_grid_axes": _record_sequence_converter(AuthoredGridAxis),
                "authored_affordances": _record_sequence_converter(
                    AuthoredAffordanceZone, with_uncertainty
                ),
                "openings": _record_sequence_converter(
                    SourceOpening, with_uncertainty
                ),
                "uncertainties": uncertainty_items,
            },
        )


__all__ = [
    "ALLOWED_INPUT_MODES",
    "ALLOWED_LENGTH_UNITS",
    "MISSING_GEOMETRY_UNCERTAINTY",
    "NEUTRAL_SCENE_V2",
    "AnalysisContext",
    "AnalysisDomain",
    "AnalysisPlane",
    "AuthoredAffordanceZone",
    "AuthoredGrid",
    "AuthoredGridAxis",
    "AuthoredGroup",
    "MaterialFact",
    "MeshGeometry3D",
    "NeutralSceneV2",
    "SourceObject",
    "SourceOpening",
    "SurfaceFact",
    "UncertaintyRecord",
]
