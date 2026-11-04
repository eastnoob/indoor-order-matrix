"""Strict stdlib-only immutable analysis documents shared by Pixi and Blender."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import tempfile
from types import MappingProxyType

SCHEMA_VERSION = "blender-analysis-result/1"
ALGORITHM_VERSION = "blender-analysis-compact/1"
REQUEST_VERSION = "planar-analysis-request/2"
KINDS = frozenset({"domain_session", "free_space_run"})
STATUSES = ("established", "conditional", "unknown", "outside", "invalid", "not_available")


def plain(value):
    """Detach only finite data containers, never executable/custom object hooks."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if value is None or type(value) in (bool, str, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return float(value)
    raise ValueError("document contains non-finite or non-data value: " + type(value).__name__)


def freeze(value):
    """Deeply detach JSON data so a reader cannot mutate live authority."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return plain(value)


def canonical_json(value):
    """Encode deterministic strict UTF-8 JSON for both deduplication and digests."""
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def document_digest(document):
    """Bind all authoritative content except the digest's own field."""
    return sha256(canonical_json({key: item for key, item in document.items() if key != "digest"}).encode("utf-8")).hexdigest()


def _object_pairs(pairs):
    """Reject duplicate keys instead of accepting parser-dependent last values."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _invalid_constant(value):
    """Reject NaN and Infinity at the JSON trust boundary."""
    raise ValueError("non-finite JSON constant: " + value)


def load_json(text):
    """Parse embedded/sidecar JSON identically without executing source text."""
    return json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_invalid_constant)


def _text(value, name):
    """Require an explicit nonempty identity/version string."""
    if not isinstance(value, str) or not value:
        raise ValueError(name + " must be a nonempty string")
    return value


def _integer(value, name, minimum=0):
    """Reject bool indices and invalid counts before indexing shared tables."""
    if type(value) is not int or value < minimum:
        raise ValueError(name + " must be an integer >= " + str(minimum))
    return value


def validate_compositions(binding, identity):
    """Check optional native observations inside existing result/Region mappings."""
    project = identity.get("project_source_identity", {}).get("project_global_id")
    plane = binding.get("plane_binding")
    space = binding.get("space_binding")
    for name, observation, fields in (
        ("plane", plane, {"version", "project_global_id", "camera_guid", "plane_uuid", "plane_revision",
                          "origin", "basis", "observation_digest"}),
        ("space", space, {"version", "project_global_id", "space_guid", "source_id", "storey_ref",
                          "geometry_digest", "origin", "provenance"}),
    ):
        if observation is None:
            continue
        if (not isinstance(observation, Mapping) or set(observation) != fields
                or type(observation["version"]) is not int or observation["version"] != 1):
            raise ValueError(name + " composition fields/version are invalid")
        plain(observation)
        if not project or observation["project_global_id"] != project:
            raise ValueError(name + " composition project differs from native source")
        hash_key = "observation_digest" if name == "plane" else "geometry_digest"
        token = observation[hash_key]
        if not isinstance(token, str) or len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
            raise ValueError(name + " composition requires a SHA256 observation")
    if plane is not None:
        if (not isinstance(plane["camera_guid"], str) or not plane["camera_guid"].strip()
                or plane["plane_uuid"] != identity.get("plane_uuid")
                or type(plane["plane_revision"]) is not int or plane["plane_revision"] < 1
                or plane["plane_revision"] != identity.get("plane_revision")):
            raise ValueError("plane composition identity/revision mismatch")
        axes = plane["basis"]
        if not isinstance(axes, (tuple, list)) or len(axes) != 3:
            raise ValueError("plane composition requires three basis axes")
        vectors = (plane["origin"], *axes)
        if (len(axes) != 3 or any(not isinstance(vector, (tuple, list)) or len(vector) != 3
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector)
                for vector in vectors)):
            raise ValueError("plane composition requires finite origin and basis")
        for first in range(3):
            for second in range(3):
                if not math.isclose(sum(a * b for a, b in zip(axes[first], axes[second])),
                                    float(first == second), rel_tol=0, abs_tol=1e-9):
                    raise ValueError("plane composition basis must be orthonormal")
        determinant = sum(axes[2][index] * (axes[0][(index + 1) % 3] * axes[1][(index + 2) % 3]
            - axes[0][(index + 2) % 3] * axes[1][(index + 1) % 3]) for index in range(3))
        if not math.isclose(determinant, 1, rel_tol=0, abs_tol=1e-9):
            raise ValueError("plane composition basis must be right-handed")
    if space is not None:
        domain = identity.get("domain_identity")
        if (not isinstance(space["space_guid"], str) or not space["space_guid"].strip()
                or space["source_id"] != "ifc-object:" + space["space_guid"]
                or not isinstance(space["storey_ref"], str) or not space["storey_ref"].startswith("ifc-object:")
                or not space["storey_ref"].removeprefix("ifc-object:").strip()
                or not isinstance(domain, Mapping) or domain.get("source_id") != space["space_guid"]
                or space["origin"] not in {"adopted", "created_from_b4"}
                or not isinstance(space["provenance"], Mapping)):
            raise ValueError("space composition source/domain/provenance mismatch")


@dataclass(frozen=True)
class ResultRef:
    """Exact immutable content address; never a mutable latest pointer."""

    kind: str
    result_id: str
    digest: str

    def __post_init__(self):
        """Validate the exact kind/id/hash selector."""
        if self.kind not in KINDS:
            raise ValueError("unsupported result kind")
        _text(self.result_id, "result_id")
        if not isinstance(self.digest, str) or len(self.digest) != 64 or any(c not in "0123456789abcdef" for c in self.digest):
            raise ValueError("result digest must be SHA256")


@dataclass(frozen=True)
class ResultMetadata:
    """A read-only projection of document identity and supported versions."""

    ref: ResultRef
    schema_version: str
    algorithm_version: str
    backend_versions: Mapping
    identity: Mapping

    def __post_init__(self):
        """Detach nested identity and backend evidence."""
        for name in ("backend_versions", "identity"):
            object.__setattr__(self, name, freeze(getattr(self, name)))


@dataclass(frozen=True)
class ResultReadContext:
    """Consumer expectations and independently verified observation evidence."""

    expected: Mapping = field(default_factory=dict)
    backend_versions: Mapping | None = None
    require_confirmed_domain: bool = False
    require_current: bool = False
    allow_historical: bool = False
    current_observation: Mapping | None = None

    def __post_init__(self):
        """Freeze expectations rather than retaining mutable caller containers."""
        for name in ("expected", "backend_versions", "current_observation"):
            object.__setattr__(self, name, freeze(getattr(self, name)))


@dataclass(frozen=True)
class ReadOnlyResultSnapshot:
    """Frozen exact document plus contextual freshness, independent of FieldStatus."""

    ref: ResultRef
    metadata: ResultMetadata
    payload: Mapping
    freshness: str

    def __post_init__(self):
        """Detach every nested payload before consumer access."""
        object.__setattr__(self, "payload", freeze(self.payload))


@dataclass(frozen=True)
class ValidatedAnalysisResult:
    """Concrete validated wire record; it imports neither bpy nor the Field engine."""

    document: Mapping

    def __post_init__(self):
        """Keep validated bytes independent from caller-owned mutable JSON."""
        object.__setattr__(self, "document", freeze(self.document))

    def __getattr__(self, name):
        """Expose the specified snapshot/lattice/cell identity without duplicating truth."""
        if name in self.document:
            return self.document[name]
        if name in ("snapshot", "lattice", "source_audit"):
            return self.document["tables"][name]
        raise AttributeError(name)


def resolve_value(document, reference):
    """Resolve one value or snapshot-provenance reference with explicit bounds."""
    if isinstance(reference, Mapping):
        if set(reference) != {"snapshot"} or not isinstance(reference["snapshot"], str):
            raise ValueError("invalid shared snapshot reference")
        try:
            return document["tables"]["snapshot"]["provenance"][reference["snapshot"]]
        except KeyError as exc:
            raise ValueError("missing shared snapshot value") from exc
    index = _integer(reference, "value reference")
    values = document["tables"]["values"]
    if index >= len(values):
        raise ValueError("value reference outside table")
    return values[index]


def _delta(document, base, delta):
    """Apply exact replacements/removals; absent keys are distinct from None."""
    return plain(_delta_view(document, base, delta))


def _delta_view(document, base, delta):
    """Resolve a private shallow delta after the document's finite-data check."""
    if not isinstance(delta, Mapping):
        raise ValueError("invalid cell delta")
    if set(delta) == {"ref"}:
        return resolve_value(document, delta["ref"])
    if set(delta) != {"changes", "removed"} or not isinstance(base, Mapping) or not isinstance(delta["changes"], Mapping):
        raise ValueError("invalid mapping delta")
    removed = delta["removed"]
    if not isinstance(removed, (list, tuple)) or any(not isinstance(key, str) for key in removed) or len(set(removed)) != len(removed):
        raise ValueError("invalid removed keys")
    if set(removed) & delta["changes"].keys() or any(key not in base for key in removed):
        raise ValueError("conflicting cell delta")
    result = dict(base)
    for key in removed:
        del result[key]
    for key, ref in delta["changes"].items():
        result[key] = resolve_value(document, ref)
    return result


def decode_cell(document, *, row, column):
    """Read exact public sample data without geometry, processes or Field imports."""
    return plain(_decode_cell_view(document, row=row, column=column))


def _decode_cell_view(document, *, row, column, base_provenance=None):
    """Read private references without detaching shared, already checked metadata."""
    if document.get("kind") != "free_space_run":
        raise ValueError("domain diagnostics have no field samples")
    lattice = document["tables"]["lattice"]
    _integer(row, "row")
    _integer(column, "column")
    if row >= lattice["n_rows"] or column >= lattice["n_cols"]:
        raise ValueError("sample outside lattice")
    cell = document["cells"][row * lattice["n_cols"] + column]
    if (cell["row"], cell["column"]) != (row, column):
        raise ValueError("cell index does not match lattice")
    tables = document["tables"]
    if base_provenance is None:
        base_provenance = {key: resolve_value(document, ref) for key, ref in tables["sample_provenance"].items()}
    support = _delta_view(document, tables["sample_support"], cell["support_delta"])
    provenance = _delta_view(document, base_provenance, cell["provenance_delta"])
    if cell["provenance_support"]:
        if not isinstance(provenance, Mapping):
            raise ValueError("sample provenance must be a mapping")
        provenance = dict(provenance)
        provenance["support"] = support
    return {"value": cell["value"], "status": cell["status"],
            "query": resolve_value(document, cell["query_ref"]), "support": support,
            "source_ids": resolve_value(document, cell["source_ids_ref"]),
            "provenance": provenance, "explanation": resolve_value(document, cell["explanation_ref"])}


def _validate_sample(sample):
    """Check the concrete bool sample's full wire shape before it reaches an addon."""
    status, value = sample["status"], sample["value"]
    if status not in STATUSES or (value is not None and type(value) is not bool):
        raise ValueError("invalid bool sample")
    if (status in STATUSES[:2]) != (value is not None):
        raise ValueError("sample value/status conflict")
    if not isinstance(sample["explanation"], str) or status == "conditional" and not sample["explanation"].strip():
        raise ValueError("conditional sample requires explanation")
    if not isinstance(sample["source_ids"], (list, tuple)) or any(not isinstance(item, str) for item in sample["source_ids"]):
        raise ValueError("invalid sample source ids")
    provenance, query = sample["provenance"], sample["query"]
    if not isinstance(provenance, Mapping) or any(provenance.get(key) != REQUEST_VERSION for key in ("algorithm_version", "schema_version")):
        raise ValueError("sample provenance versions incompatible")
    if not isinstance(query, Mapping) or set(query) != {"domain_id", "frame", "plane", "height_band", "demand", "tolerance", "revision"}:
        raise ValueError("invalid sample query")
    if (query["domain_id"] is not None and not isinstance(query["domain_id"], str)
            or query["frame"] is not None and not isinstance(query["frame"], str)
            or not isinstance(query["revision"], str) or type(query["tolerance"]) not in (int, float) or query["tolerance"] < 0):
        raise ValueError("invalid query identity/tolerance")


def validate_document(document):
    """Authenticate fixed versions, digest, identity, tables and every cell reference."""
    original_document = document
    try:
        # Validate the same detached data that public reads expose, so custom
        # container methods cannot disguise stored values in private cell views.
        document = plain(document)
        if document["schema_version"] != SCHEMA_VERSION or document["algorithm_version"] != ALGORITHM_VERSION:
            raise ValueError("unsupported result schema/algorithm")
        ResultRef(document["kind"], document["result_id"], document["digest"])
        if document["digest"] != document_digest(document):
            raise ValueError("result digest mismatch")
        if document["result_id"] != document["job_id"]:
            raise ValueError("job/result identity mismatch")
        identity = document["identity"]
        if not isinstance(identity, Mapping) or not isinstance(document["binding"], Mapping):
            raise ValueError("invalid identity/binding")
        composition_identity = identity
        if document["kind"] == "domain_session" and identity.get("domain_identity") is None:
            composition_identity = {**identity, "domain_identity": document["payload"].get("authored_domain")}
        validate_compositions(document["binding"], composition_identity)
        plane_binding = document["binding"].get("plane_binding")
        if plane_binding is not None and document["kind"] == "free_space_run":
            plane = document["tables"]["snapshot"]["request"]["plane"]
            if any(plain(plane_binding[key]) != plain(plane[key]) for key in ("origin", "basis")):
                raise ValueError("plane composition pose differs from request")
        if document["kind"] == "free_space_run":
            _integer(document["plane_revision"], "plane revision", 1)
            tables = document["tables"]
            snapshot = tables["snapshot"]
            request = snapshot["request"]
            lattice = tables["lattice"]
            for key in ("n_rows", "n_cols"):
                _integer(lattice[key], key, 1)
            if lattice != request["sampling"] or len(document["cells"]) != lattice["n_rows"] * lattice["n_cols"]:
                raise ValueError("incomplete lattice")
            if (snapshot["semantic_key"] != document["semantic_key"] or snapshot["backend_versions"] != document["backend_versions"]
                    or snapshot["provenance"]["algorithm_version"] != REQUEST_VERSION
                    or snapshot["provenance"]["schema_version"] != REQUEST_VERSION
                    or document["backend_versions"].get("executor") != REQUEST_VERSION
                    or request["plane"]["identity"] != document["plane_uuid"]
                    or request["plane"]["revision"] != document["plane_revision"]
                    or identity["plane_uuid"] != document["plane_uuid"]
                    or identity["plane_revision"] != document["plane_revision"]
                    or identity["semantic_key"] != document["semantic_key"]
                    or identity["domain_identity"] != request["domain"]
                    or identity["operation"] != request["operation"]
                    or identity["query_key"] != request["geometry_query"]
                    or identity["request_identity"] != request["request_id"]):
                raise ValueError("snapshot/token/version mismatch")
            # The complete finite-data and digest passes above cover shared values;
            # each cell still validates its own references, deltas and sample shape.
            base_provenance = {key: resolve_value(document, ref) for key, ref in tables["sample_provenance"].items()}
            for index, cell in enumerate(document["cells"]):
                _integer(cell["row"], "cell row")
                _integer(cell["column"], "cell column")
                if (cell["row"], cell["column"]) != divmod(index, lattice["n_cols"]) or type(cell["provenance_support"]) is not bool:
                    raise ValueError("duplicate/out-of-order/invalid cell")
                _validate_sample(_decode_cell_view(document, row=cell["row"], column=cell["column"],
                                                  base_provenance=base_provenance))
            _validate_fragments(document)
        else:
            payload = document["payload"]
            if "query_key" in identity or "operation" in identity or identity["domain_identity"] != payload["analysis_domain"]:
                raise ValueError("domain identity cannot impersonate occupancy")
            _text(identity.get("plane_uuid"), "domain plane uuid")
            _integer(identity.get("plane_revision"), "domain plane revision", 1)
            if "plane_uuid" in document:
                if document["plane_uuid"] != identity["plane_uuid"]:
                    raise ValueError("domain plane identity mismatch")
            if "plane_revision" in document:
                _integer(document["plane_revision"], "domain plane revision", 1)
                if document["plane_revision"] != identity["plane_revision"]:
                    raise ValueError("domain plane revision mismatch")
            if identity["domain_identity"] is None and payload["confirmation_binding"] is not None:
                raise ValueError("confirmation without active domain")
            if "plane_uuid" in document["binding"] and document["binding"]["plane_uuid"] != identity["plane_uuid"]:
                raise ValueError("domain binding plane uuid mismatch")
            if "plane_revision" in document["binding"]:
                _integer(document["binding"]["plane_revision"], "domain plane revision", 1)
                if document["binding"]["plane_revision"] != identity["plane_revision"]:
                    raise ValueError("domain binding plane revision mismatch")
        if document["kind"] == "free_space_run":
            snapshot = document["tables"]["snapshot"]
            source_fingerprint = snapshot["source_fingerprint"]
            if identity.get("request_source_fingerprint") != source_fingerprint:
                raise ValueError("source identity conflicts with snapshot source fingerprint")
            snapshot_identity = snapshot["provenance"].get("project_source_identity",
                {"request_source_fingerprint": source_fingerprint})
            if not isinstance(snapshot_identity, Mapping) or identity.get("project_source_identity") != snapshot_identity:
                raise ValueError("source identity conflicts with snapshot project/source identity")
        for key, value in document["binding"].items():
            if key in document and key != "binding" and document[key] != value:
                raise ValueError("binding token conflicts with document: " + key)
            if key in identity and identity[key] != value:
                raise ValueError("binding token conflicts with metadata: " + key)
        return original_document
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ValueError("malformed analysis document") from exc


def _validate_fragments(document):
    """Validate T4's reserved display-only fragment protocol without geometry imports."""
    fragments = document["display_fragments"]
    if not isinstance(fragments, (list, tuple)):
        raise ValueError("display fragments must be records")
    for fragment in fragments:
        if not isinstance(fragment, Mapping) or set(fragment) != {"cell_index", "vertices", "faces"}:
            raise ValueError("invalid display fragment fields")
        if _integer(fragment["cell_index"], "fragment cell index") >= len(document["cells"]):
            raise ValueError("fragment outside lattice")
        vertices, faces = fragment["vertices"], fragment["faces"]
        if not isinstance(vertices, (list, tuple)) or not vertices or not isinstance(faces, (list, tuple)) or not faces:
            raise ValueError("empty display fragment")
        if any(not isinstance(vertex, (list, tuple)) or len(vertex) != 3
               or any(type(value) not in (int, float) or not math.isfinite(value) for value in vertex) for vertex in vertices):
            raise ValueError("invalid display vertices")
        for face in faces:
            if not isinstance(face, (list, tuple)) or len(face) < 3 or len(set(face)) != len(face):
                raise ValueError("invalid display face")
            if any(_integer(index, "face vertex") >= len(vertices) for index in face):
                raise ValueError("face references missing vertex")


def validate_analysis_result(document, *, expected_job_id, expected_plane_uuid, expected_plane_revision, expected_semantic_key):
    """Validate a free-space document against the exact frozen publication tokens."""
    validate_document(document)
    expected = {"job_id": expected_job_id, "plane_uuid": expected_plane_uuid,
                "plane_revision": expected_plane_revision, "semantic_key": expected_semantic_key}
    if document["kind"] != "free_space_run" or any(document.get(key) != value for key, value in expected.items()):
        raise ValueError("result does not match frozen job")
    return ValidatedAnalysisResult(document)


def list_analysis_results(documents: Sequence[Mapping], *, kind=None):
    """Project metadata from supplied documents without auto-selecting latest."""
    if kind is not None and kind not in KINDS:
        raise ValueError("unsupported result kind")
    result = []
    for document in documents:
        validate_document(document)
        if kind is None or document["kind"] == kind:
            result.append(ResultMetadata(ResultRef(document["kind"], document["result_id"], document["digest"]),
                document["schema_version"], document["algorithm_version"], document["backend_versions"], document["identity"]))
    return tuple(result)


def open_analysis_result(documents, *, result_ref, context):
    """Exact-open immutable content with explicit identity/version/freshness expectations."""
    matches = [document for document in documents if document.get("kind") == result_ref.kind
               and document.get("result_id") == result_ref.result_id]
    if len(matches) != 1 or matches[0].get("digest") != result_ref.digest:
        raise ValueError("missing, ambiguous or mismatched ResultRef")
    document = matches[0]
    metadata = list_analysis_results([document])[0]
    if context.backend_versions is not None and plain(context.backend_versions) != plain(metadata.backend_versions):
        raise ValueError("incompatible backend versions")
    if not context.expected or any(key not in metadata.identity or plain(metadata.identity[key]) != plain(value)
                                   for key, value in context.expected.items()):
        raise ValueError("consumer identity mismatch or missing expectations")
    if context.require_confirmed_domain and (metadata.identity.get("domain_identity") is None
            or not document["binding"].get("confirmation_binding", document.get("payload", {}).get("confirmation_binding"))):
        raise ValueError("consumer requires confirmed domain")
    current = context.current_observation
    # Evidence is supplied by the existing runtime verification seam, never a persisted current flag.
    fresh = (current is not None and current.get("digest") == document["digest"]
             and current.get("binding") == freeze(document["binding"])
             and current.get("verified") is True and bool(document["binding"])
             and context.backend_versions is not None)
    if context.require_current and not fresh:
        raise ValueError("current read requires matching independently verified observation")
    if not fresh and not context.allow_historical:
        raise ValueError("historical read requires explicit allowance")
    return ReadOnlyResultSnapshot(result_ref, metadata, document, "current" if fresh else "historical")


def write_result_atomic(document, *, path: Path):
    """Publish only validated bytes; failed writes preserve the previous final file."""
    validate_document(document)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, partial = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(document))
            stream.flush()
            os.fsync(stream.fileno())
        validate_document(load_json(Path(partial).read_text(encoding="utf-8")))
        os.replace(partial, path)
    finally:
        Path(partial).unlink(missing_ok=True)
    return path

