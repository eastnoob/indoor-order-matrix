"""Typed, immutable package-owned parameter snapshots and identity checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType


REQUIRED = object()
_SUPPORTED_TYPES = (str, bool, int, float, dict, tuple, type(None))
_TYPE_TAGS = {
    str: "str",
    bool: "bool",
    int: "int",
    float: "float",
    dict: "dict",
    tuple: "tuple",
    type(None): "none",
}
_TYPES_BY_TAG = {tag: value for value, tag in _TYPE_TAGS.items()}
_UNITS = {"m", "rad", "dimensionless", "request_context"}


class ParameterImpact(str, Enum):
    """Classify whether changing a parameter changes computation identity."""

    RECOMPUTE_REQUIRED = "recompute_required"
    REUSE_WITH_WARNING = "reuse_with_warning"
    METADATA_ONLY = "metadata_only"


_IMPACTS = {item.value for item in ParameterImpact}


def _json_value(value):
    """Convert frozen parameter JSON into ordinary finite JSON values."""
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("parameter mapping keys must be strings")
        return {key: _json_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return 0.0 if value == 0.0 else value
    raise TypeError("parameters must contain finite JSON values")


def _freeze(value):
    """Detach caller containers so downstream readers cannot edit history."""
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("parameter mapping keys must be strings")
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return _json_value(value)


def _type_tag(value_type):
    """Return the stable contract tag for a supported Python type."""
    try:
        return _TYPE_TAGS[value_type]
    except KeyError as exc:
        raise TypeError("unsupported parameter value_type") from exc


def _validate_source_map(sources, names, *, required):
    """Validate source labels without coercing or inventing caller values."""
    if not isinstance(sources, Mapping):
        raise TypeError("sources must be a mapping")
    source_keys = set(sources)
    if any(type(key) is not str for key in source_keys):
        raise TypeError("source mapping keys must be strings")
    unknown = source_keys - set(names)
    if unknown:
        raise ValueError("unknown parameter source")
    if required and source_keys != set(names):
        missing = sorted(set(names) - source_keys)
        raise ValueError(f"missing parameter source: {missing[0]}")
    for label in sources.values():
        if type(label) is not str or not label:
            raise TypeError("parameter source labels must be nonempty strings")


def _validate_json_container(value):
    """Validate nested finite JSON and return its detached representation."""
    return _freeze(value)


def _validate_value(spec, value):
    """Validate and normalize one value according to a parameter declaration."""
    if value is None:
        if spec.nullable or spec.value_type is type(None):
            return None
        raise TypeError(f"parameter {spec.name!r} does not allow null")

    value_type = spec.value_type
    if value_type is float:
        if type(value) not in (int, float) or type(value) is bool:
            raise TypeError(f"parameter {spec.name!r} must be a finite float")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"parameter {spec.name!r} must be finite")
        value = 0.0 if value == 0.0 else value
    elif value_type is int:
        if type(value) is not int:
            raise TypeError(f"parameter {spec.name!r} must be an int")
    elif value_type is bool:
        if type(value) is not bool:
            raise TypeError(f"parameter {spec.name!r} must be a bool")
    elif value_type is str:
        if type(value) is not str:
            raise TypeError(f"parameter {spec.name!r} must be a str")
    elif value_type is dict:
        if not isinstance(value, Mapping):
            raise TypeError(f"parameter {spec.name!r} must be a mapping")
        value = _validate_json_container(value)
    elif value_type is tuple:
        if not isinstance(value, (tuple, list)):
            raise TypeError(f"parameter {spec.name!r} must be a tuple or list")
        value = _validate_json_container(value)
    elif value_type is type(None):
        raise TypeError(f"parameter {spec.name!r} must be None")
    else:
        raise TypeError("unsupported parameter value_type")

    if spec.minimum is not None and value < spec.minimum:
        raise ValueError(f"parameter {spec.name!r} is below minimum")
    if spec.maximum is not None and value > spec.maximum:
        raise ValueError(f"parameter {spec.name!r} is above maximum")
    if spec.choices is not None:
        normalized_choices = [_validate_value_without_choices(spec, item)
                              for item in spec.choices]
        if _fingerprint(value) not in {
            _fingerprint(item) for item in normalized_choices
        }:
            raise ValueError(f"parameter {spec.name!r} is not an allowed choice")
    return value


def _validate_value_without_choices(spec, value):
    """Validate a declared choice without recursively checking choices."""
    if spec.choices is None:
        return _validate_value(spec, value)
    shallow = ParameterSpec(
        spec.name, spec.value_type, REQUIRED, spec.unit, spec.exposed,
        spec.impact, spec.minimum, spec.maximum, None, spec.nullable,
    )
    return _validate_value(shallow, value)


def _validate_spec(spec):
    """Validate a parameter declaration and its default/choice contracts."""
    if not isinstance(spec, ParameterSpec):
        raise TypeError("specs must contain ParameterSpec values")
    if type(spec.name) is not str or not spec.name:
        raise ValueError("parameter names must be nonempty strings")
    if spec.value_type not in _SUPPORTED_TYPES:
        raise TypeError("unsupported parameter value_type")
    if type(spec.unit) is not str or spec.unit not in _UNITS:
        raise ValueError("parameter units must be canonical")
    if type(spec.exposed) is not bool or type(spec.nullable) is not bool:
        raise TypeError("exposed and nullable must be bool")
    if not isinstance(spec.impact, ParameterImpact):
        raise TypeError("impact must be a ParameterImpact")
    for bound_name, bound in (("minimum", spec.minimum), ("maximum", spec.maximum)):
        if bound is not None:
            if type(bound) not in (int, float) or type(bound) is bool:
                raise TypeError(f"{bound_name} must be numeric")
            if not math.isfinite(float(bound)):
                raise ValueError(f"{bound_name} must be finite")
    if spec.minimum is not None and spec.maximum is not None:
        if spec.minimum > spec.maximum:
            raise ValueError("minimum cannot exceed maximum")
    if spec.value_type not in (int, float) and (
        spec.minimum is not None or spec.maximum is not None
    ):
        raise TypeError("bounds require an int or float parameter")
    if spec.choices is not None:
        if not isinstance(spec.choices, tuple) or not spec.choices:
            raise ValueError("choices must be a nonempty tuple")
        normalized = [_validate_value_without_choices(spec, item)
                     for item in spec.choices]
        if len({_fingerprint(item) for item in normalized}) != len(normalized):
            raise ValueError("choices must be unique")
    if spec.default is not REQUIRED:
        _validate_value(spec, spec.default)


def _identity_payload(package_id, schema_version, effective, impacts):
    """Project only values whose change requires a new computation."""
    return {
        "package_id": package_id,
        "config_schema_version": schema_version,
        "parameters": {
            name: _json_value(effective[name])
            for name in sorted(effective)
            if impacts[name] == ParameterImpact.RECOMPUTE_REQUIRED.value
        },
    }


def _fingerprint(payload):
    """Hash canonical finite JSON without source or request metadata."""
    return hashlib.sha256(json.dumps(
        _json_value(payload), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _freeze_snapshot_mapping(value, field_name):
    """Freeze one public snapshot mapping and require string keys."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{field_name} keys must be strings")
    return _freeze(value)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Declare one package-owned parameter and its validation contract."""

    name: str
    value_type: type
    default: object = REQUIRED
    unit: str = "dimensionless"
    exposed: bool = True
    impact: ParameterImpact = ParameterImpact.RECOMPUTE_REQUIRED
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[object, ...] | None = None
    nullable: bool = False

    def __post_init__(self):
        """Reject invalid primitive declaration fields at construction time."""
        if type(self.name) is not str or not self.name:
            raise ValueError("parameter names must be nonempty strings")
        if self.value_type not in _SUPPORTED_TYPES:
            raise TypeError("unsupported parameter value_type")
        if type(self.unit) is not str or self.unit not in _UNITS:
            raise ValueError("parameter units must be canonical")
        if type(self.exposed) is not bool or type(self.nullable) is not bool:
            raise TypeError("exposed and nullable must be bool")
        if not isinstance(self.impact, ParameterImpact):
            raise TypeError("impact must be a ParameterImpact")


@dataclass(frozen=True, slots=True)
class ParameterSnapshot:
    """Hold immutable effective/calculated values and their audit metadata."""

    package_id: str
    config_schema_version: str
    effective_parameters: Mapping[str, object]
    calculated_parameters: Mapping[str, object]
    parameter_sources: Mapping[str, str]
    parameter_impacts: Mapping[str, str]
    parameter_value_contracts: Mapping[str, Mapping[str, object]]
    parameter_fingerprint: str

    def __post_init__(self):
        """Detach every public mapping so direct construction is immutable."""
        if type(self.package_id) is not str or not self.package_id:
            raise TypeError("package_id must be a nonempty string")
        if type(self.config_schema_version) is not str or not self.config_schema_version:
            raise TypeError("config_schema_version must be a nonempty string")
        if type(self.parameter_fingerprint) is not str:
            raise TypeError("parameter_fingerprint must be a string")
        effective = _freeze_snapshot_mapping(
            self.effective_parameters, "effective_parameters")
        calculated = _freeze_snapshot_mapping(
            self.calculated_parameters, "calculated_parameters")
        sources = _freeze_snapshot_mapping(
            self.parameter_sources, "parameter_sources")
        impacts = _freeze_snapshot_mapping(
            self.parameter_impacts, "parameter_impacts")
        contracts = _freeze_snapshot_mapping(
            self.parameter_value_contracts, "parameter_value_contracts")
        names = set(effective)
        if (set(calculated) != names or set(sources) != names
                or set(impacts) != names or set(contracts) != names):
            raise ValueError("snapshot parameter key sets must match")
        for label in sources.values():
            if type(label) is not str or not label:
                raise TypeError("parameter source labels must be nonempty strings")
        for impact in impacts.values():
            if type(impact) is not str or impact not in _IMPACTS:
                raise ValueError("unrecognized parameter impact")
        for contract in contracts.values():
            if not isinstance(contract, Mapping) or set(contract) != {"type", "nullable", "unit"}:
                raise ValueError("parameter value contract keys do not match")
            if contract["type"] not in _TYPES_BY_TAG:
                raise TypeError("unrecognized parameter type contract")
            if type(contract["nullable"]) is not bool:
                raise TypeError("parameter nullable contract must be bool")
            if contract["unit"] not in _UNITS:
                raise ValueError("parameter value contract unit is not canonical")
        object.__setattr__(self, "effective_parameters", effective)
        object.__setattr__(self, "calculated_parameters", calculated)
        object.__setattr__(self, "parameter_sources", sources)
        object.__setattr__(self, "parameter_impacts", impacts)
        object.__setattr__(self, "parameter_value_contracts", contracts)

    def identity_payload(self) -> dict[str, object]:
        """Return only schema and computation-affecting values."""
        return _identity_payload(
            self.package_id,
            self.config_schema_version,
            self.effective_parameters,
            self.parameter_impacts,
        )

    def to_json(self) -> dict[str, object]:
        """Return expanded historical values and audit metadata."""
        return {
            "package_id": self.package_id,
            "config_schema_version": self.config_schema_version,
            "effective_parameters": _json_value(self.effective_parameters),
            "calculated_parameters": _json_value(self.calculated_parameters),
            "parameter_sources": _json_value(self.parameter_sources),
            "parameter_impacts": _json_value(self.parameter_impacts),
            "parameter_value_contracts": _json_value(self.parameter_value_contracts),
            "parameter_fingerprint": self.parameter_fingerprint,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> "ParameterSnapshot":
        """Validate stored values without applying current defaults."""
        if not isinstance(payload, Mapping):
            raise TypeError("snapshot payload must be a mapping")
        expected = {
            "package_id", "config_schema_version", "effective_parameters",
            "calculated_parameters", "parameter_sources", "parameter_impacts",
            "parameter_value_contracts", "parameter_fingerprint",
        }
        if set(payload) != expected:
            raise ValueError("snapshot payload keys do not match contract")
        package_id = payload["package_id"]
        schema_version = payload["config_schema_version"]
        fingerprint = payload["parameter_fingerprint"]
        if type(package_id) is not str or not package_id:
            raise TypeError("package_id must be a nonempty string")
        if type(schema_version) is not str or not schema_version:
            raise TypeError("config_schema_version must be a nonempty string")
        if type(fingerprint) is not str or not fingerprint:
            raise TypeError("parameter_fingerprint must be a string")
        effective = payload["effective_parameters"]
        calculated = payload["calculated_parameters"]
        sources = payload["parameter_sources"]
        impacts = payload["parameter_impacts"]
        contracts = payload["parameter_value_contracts"]
        maps = (effective, calculated, sources, impacts, contracts)
        if not all(isinstance(item, Mapping) for item in maps):
            raise TypeError("snapshot parameter fields must be mappings")
        names = set(effective)
        if any(type(name) is not str for name in names):
            raise TypeError("parameter names must be strings")
        if set(calculated) != names or set(sources) != names or set(impacts) != names \
                or set(contracts) != names:
            raise ValueError("snapshot parameter key sets must match")
        _validate_source_map(sources, names, required=True)
        frozen_effective = {}
        frozen_calculated = {}
        frozen_contracts = {}
        for name in sorted(names):
            impact = impacts[name]
            if type(impact) is not str or impact not in _IMPACTS:
                raise ValueError("unrecognized parameter impact")
            contract = contracts[name]
            if not isinstance(contract, Mapping) or set(contract) != {"type", "nullable", "unit"}:
                raise ValueError("parameter value contract keys do not match")
            tag = contract["type"]
            nullable = contract["nullable"]
            unit = contract["unit"]
            if tag not in _TYPES_BY_TAG:
                raise TypeError("unrecognized parameter type contract")
            if type(nullable) is not bool:
                raise TypeError("parameter nullable contract must be bool")
            if type(unit) is not str or unit not in _UNITS:
                raise ValueError("parameter value contract unit is not canonical")
            spec = ParameterSpec(name, _TYPES_BY_TAG[tag], REQUIRED, unit,
                                 True, ParameterImpact(impact), nullable=nullable)
            frozen_effective[name] = _validate_value(spec, effective[name])
            frozen_calculated[name] = _validate_value(spec, calculated[name])
            frozen_contracts[name] = MappingProxyType({
                "type": tag, "nullable": nullable, "unit": unit,
            })
        # Normalize declared scalar floats first; nested JSON still distinguishes
        # Boolean, integer and float values that Python equality conflates.
        if _fingerprint(frozen_effective) != _fingerprint(frozen_calculated):
            raise ValueError("calculated parameters must equal effective parameters")
        snapshot = cls(
            package_id,
            schema_version,
            MappingProxyType(frozen_effective),
            MappingProxyType(frozen_calculated),
            MappingProxyType(dict(sources)),
            MappingProxyType(dict(impacts)),
            MappingProxyType(frozen_contracts),
            fingerprint,
        )
        if _fingerprint(snapshot.identity_payload()) != fingerprint:
            raise ValueError("snapshot fingerprint does not match values")
        return snapshot


@dataclass(frozen=True, slots=True)
class ParameterSchema:
    """Own parameter declarations used to resolve current requests."""

    package_id: str
    schema_version: str
    specs: tuple[ParameterSpec, ...]

    def __post_init__(self):
        """Validate declaration identity and every parameter contract."""
        if type(self.package_id) is not str or not self.package_id:
            raise ValueError("package_id must be a nonempty string")
        if type(self.schema_version) is not str or not self.schema_version:
            raise ValueError("schema_version must be a nonempty string")
        if not isinstance(self.specs, tuple):
            raise TypeError("specs must be a tuple")
        names = []
        for spec in self.specs:
            _validate_spec(spec)
            if spec.name in names:
                raise ValueError("duplicate parameter name")
            names.append(spec.name)

    def _snapshot(self, effective, sources):
        """Freeze resolved values and construct their canonical snapshot."""
        names = [spec.name for spec in self.specs]
        impacts = {
            spec.name: spec.impact.value
            for spec in self.specs
        }
        contracts = {
            spec.name: MappingProxyType({
                "type": _type_tag(spec.value_type),
                "nullable": spec.nullable,
                "unit": spec.unit,
            })
            for spec in self.specs
        }
        frozen_effective = MappingProxyType({
            name: _freeze(effective[name]) for name in names
        })
        frozen_sources = MappingProxyType(dict(sources))
        snapshot = ParameterSnapshot(
            self.package_id,
            self.schema_version,
            frozen_effective,
            frozen_effective,
            frozen_sources,
            MappingProxyType(impacts),
            MappingProxyType(contracts),
            "",
        )
        return ParameterSnapshot(
            snapshot.package_id,
            snapshot.config_schema_version,
            snapshot.effective_parameters,
            snapshot.calculated_parameters,
            snapshot.parameter_sources,
            snapshot.parameter_impacts,
            snapshot.parameter_value_contracts,
            _fingerprint(snapshot.identity_payload()),
        )

    def resolve(self, values: Mapping[str, object] | None = None, *,
                sources: Mapping[str, str] | None = None) -> ParameterSnapshot:
        """Expand defaults and validate requested values before calculation."""
        if values is None:
            values = {}
        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping")
        names = [spec.name for spec in self.specs]
        if any(type(key) is not str for key in values):
            raise TypeError("parameter names must be strings")
        unknown = set(values) - set(names)
        if unknown:
            raise ValueError("unknown parameter")
        if sources is None:
            sources = {}
        _validate_source_map(sources, names, required=False)
        effective = {}
        resolved_sources = {}
        for spec in self.specs:
            if spec.name in values:
                effective[spec.name] = _validate_value(spec, values[spec.name])
                resolved_sources[spec.name] = sources.get(spec.name, "request")
            elif spec.default is REQUIRED:
                raise ValueError(f"missing parameter: {spec.name}")
            else:
                effective[spec.name] = _validate_value(spec, spec.default)
                resolved_sources[spec.name] = sources.get(spec.name, "default")
        return self._snapshot(effective, resolved_sources)

    def capture_calculated(self, values: Mapping[str, object], *,
                           sources: Mapping[str, str]) -> ParameterSnapshot:
        """Validate a complete historical value map without expanding defaults."""
        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping")
        names = [spec.name for spec in self.specs]
        if set(values) != set(names):
            missing = set(names) - set(values)
            extra = set(values) - set(names)
            if missing:
                raise ValueError(f"missing parameter: {sorted(missing)[0]}")
            raise ValueError(f"unknown parameter: {sorted(extra)[0]}")
        _validate_source_map(sources, names, required=True)
        effective = {
            spec.name: _validate_value(spec, values[spec.name])
            for spec in self.specs
        }
        return self._snapshot(effective, sources)


def compare_parameter_snapshots(calculated: ParameterSnapshot,
                                requested: ParameterSnapshot) -> dict[str, object]:
    """Report exact, warning reuse or required recomputation with both value sets."""
    if not isinstance(calculated, ParameterSnapshot) or not isinstance(requested, ParameterSnapshot):
        raise TypeError("comparison requires ParameterSnapshot values")
    same_contract = (
        calculated.package_id == requested.package_id
        and calculated.config_schema_version == requested.config_schema_version
        and set(calculated.effective_parameters) == set(requested.effective_parameters)
        and set(calculated.calculated_parameters) == set(requested.calculated_parameters)
        and set(calculated.parameter_sources) == set(requested.parameter_sources)
        and dict(calculated.parameter_impacts) == dict(requested.parameter_impacts)
        and dict(calculated.parameter_value_contracts) == dict(requested.parameter_value_contracts)
    )
    base = {
        "reuse": "exact",
        "exact_match": True,
        "recompute_required": False,
        "calculated_parameters": calculated.to_json()["calculated_parameters"],
        "requested_parameters": requested.to_json()["effective_parameters"],
        "warnings": [],
    }
    if not same_contract:
        base["reuse"] = "recompute_required"
        base["exact_match"] = False
        base["recompute_required"] = True
        return base
    warnings = []
    for name in sorted(calculated.effective_parameters):
        old = calculated.effective_parameters[name]
        new = requested.effective_parameters[name]
        if _fingerprint(old) == _fingerprint(new):
            continue
        impact = calculated.parameter_impacts[name]
        if impact == ParameterImpact.RECOMPUTE_REQUIRED.value:
            base["reuse"] = "recompute_required"
            base["recompute_required"] = True
            base["exact_match"] = False
        elif impact == ParameterImpact.REUSE_WITH_WARNING.value:
            warnings.append({
                "parameter": name,
                "calculated": _json_value(old),
                "requested": _json_value(new),
                "impact": impact,
            })
    if warnings:
        base["warnings"] = warnings
        if not base["recompute_required"]:
            base["reuse"] = "reuse_with_warning"
            base["exact_match"] = False
    return base
