"""Read hash-pinned saved package channels through a distinct consumer package.

This is a faithful channel view, not a fusion formula. Callers independently
build the current contract for the scope they intend to reuse; a saved status or
publication receipt is not evidence that a live scene is current.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from features.field_core import (
    EvidenceOutputChannel,
    EvidencePackage,
    EvidencePackageChannelReference,
    EvidencePackageDependency,
    EvidencePackageInput,
    EvidencePackageOutput,
    FieldResultEnvelope,
    deserialize_evidence_package_output,
    evaluate_evidence_package_freshness,
    fingerprint_evidence_dependency,
    read_evidence_package_channel,
)


PACKAGE_ID = "evidence-package-channel-readback"


def load_saved_evidence_package(path: Path, *, expected_sha256: str) -> EvidencePackageOutput:
    """Check exact saved-byte integrity before decoding the fixed package schema."""
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in expected_sha256)):
        raise ValueError("expected_sha256 must be a complete SHA-256 digest")
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256.lower():
        raise ValueError("saved package SHA-256 does not match the required digest")
    return deserialize_evidence_package_output(json.loads(data))


def _source_context_fingerprint(envelopes: Iterable[FieldResultEnvelope]) -> str:
    """Bind the complete numerical source context while excluding outer audit labels."""
    sources = tuple(envelopes)
    if any(not isinstance(source, FieldResultEnvelope) for source in sources):
        raise TypeError("current_source_envelopes must contain FieldResultEnvelope values")
    return fingerprint_evidence_dependency(tuple({
        name: getattr(source, name)
        for name in ("target", "query", "channel_set", "cache_identity", "raw_status", "value", "support", "source_ids")
    } for source in sorted(sources, key=lambda item: (item.target["identity"], item.cache_identity["identity"]))))


def consume_saved_evidence_package(
    path: Path,
    *,
    expected_sha256: str,
    cached_contract: Mapping[str, Any] | None,
    current_contract: Mapping[str, Any] | None,
    current_source_envelopes: Iterable[FieldResultEnvelope] | None,
    selections: Iterable[tuple[str, str]],
    dependency_graph: Mapping[str, Iterable[str]],
) -> EvidencePackageOutput:
    """Copy explicitly selected channels with contract-gated usable observations.

    The required graph names this consumer, the source package, and every
    transitive dependency. The shared core validates closure, actual declared
    edges and cycles before the output callback executes. Source envelopes stay
    complete even when only a few published channels are selected. Callers must
    independently reconstruct current sources and their corresponding current
    contract from the intended inputs. This adapter never infers that binding
    from a saved status, receipt, or matching computation identity.
    """
    source = load_saved_evidence_package(path, expected_sha256=expected_sha256)
    if not isinstance(dependency_graph, Mapping):
        raise TypeError("dependency_graph must be an explicit complete graph mapping")
    for contract in (cached_contract, current_contract):
        if contract is not None and contract.get("package_id") != source.package_id:
            raise ValueError("contract package_id must match the saved package")
    if cached_contract is not None:
        # Existing packages declare either source targets or additive output targets.
        scopes = [
            {item.target[key] for item in records}
            for records in (source.source_envelopes, source.outputs)
            for key in ("id", "identity")
        ]
        if set(cached_contract.get("target_ids", ())) not in scopes:
            raise ValueError("cached contract target scope must match saved source or output targets")
    if (current_source_envelopes is not None
            and _source_context_fingerprint(current_source_envelopes) != _source_context_fingerprint(source.source_envelopes)):
        raise ValueError("current source context differs from the saved package source context")
    selected = tuple(selections)
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("selections must contain distinct target/channel pairs")
    references = tuple(EvidencePackageChannelReference(
        package_id=source.package_id, output_identity=source.output_identity,
        target_identity=target_identity, channel=channel,
    ) for target_identity, channel in selected)
    # Resolve exact addresses before evaluation so a miss cannot become an empty view.
    for reference in references:
        read_evidence_package_channel(source, reference)
    freshness = evaluate_evidence_package_freshness(
        cached_contract=cached_contract, current_contract=current_contract,
    )
    if current_source_envelopes is None:
        freshness["freshness"] = "unavailable"
        freshness["reasons"].append({"code": "current_source_context_missing"})
    reasons = ", ".join(reason["code"] for reason in freshness["reasons"])
    dependency = EvidencePackageDependency(
        package_id=source.package_id, output_identity=source.output_identity,
        channels=references, source_output=source,
        package_freshness=freshness["freshness"],
    )

    def readback(context: EvidencePackageInput) -> tuple[EvidenceOutputChannel, ...]:
        """Preserve source meaning/status while redacting noncurrent observations."""
        return tuple(EvidenceOutputChannel(
            target=resolved.audit_channel.target,
            channel=resolved.audit_channel.channel,
            observation=(resolved.channel.observation if resolved.channel is not None else None),
            status=resolved.effective_status,
            scale=resolved.audit_channel.scale,
            derived_from=(resolved.ref,),
            source_ids=resolved.audit_channel.source_ids,
            provenance=resolved.audit_channel.provenance,
            explanation=(resolved.audit_channel.explanation if resolved.channel is not None
                         else f"{resolved.explanation}; contract comparison: {reasons}"),
        ) for resolved in context.resolved_dependencies)

    package = EvidencePackage(
        package_id=PACKAGE_ID, output_function_id="read_existing_package_channels",
        output_function_version="1", output_function=None, context_output_function=readback,
    )
    return package.evaluate(
        source.source_envelopes, dependencies=(dependency,), dependency_graph=dependency_graph,
    )
