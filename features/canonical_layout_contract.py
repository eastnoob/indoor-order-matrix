"""Source-independent records for the clean-room layout descriptor contract."""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence, TypeAlias, TypeVar, cast


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
FrozenJsonValue: TypeAlias = JsonScalar | tuple["FrozenJsonValue", ...] | Mapping[str, "FrozenJsonValue"]
Vector2: TypeAlias = tuple[float, float]
Vector3: TypeAlias = tuple[float, float, float]
Matrix3: TypeAlias = tuple[Vector3, Vector3, Vector3]
Matrix4: TypeAlias = tuple[tuple[float, float, float, float], ...]

ALLOWED_LENGTH_UNITS = frozenset(
    {"nm", "um", "mm", "cm", "dm", "m", "dam", "hm", "km", "in", "ft"}
)
_UNIT_TO_METRES = {
    "nm": 1e-9,
    "um": 1e-6,
    "mm": 1e-3,
    "cm": 1e-2,
    "dm": 1e-1,
    "m": 1.0,
    "dam": 1e1,
    "hm": 1e2,
    "km": 1e3,
    "in": 0.0254,
    "ft": 0.3048,
}
_IDENTITY_4: Matrix4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)

RecordType = TypeVar("RecordType", bound="_Record")


class ResultStatus(str, Enum):
    """Status vocabulary that keeps unavailable states distinct from zero."""

    COMPUTED = "computed"
    UNDEFINED = "undefined"
    INVALID = "invalid"
    NOT_AVAILABLE = "not_available"
    NOT_EVALUATED = "not_evaluated"


def _path_item(path: str, index: int) -> str:
    """Return a stable error path for one sequence item."""
    return f"{path}[{index}]"


def _path_field(path: str, name: str) -> str:
    """Return a stable error path for one named field."""
    return f"{path}.{name}" if path else name


def _text(value: object, path: str, *, optional: bool = False) -> str | None:
    """Validate required or optional non-empty text."""
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _number(value: object, path: str, *, positive: bool = False) -> float:
    """Validate a finite numeric value, optionally requiring positivity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise ValueError(f"{path} must be a {qualifier} number")
    return result


def _unit(value: object, path: str) -> str:
    """Validate a canonical length-unit token."""
    if not isinstance(value, str) or value not in ALLOWED_LENGTH_UNITS:
        raise ValueError(f"{path} must be a supported length unit")
    return value


def _vector(value: object, path: str, size: int) -> tuple[float, ...]:
    """Validate and freeze a finite vector."""
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{path} must contain exactly {size} finite numbers")
    return tuple(_number(item, _path_item(path, index)) for index, item in enumerate(value))


def _matrix(value: object, path: str, size: int) -> tuple[tuple[float, ...], ...]:
    """Validate and freeze a finite square matrix."""
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{path} must be a finite {size}x{size} matrix")
    rows = []
    for row_index, row in enumerate(value):
        rows.append(_vector(row, _path_item(path, row_index), size))
    return tuple(rows)


def _refs(value: object, path: str, *, sort: bool = False) -> tuple[str, ...]:
    """Validate stable string references and optionally canonicalize their order."""
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{path} must be an ordered sequence of ids")
    result = tuple(_text(item, _path_item(path, index)) for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise ValueError(f"{path} must not contain duplicate ids")
    return tuple(sorted(result)) if sort else result


def _freeze_json(value: object, path: str) -> FrozenJsonValue:
    """Recursively copy JSON-compatible values and reject non-finite floats."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        result: dict[str, FrozenJsonValue] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} has a non-string key")
            result[key] = _freeze_json(nested, _path_field(path, key))
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, _path_item(path, index)) for index, item in enumerate(value))
    if isinstance(value, Enum):
        return _freeze_json(value.value, path)
    raise TypeError(f"{path} has unsupported value type {type(value).__name__}")


def _json_object(value: object, path: str) -> Mapping[str, FrozenJsonValue]:
    """Freeze one JSON object and reject non-object provenance payloads."""
    frozen = _freeze_json(value, path)
    if not isinstance(frozen, Mapping):
        raise ValueError(f"{path} must be a JSON object")
    return frozen


def _json_value(value: object, path: str = "") -> JsonValue:
    """Convert frozen record state to ordinary JSON-compatible containers."""
    if isinstance(value, Enum):
        return _json_value(value.value, path)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path or '<root>'} contains a non-finite float")
        return value
    if isinstance(value, _Record):
        return {
            item.name: _json_value(getattr(value, item.name), _path_field(path, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _json_value(nested, _path_field(path, str(key))) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item, _path_item(path, index)) for index, item in enumerate(value)]
    raise TypeError(f"{path or '<root>'} has unsupported value type {type(value).__name__}")


def _load(record_type: type[RecordType], data: object, path: str, converters: Mapping[str, Any] | None = None) -> RecordType:
    """Rebuild one record with exact field and nested-record validation."""
    if not isinstance(data, Mapping):
        raise TypeError(f"{path} must be a JSON object")
    payload = dict(data)
    record_fields = fields(record_type)
    expected = {item.name for item in record_fields}
    missing = [
        item.name
        for item in record_fields
        if item.default is MISSING and item.default_factory is MISSING and item.name not in payload
    ]
    if missing:
        raise ValueError(f"{path} is missing field {missing[0]}")
    unexpected = [name for name in payload if name not in expected]
    if unexpected:
        raise ValueError(f"{path} has unexpected field {unexpected[0]}")
    for name, converter in (converters or {}).items():
        if name in payload:
            payload[name] = converter(payload[name], _path_field(path, name))
    return record_type(**payload)


def _record_converter(record_type: type[RecordType], converters: Mapping[str, Any] | None = None):
    """Build a strict nested-record converter."""
    def convert(value: object, path: str) -> RecordType:
        """Rebuild one nested record at a precise JSON path."""
        return _load(record_type, value, path, converters)

    return convert


def _record_sequence_converter(record_type: type[RecordType], converters: Mapping[str, Any] | None = None):
    """Build a converter for an ordered sequence of nested records."""
    def convert(value: object, path: str) -> tuple[RecordType, ...]:
        """Rebuild each nested record while preserving source sequence order."""
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{path} must be an ordered record sequence")
        return tuple(_load(record_type, item, _path_item(path, index), converters) for index, item in enumerate(value))

    return convert


def _enum_converter(enum_type: type[Enum]):
    """Build a strict converter for one serialized enum value."""
    def convert(value: object, path: str) -> Enum:
        """Rebuild one enum and report unknown values at the field path."""
        try:
            return enum_type(value)
        except (TypeError, ValueError):
            raise ValueError(f"{path} has unknown status {value!r}") from None

    return convert


def _orthonormal_basis(value: object, path: str) -> Matrix3:
    """Validate a three-dimensional orthonormal basis."""
    basis = cast(Matrix3, _matrix(value, path, 3))
    for index, axis in enumerate(basis):
        length = math.sqrt(sum(component * component for component in axis))
        if not math.isclose(length, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"{path}[{index}] must be orthonormal and unit length")
    for first in range(3):
        for second in range(first + 1, 3):
            dot = sum(basis[first][index] * basis[second][index] for index in range(3))
            if not math.isclose(dot, 0.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"{path} must be orthonormal")
    return basis


class _Record:
    """Shared strict serialization behavior for canonical records."""

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the immutable record to ordinary JSON-compatible values."""
        return cast(dict[str, JsonValue], _json_value(self))


@dataclass(frozen=True)
class AnalysisFrame(_Record):
    """Coordinate frame, units, plane, and positive geometry tolerances."""

    frame_id: str
    origin: Vector3
    basis: Matrix3
    source_unit: str
    analysis_unit: str
    geometry_tolerance: float
    topology_tolerance: float
    plane: str = "xy"
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate frame identity, orthonormal basis, units, and tolerances."""
        object.__setattr__(self, "frame_id", _text(self.frame_id, "analysis_frame.frame_id"))
        object.__setattr__(self, "origin", cast(Vector3, _vector(self.origin, "analysis_frame.origin", 3)))
        object.__setattr__(self, "basis", _orthonormal_basis(self.basis, "analysis_frame.basis"))
        object.__setattr__(self, "source_unit", _unit(self.source_unit, "analysis_frame.source_unit"))
        object.__setattr__(self, "analysis_unit", _unit(self.analysis_unit, "analysis_frame.analysis_unit"))
        object.__setattr__(self, "geometry_tolerance", _number(self.geometry_tolerance, "analysis_frame.geometry_tolerance", positive=True))
        object.__setattr__(self, "topology_tolerance", _number(self.topology_tolerance, "analysis_frame.topology_tolerance", positive=True))
        if self.plane not in {"xy", "xz", "yz"}:
            raise ValueError("analysis_frame.plane must be one of xy, xz, yz")
        object.__setattr__(self, "provenance", _json_object(self.provenance, "analysis_frame.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> "AnalysisFrame":
        """Reconstruct an analysis frame from an exact JSON object."""
        return _load(cls, data, "analysis_frame")


@dataclass(frozen=True)
class AxisSpec(_Record):
    """Explicit oriented axis declared in one analysis frame."""

    frame_id: str
    name: str
    unit_vector: Vector3
    direction_convention: str

    def __post_init__(self) -> None:
        """Validate frame reference, axis name, unit direction, and convention."""
        object.__setattr__(self, "frame_id", _text(self.frame_id, "axis.frame_id"))
        object.__setattr__(self, "name", _text(self.name, "axis.name"))
        vector = cast(Vector3, _vector(self.unit_vector, "axis.unit_vector", 3))
        if not math.isclose(math.sqrt(sum(item * item for item in vector)), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("axis.unit_vector must be unit length")
        object.__setattr__(self, "unit_vector", vector)
        object.__setattr__(self, "direction_convention", _text(self.direction_convention, "axis.direction_convention"))

    @classmethod
    def from_dict(cls, data: object) -> "AxisSpec":
        """Reconstruct an axis specification from an exact JSON object."""
        return _load(cls, data, "axis")


@dataclass(frozen=True)
class SourceObjectFact(_Record):
    """Factual source object identity and references without derived scores."""

    object_id: str
    semantic_type: str = "unknown"
    world_transform: Matrix4 = _IDENTITY_4
    geometry_refs: tuple[str, ...] = ()
    authored_group_refs: tuple[str, ...] = ()
    source_unit: str = "m"
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate source identity, transform, references, units, and provenance."""
        object.__setattr__(self, "object_id", _text(self.object_id, "source_object.object_id"))
        object.__setattr__(self, "semantic_type", _text(self.semantic_type, "source_object.semantic_type"))
        object.__setattr__(self, "world_transform", cast(Matrix4, _matrix(self.world_transform, "source_object.world_transform", 4)))
        object.__setattr__(self, "geometry_refs", _refs(self.geometry_refs, "source_object.geometry_refs", sort=True))
        object.__setattr__(self, "authored_group_refs", _refs(self.authored_group_refs, "source_object.authored_group_refs", sort=True))
        object.__setattr__(self, "source_unit", _unit(self.source_unit, "source_object.source_unit"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "source_object.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> "SourceObjectFact":
        """Reconstruct a source-object fact from an exact JSON object."""
        return _load(cls, data, "source_object")


@dataclass(frozen=True)
class SourceGeometry3D(_Record):
    """Triangulated source geometry with representation and transform provenance."""

    geometry_id: str
    object_id: str
    vertices: tuple[Vector3, ...]
    triangles: tuple[tuple[int, int, int], ...] = ()
    source_representation: str = "unknown"
    source_unit: str = "m"
    world_transform: Matrix4 = _IDENTITY_4
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate source mesh topology, units, transforms, and provenance."""
        object.__setattr__(self, "geometry_id", _text(self.geometry_id, "source_geometry.geometry_id"))
        object.__setattr__(self, "object_id", _text(self.object_id, "source_geometry.object_id"))
        vertices = tuple(cast(Vector3, _vector(item, _path_item("source_geometry.vertices", index), 3)) for index, item in enumerate(self.vertices))
        object.__setattr__(self, "vertices", vertices)
        if not isinstance(self.triangles, (list, tuple)):
            raise ValueError("source_geometry.triangles must be an ordered sequence")
        triangles = []
        for index, triangle in enumerate(self.triangles):
            path = _path_item("source_geometry.triangles", index)
            if not isinstance(triangle, (list, tuple)) or len(triangle) != 3:
                raise ValueError(f"{path} must contain three vertex indices")
            if any(isinstance(item, bool) or not isinstance(item, int) for item in triangle):
                raise ValueError(f"{path} must contain integer vertex indices")
            if any(item < 0 or item >= len(vertices) for item in triangle):
                raise ValueError(f"{path} contains an out-of-range vertex index")
            triangles.append(cast(tuple[int, int, int], tuple(triangle)))
        object.__setattr__(self, "triangles", tuple(triangles))
        object.__setattr__(self, "source_representation", _text(self.source_representation, "source_geometry.source_representation"))
        object.__setattr__(self, "source_unit", _unit(self.source_unit, "source_geometry.source_unit"))
        object.__setattr__(self, "world_transform", cast(Matrix4, _matrix(self.world_transform, "source_geometry.world_transform", 4)))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "source_geometry.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> "SourceGeometry3D":
        """Reconstruct source geometry from an exact JSON object."""
        return _load(cls, data, "source_geometry")


@dataclass(frozen=True)
class PlanGeometry(_Record):
    """Normalized plan geometry and explicit projection status."""

    object_id: str
    vertices: tuple[Vector2, ...]
    triangles: tuple[tuple[int, int, int], ...] = ()
    frame_id: str = ""
    unit: str = "m"
    source_representation: str = "unknown"
    method: str = "unknown"
    unit_conversion: float = 1.0
    status: ResultStatus = ResultStatus.COMPUTED
    reason: str | None = None
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate projected vertices, topology, status, and provenance fields."""
        object.__setattr__(self, "object_id", _text(self.object_id, "plan_geometry.object_id"))
        vertices = tuple(cast(Vector2, _vector(item, _path_item("plan_geometry.vertices", index), 2)) for index, item in enumerate(self.vertices))
        object.__setattr__(self, "vertices", vertices)
        if not isinstance(self.triangles, (list, tuple)):
            raise ValueError("plan_geometry.triangles must be an ordered sequence")
        triangles = []
        for index, triangle in enumerate(self.triangles):
            path = _path_item("plan_geometry.triangles", index)
            if not isinstance(triangle, (list, tuple)) or len(triangle) != 3:
                raise ValueError(f"{path} must contain three vertex indices")
            if any(isinstance(item, bool) or not isinstance(item, int) for item in triangle):
                raise ValueError(f"{path} must contain integer vertex indices")
            if any(item < 0 or item >= len(vertices) for item in triangle):
                raise ValueError(f"{path} contains an out-of-range vertex index")
            triangles.append(cast(tuple[int, int, int], tuple(triangle)))
        object.__setattr__(self, "triangles", tuple(triangles))
        object.__setattr__(self, "frame_id", _text(self.frame_id, "plan_geometry.frame_id"))
        object.__setattr__(self, "unit", _unit(self.unit, "plan_geometry.unit"))
        object.__setattr__(self, "source_representation", _text(self.source_representation, "plan_geometry.source_representation"))
        object.__setattr__(self, "method", _text(self.method, "plan_geometry.method"))
        object.__setattr__(self, "unit_conversion", _number(self.unit_conversion, "plan_geometry.unit_conversion", positive=True))
        status = ResultStatus(self.status)
        object.__setattr__(self, "status", status)
        reason = _text(self.reason, "plan_geometry.reason", optional=True)
        if status is ResultStatus.COMPUTED and reason is not None:
            raise ValueError("plan_geometry.reason must be null for computed geometry")
        if status is not ResultStatus.COMPUTED and reason is None:
            raise ValueError("plan_geometry.reason is required for non-computed geometry")
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "provenance", _json_object(self.provenance, "plan_geometry.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> "PlanGeometry":
        """Reconstruct normalized plan geometry from an exact JSON object."""
        return _load(cls, data, "plan_geometry", {"status": _enum_converter(ResultStatus)})


@dataclass(frozen=True)
class AuthoredGroupFact(_Record):
    """Explicit authored group membership without inferred semantic meaning."""

    group_id: str
    member_object_ids: tuple[str, ...]
    source_reference: str
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate group identity, canonical member references, and provenance."""
        object.__setattr__(self, "group_id", _text(self.group_id, "authored_group.group_id"))
        object.__setattr__(self, "member_object_ids", _refs(self.member_object_ids, "authored_group.member_object_ids", sort=True))
        object.__setattr__(self, "source_reference", _text(self.source_reference, "authored_group.source_reference"))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "authored_group.provenance"))

    @classmethod
    def from_dict(cls, data: object) -> "AuthoredGroupFact":
        """Reconstruct authored group facts from an exact JSON object."""
        return _load(cls, data, "authored_group")


@dataclass(frozen=True)
class CanonicalScene(_Record):
    """Complete clean-room scene facts and normalized geometry references."""

    frame: AnalysisFrame
    axes: tuple[AxisSpec, ...] = ()
    objects: tuple[SourceObjectFact, ...] = ()
    source_geometries: tuple[SourceGeometry3D, ...] = ()
    plan_geometries: tuple[PlanGeometry, ...] = ()
    authored_groups: tuple[AuthoredGroupFact, ...] = ()
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate nested record types and canonicalize stable record ordering."""
        if not isinstance(self.frame, AnalysisFrame):
            raise ValueError("canonical_scene.frame must be an AnalysisFrame")
        for name, record_type in (
            ("axes", AxisSpec),
            ("objects", SourceObjectFact),
            ("source_geometries", SourceGeometry3D),
            ("plan_geometries", PlanGeometry),
            ("authored_groups", AuthoredGroupFact),
        ):
            records = getattr(self, name)
            if not isinstance(records, (list, tuple)) or any(not isinstance(item, record_type) for item in records):
                raise ValueError(f"canonical_scene.{name} must contain {record_type.__name__} records")
            key = {
                "axes": lambda item: (item.frame_id, item.name),
                "objects": lambda item: item.object_id,
                "source_geometries": lambda item: item.geometry_id,
                "plan_geometries": lambda item: item.object_id,
                "authored_groups": lambda item: item.group_id,
            }[name]
            object.__setattr__(self, name, tuple(sorted(records, key=key)))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "canonical_scene.provenance"))
        _validate_scene_references(self)

    @property
    def groups(self) -> tuple[AuthoredGroupFact, ...]:
        """Expose authored groups under the concise geometry-facing name."""
        return self.authored_groups

    @classmethod
    def from_dict(cls, data: object) -> "CanonicalScene":
        """Reconstruct a complete canonical scene from an exact JSON object."""
        return _load(
            cls,
            data,
            "canonical_scene",
            {
                "frame": _record_converter(AnalysisFrame),
                "axes": _record_sequence_converter(AxisSpec),
                "objects": _record_sequence_converter(SourceObjectFact),
                "source_geometries": _record_sequence_converter(SourceGeometry3D),
                "plan_geometries": _record_sequence_converter(PlanGeometry, {"status": _enum_converter(ResultStatus)}),
                "authored_groups": _record_sequence_converter(AuthoredGroupFact),
            },
        )


@dataclass(frozen=True)
class DescriptorResult(_Record):
    """Auditable descriptor value with explicit status, scope, and provenance."""

    descriptor_id: str
    scope: str
    value: FrozenJsonValue | None
    status: ResultStatus
    algorithm_id: str
    unit: str | None = None
    parameters: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    object_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()
    provenance: Mapping[str, FrozenJsonValue] = field(default_factory=dict)
    reason: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate result status/value consistency and stable provenance references."""
        object.__setattr__(self, "descriptor_id", _text(self.descriptor_id, "descriptor_result.descriptor_id"))
        object.__setattr__(self, "scope", _text(self.scope, "descriptor_result.scope"))
        status = ResultStatus(self.status)
        object.__setattr__(self, "status", status)
        frozen_value = None if self.value is None else _freeze_json(self.value, "descriptor_result.value")
        if status is ResultStatus.COMPUTED and frozen_value is None:
            raise ValueError("descriptor_result.value is required for computed status")
        reason = _text(self.reason, "descriptor_result.reason", optional=True)
        if status is ResultStatus.COMPUTED and reason is not None:
            raise ValueError("descriptor_result.reason must be null for computed status")
        if status is not ResultStatus.COMPUTED and (frozen_value is not None or reason is None):
            raise ValueError("non-computed descriptor results require a reason and null value")
        object.__setattr__(self, "value", frozen_value)
        object.__setattr__(self, "algorithm_id", _text(self.algorithm_id, "descriptor_result.algorithm_id"))
        if self.unit is not None:
            object.__setattr__(self, "unit", _unit(self.unit, "descriptor_result.unit"))
        object.__setattr__(self, "parameters", _json_object(self.parameters, "descriptor_result.parameters"))
        object.__setattr__(self, "object_ids", _refs(self.object_ids, "descriptor_result.object_ids", sort=True))
        object.__setattr__(self, "group_ids", _refs(self.group_ids, "descriptor_result.group_ids", sort=True))
        object.__setattr__(self, "provenance", _json_object(self.provenance, "descriptor_result.provenance"))
        if not isinstance(self.warnings, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in self.warnings):
            raise ValueError("descriptor_result.warnings must contain non-empty strings")
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @classmethod
    def from_dict(cls, data: object) -> "DescriptorResult":
        """Reconstruct a descriptor result from an exact JSON object."""
        return _load(cls, data, "descriptor_result", {"status": _enum_converter(ResultStatus)})


def _validate_scene_references(scene: CanonicalScene) -> None:
    """Validate every canonical scene reference without inferring missing facts."""
    object_ids = {record.object_id for record in scene.objects}
    geometry_ids = {record.geometry_id for record in scene.source_geometries}
    group_ids = {record.group_id for record in scene.authored_groups}
    if len(object_ids) != len(scene.objects):
        raise ValueError("canonical_scene.objects must have unique object ids")
    if len(geometry_ids) != len(scene.source_geometries):
        raise ValueError("canonical_scene.source_geometries must have unique geometry ids")
    if len(group_ids) != len(scene.authored_groups):
        raise ValueError("canonical_scene.authored_groups must have unique group ids")
    if any(axis.frame_id != scene.frame.frame_id for axis in scene.axes):
        raise ValueError("canonical_scene.axes must reference canonical_scene.frame")
    for geometry in scene.source_geometries:
        if geometry.object_id not in object_ids:
            raise ValueError(f"source geometry {geometry.geometry_id} references unknown object")
    for geometry in scene.plan_geometries:
        if geometry.object_id not in object_ids:
            raise ValueError(f"plan geometry for {geometry.object_id} references unknown object")
        if geometry.frame_id != scene.frame.frame_id:
            raise ValueError(f"plan geometry for {geometry.object_id} references unknown frame")
    for group in scene.authored_groups:
        if any(member not in object_ids for member in group.member_object_ids):
            raise ValueError(f"authored group {group.group_id} references unknown object")


def validate_canonical_scene(scene: CanonicalScene) -> None:
    """Validate one canonical scene and raise on malformed or dangling facts."""
    if not isinstance(scene, CanonicalScene):
        raise TypeError("scene must be a CanonicalScene")
    _validate_scene_references(scene)


def unit_scale(source_unit: str, analysis_unit: str) -> float:
    """Return the positive conversion factor from source units to analysis units."""
    return _UNIT_TO_METRES[_unit(source_unit, "source_unit")] / _UNIT_TO_METRES[_unit(analysis_unit, "analysis_unit")]


__all__ = [
    "ALLOWED_LENGTH_UNITS",
    "AnalysisFrame",
    "AuthoredGroupFact",
    "AxisSpec",
    "CanonicalScene",
    "DescriptorResult",
    "JsonValue",
    "Matrix4",
    "PlanGeometry",
    "ResultStatus",
    "SourceGeometry3D",
    "SourceObjectFact",
    "Vector2",
    "Vector3",
    "unit_scale",
    "validate_canonical_scene",
]
