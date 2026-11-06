"""Describe planar empty cells while retaining one complete compact occupancy source.

The adapter authenticates the wire document. This pure package owns only its
declarations, stable cell targets and explicit Boolean complement; it never
imports a session, reconstructs geometry or interprets emptiness as walkability.
"""

from __future__ import annotations

from collections.abc import Mapping
import json

from .field_core import (
    EvidenceChannelRecord, EvidenceChannelReference, EvidenceOutputChannel,
    EvidenceOutputScale, EvidencePackage, FieldQuery, FieldResultEnvelope,
    FieldResultStatus, _json_value, build_evidence_package_contract,
    build_field_result_cache_identity, fingerprint_evidence_dependency,
)

PACKAGE_ID = "free-space"
PACKAGE_SCHEMA = "free-space-evidence-package/v1"
ALGORITHM_VERSION = "free-space-boolean-complement/1"
PRODUCER = "features.free_space_evidence_package"
OUTPUT_FUNCTION_ID = "free_space"
OUTPUT_FUNCTION_VERSION = "free-space-output/1"
SOURCE_CHANNEL = "physical_occupancy"
OUTPUT_CHANNEL = "free_space"

_STATUS = {
    "established": FieldResultStatus.COMPUTED,
    "conditional": FieldResultStatus.PARTIAL,
    "unknown": FieldResultStatus.PARTIAL,
    "outside": FieldResultStatus.OUTSIDE,
    "invalid": FieldResultStatus.INVALID,
    "not_available": FieldResultStatus.NOT_AVAILABLE,
}
_CHANNELS = ({"channel": SOURCE_CHANNEL, "polarity": "descriptive", "units": "boolean"},
             {"channel": OUTPUT_CHANNEL, "polarity": "descriptive", "units": "boolean"})
_RECIPE = {"formula": "free_space = not physical_occupancy for Boolean values; otherwise null",
           "meaning": "Empty under the declared physical query; no walkability, clearance or connectivity claim"}


def _value(document, reference):
    """Read the two compact reference forms without expanding shared sample metadata."""
    if isinstance(reference, Mapping):
        if set(reference) != {"snapshot"} or not isinstance(reference["snapshot"], str):
            raise ValueError("invalid compact snapshot reference")
        return document["tables"]["snapshot"]["provenance"][reference["snapshot"]]
    if type(reference) is not int or not 0 <= reference < len(document["tables"]["values"]):
        raise ValueError("invalid compact value reference")
    return document["tables"]["values"][reference]


def _document_scope(document):
    """Validate projection inputs and bind scene, domain, plane and exact lattice scope."""
    try:
        if not isinstance(document, Mapping) or document["kind"] != "free_space_run":
            raise ValueError("a compact free_space_run document is required")
        # Strict JSON plus the content digest binds the complete retained source,
        # including sample fields this Boolean projection does not interpret.
        json.dumps(_json_value(document), allow_nan=False)
        actual = fingerprint_evidence_dependency({key: value for key, value in document.items() if key != "digest"})
        if actual != document["digest"]:
            raise ValueError("free-space document digest mismatch")
        tables, identity = document["tables"], document["identity"]
        request, lattice = tables["snapshot"]["request"], tables["lattice"]
        if (any(type(lattice[key]) is not int or lattice[key] < 1 for key in ("n_rows", "n_cols"))
                or lattice != request["sampling"]
                or len(document["cells"]) != lattice["n_rows"] * lattice["n_cols"]):
            raise ValueError("free-space document requires a complete positive lattice")
        for index, cell in enumerate(document["cells"]):
            if (type(cell["row"]) is not int or type(cell["column"]) is not int
                    or (cell["row"], cell["column"]) != divmod(index, lattice["n_cols"])):
                raise ValueError("free-space cells must cover the lattice exactly once in order")
            status, value = cell["status"], cell["value"]
            if (status not in _STATUS or value is not None and type(value) is not bool
                    or (status in {"established", "conditional"}) != (value is not None)):
                raise ValueError("free-space sample value/status conflict")
            source_ids, explanation = _value(document, cell["source_ids_ref"]), _value(document, cell["explanation_ref"])
            if (not isinstance(source_ids, (list, tuple)) or any(not isinstance(item, str) for item in source_ids)
                    or not isinstance(explanation, str) or status == "conditional" and not explanation.strip()):
                raise ValueError("free-space sample requires valid source ids and explanation")
        scope = fingerprint_evidence_dependency({
            "source": identity["project_source_identity"],
            "scene": identity["request_source_fingerprint"],
            "domain": request["domain"], "plane": request["plane"],
            "lattice": lattice, "geometry_query": request["geometry_query"],
        })
        return "free-space-grid:" + scope
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("malformed compact free-space source") from exc


def _target(scope, cell):
    """Address one deterministic scene/grid cell without relying on publication order."""
    identity = f"{scope}:row:{cell['row']}:column:{cell['column']}"
    return {"kind": "free_space_cell", "id": identity, "identity": identity}


def _result_ref(document):
    """Expose the exact publication locator retained by the authenticated source."""
    return {key: document[key] for key in ("kind", "result_id", "digest")}


def _source_identity(document, target, query):
    """Bind a field-scope source to its actual compact bytes and exact publication ref."""
    return build_field_result_cache_identity(
        target=target, query=query, channel_declarations=(_CHANNELS[0],),
        input_fingerprint=document["digest"], source_fingerprint=fingerprint_evidence_dependency(_result_ref(document)),
        recipe_fingerprint=fingerprint_evidence_dependency(_RECIPE),
        algorithm_version=ALGORITHM_VERSION, schema_version=PACKAGE_SCHEMA,
    )


def build_free_space_package_contract(document, *, dependency_fingerprints=None, visualization_manifest=None):
    """Bind actual source bytes and optional declared dependencies to seven shared roles."""
    scope = _document_scope(document)
    request = document["tables"]["snapshot"]["request"]
    declared = {} if dependency_fingerprints is None else dict(dependency_fingerprints)
    actual = {
        "scene": {"source_fingerprint": document["identity"]["request_source_fingerprint"], "document_digest": document["digest"]},
        "model": {"backend_versions": document["backend_versions"], "producer": PRODUCER},
        "source": {"identity": document["identity"]["project_source_identity"], "result_ref": _result_ref(document)},
        "plane": request["plane"],
        "query": {key: value for key, value in request.items() if key != "request_id"},
        "recipe": {**_RECIPE, "output_function": OUTPUT_FUNCTION_ID, "output_function_version": OUTPUT_FUNCTION_VERSION},
        "channels": _CHANNELS,
    }
    if set(declared) - set(actual) or any(not isinstance(value, str) or not value for value in declared.values()):
        raise ValueError("declared dependency fingerprints must name shared roles with nonempty fingerprints")
    dependencies = {name: fingerprint_evidence_dependency({"actual": value, "declared": declared.get(name)})
                    for name, value in actual.items()}
    return build_evidence_package_contract(
        package_id=PACKAGE_ID, package_schema=PACKAGE_SCHEMA, producer=PRODUCER,
        target_ids=(_target(scope, cell)["identity"] for cell in document["cells"]),
        dependencies=dependencies, algorithm_version=ALGORITHM_VERSION, schema_version=PACKAGE_SCHEMA,
        artifacts={} if visualization_manifest is None else {"visualization_manifest": visualization_manifest},
    )


def build_free_space_source_envelope(document, *, source_freshness="historical"):
    """Retain the compact document once in one immutable field-scope source envelope."""
    scope = _document_scope(document)
    if source_freshness not in {"historical", "current", "supplied_scene"}:
        raise ValueError("source freshness must describe an explicit reader or supplied scene")
    query = FieldQuery(**_value(document, document["cells"][0]["query_ref"]))
    target = {"kind": "free_space_field_scope", "id": scope, "identity": scope}
    statuses = {_STATUS[cell["status"]] for cell in document["cells"]}
    status = next(iter(statuses)) if len(statuses) == 1 else FieldResultStatus.PARTIAL
    explanation = "" if status is FieldResultStatus.COMPUTED else "Retained field contains bounded or unavailable raw sample statuses; inspect exact cells"
    provenance = {"algorithm_version": ALGORITHM_VERSION, "schema_version": PACKAGE_SCHEMA,
                  "producer": PRODUCER, "source_freshness": source_freshness,
                  "result_ref": _result_ref(document), "scope": scope}
    identity = _source_identity(document, target, query)
    record = EvidenceChannelRecord(channel=SOURCE_CHANNEL, required=True, polarity="descriptive",
        observation={"document": document}, status=status, units="boolean",
        provenance={"inherits_top_level": True}, explanation=explanation)
    return FieldResultEnvelope(target=target, query=query, raw_status=status, channel_set=(SOURCE_CHANNEL,),
        value={"channels": (record,)}, provenance=provenance, cache_identity=identity, explanation=explanation)


def _outputs(source_envelopes):
    """Append one descriptive Boolean reading per exact cell with sparse source lineage."""
    if len(source_envelopes) != 1 or source_envelopes[0].channel_set != (SOURCE_CHANNEL,):
        raise ValueError("free-space package requires one physical_occupancy field-scope source")
    envelope = source_envelopes[0]
    document = envelope.value["channels"][0].observation["document"]
    scope = _document_scope(document)
    if envelope.target["kind"] != "free_space_field_scope" or envelope.target["identity"] != scope:
        raise ValueError("source envelope target differs from the actual field scope")
    query = FieldQuery(**_value(document, document["cells"][0]["query_ref"]))
    if envelope.query != query or envelope.cache_identity != _source_identity(document, envelope.target, query):
        raise ValueError("source envelope identity differs from the actual compact document")
    lineage = (EvidenceChannelReference.from_envelope(envelope, SOURCE_CHANNEL),)
    scale = EvidenceOutputScale(meaning=_RECIPE["meaning"], units="boolean", normalization_method=_RECIPE["formula"])
    result_ref = _result_ref(document)
    for index, cell in enumerate(document["cells"]):
        status = _STATUS[cell["status"]]
        reason = _value(document, cell["explanation_ref"])
        if status is not FieldResultStatus.COMPUTED and not reason.strip():
            reason = "Raw physical occupancy status is " + cell["status"]
        locator = {"row": cell["row"], "column": cell["column"], "cell_index": index, "result_ref": result_ref}
        # A conditional Boolean stays partial; unavailable values remain null.
        observation = {"value": None if cell["value"] is None else not cell["value"],
                       "physical_occupancy": cell["value"], "raw_status": cell["status"], "cell_locator": locator}
        yield EvidenceOutputChannel(target=_target(scope, cell), channel=OUTPUT_CHANNEL,
            observation=observation, status=status, scale=scale, derived_from=lineage,
            source_ids=tuple(_value(document, cell["source_ids_ref"])),
            provenance={"producer": PRODUCER, "algorithm_version": ALGORITHM_VERSION,
                        "schema_version": PACKAGE_SCHEMA, "output_function": OUTPUT_FUNCTION_ID,
                        "output_function_version": OUTPUT_FUNCTION_VERSION,
                        "source_result_identity": envelope.cache_identity["identity"],
                        "sample_locator": locator}, explanation=reason)


def build_free_space_evidence_package():
    """Construct the existing shared execution template for the one declared channel."""
    return EvidencePackage(PACKAGE_ID, OUTPUT_FUNCTION_ID, OUTPUT_FUNCTION_VERSION, _outputs)
