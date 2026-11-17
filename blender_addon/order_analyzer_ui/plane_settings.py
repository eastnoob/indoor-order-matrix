"""Persist native plane choices without owning geometry or numerical execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from adapters.blender_analysis_result_wire import freeze, load_json, plain, validate_compositions
from features.package_analysis_context import AnalysisPlaneCatalog
from features.scene_contract import AnalysisPlane


@dataclass(frozen=True)
class NativePlaneSettings:
    """Keep immutable native observations, one default and explicit package overrides."""

    records: Mapping = field(default_factory=dict)
    default_plane_id: str | None = None
    package_overrides: Mapping = field(default_factory=dict)

    def __post_init__(self):
        """Reject ambiguous identities and detach persisted observations from their caller."""
        if not isinstance(self.records, Mapping) or not isinstance(self.package_overrides, Mapping):
            raise ValueError("plane records and package overrides must be mappings")
        records = plain(self.records)
        projects = set()
        for identity, record in records.items():
            if not isinstance(record, Mapping):
                raise ValueError("native plane observation must be a mapping")
            validate_compositions({"plane_binding": record}, {
                "project_source_identity": {"project_global_id": record.get("project_global_id")},
                "plane_uuid": identity, "plane_revision": record.get("plane_revision")})
            if identity != "bonsai-camera:ifc:" + record["camera_guid"]:
                raise ValueError("native plane identity differs from its drawing GUID")
            projects.add(record["project_global_id"])
        if len(projects) > 1:
            raise ValueError("native plane directory crosses IFC projects")
        if (records and self.default_plane_id not in records) or (not records and self.default_plane_id is not None):
            raise ValueError("native plane default is missing from the directory")
        for package_id, identity in self.package_overrides.items():
            if not isinstance(package_id, str) or not package_id.strip() or identity not in records:
                raise ValueError("package plane override is invalid or missing")
        object.__setattr__(self, "records", freeze(records))
        object.__setattr__(self, "package_overrides", freeze(self.package_overrides))

    @classmethod
    def from_json(cls, encoded: str, *, legacy_binding: str = ""):
        """Read strict settings or lazily adapt one saved legacy observation."""
        if not encoded:
            if not legacy_binding:
                return cls()
            record = load_json(legacy_binding)
            if not isinstance(record, Mapping):
                raise ValueError("stored drawing camera observation is invalid")
            identity = record.get("plane_uuid")
            return cls({identity: record}, identity)
        data = load_json(encoded)
        if (not isinstance(data, Mapping) or set(data) != {
                "version", "records", "default_plane_id", "package_overrides"}
                or type(data["version"]) is not int or data["version"] != 1):
            raise ValueError("native plane settings fields/version are invalid")
        return cls(data["records"], data["default_plane_id"], data["package_overrides"])

    def to_dict(self):
        """Return caller-owned settings suitable for the existing Scene JSON property."""
        return {"version": 1, "records": plain(self.records), "default_plane_id": self.default_plane_id,
                "package_overrides": plain(self.package_overrides)}

    def with_observation(self, record, *, make_default=False):
        """Retain each author's revision history when adopting or refreshing another plane."""
        identity = record["plane_uuid"]
        return replace(self, records={**self.records, identity: record},
                       default_plane_id=identity if make_default or self.default_plane_id is None else self.default_plane_id)

    def with_default(self, identity):
        """Change only the shared default, preserving package overrides."""
        return replace(self, default_plane_id=identity)

    def with_package_override(self, package_id, identity=None):
        """Select an explicit plane or return the package to the shared default."""
        if not isinstance(package_id, str) or not package_id.strip():
            raise ValueError("package plane override requires a nonempty package id")
        overrides = dict(self.package_overrides)
        if identity is None:
            overrides.pop(package_id, None)
        else:
            overrides[package_id] = identity
        return replace(self, package_overrides=overrides)

    def resolve(self, package_id=None):
        """Resolve one reference through the shared typed catalog without observing native state."""
        if not self.records:
            raise ValueError("create or adopt a native drawing camera first")
        planes = tuple(AnalysisPlane(name=str(record.get("camera_guid", identity)),
                                     identity=identity, revision=record["plane_revision"],
                                     origin=record["origin"], basis=record["basis"])
                       for identity, record in self.records.items())
        selected_identity = self.package_overrides.get(package_id)
        context = AnalysisPlaneCatalog(planes, self.default_plane_id).resolve(
            package_plane_identity=selected_identity)
        return self.records[context.primary_plane.identity]
