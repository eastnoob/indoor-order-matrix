# Evidence Package Output Contract

**Status:** working contract implemented in `features/field_core.py`; this
revision adds optional, explicit cross-package channel readback and dependency
lineage. It does not approve or implement a fusion formula.

## Purpose

An evidence package may retain several measured channels and apply its own
domain-specific output function. The shared contract stores that result and
its scale description without replacing or flattening the source evidence.
This is an internal field-core contract, not a plugin system or public API.

## Execution template

`EvidencePackage` is the shared execution template for package-owned derived
outputs. Construction requires a non-empty package id, output-function id and
version, plus a callable. The existing `evaluate(source_envelopes)` call stays
valid. An opted-in consumer may pass explicit package dependencies and use the
context callback to read them; the legacy callback still receives only source
envelopes. The callable accepts only an iterable of
`EvidenceOutputChannel` records that passes `EvidencePackageOutput` validation.
The executing algorithm identity is package-level (`output_function` plus
version); output channels remain distinct by name, lineage, status, scale and
observation, but the shared core does not require a separate algorithm id on
each channel.
The shared validation checks record shape, status explanations, scale metadata,
source-channel and package-channel lineage, duplicate outputs and preservation
of every input envelope/channel.

The callable owns the package's actual calculation and any normalization it
declares. Shared validation can verify that the output declares a scale and
that bounded scales explain their endpoints; it cannot establish that a
formula is scientifically correct or that two packages are comparable. Those
rules remain package-specific and require review. Direct construction of
`EvidencePackageOutput` remains available for existing serialization and
contract uses, so `EvidencePackage.evaluate()` is the canonical execution
path, not a global enforcement mechanism for every caller.

## Data shape

`EvidencePackageOutput` contains:

- `source_envelopes`: the exact immutable `FieldResultEnvelope` inputs used by
  the package output function;
- `outputs`: additive `EvidenceOutputChannel` records;
- `dependencies`: exact external package/output/target/channel references and
  package freshness used by this result (no recursive copy of the source result);
- `package_id`, `output_function`, and `output_function_version`;
- `output_identity`, derived from all input result identities, output
  declarations, scale metadata, output schema, and function version. Any
  additional parameter that can change a result must be included in the source
  envelope identity or the output function version.

Each output channel records its target, channel name, observation, status,
scale description, direct source-channel references, source ids, provenance,
and explanation. An output must reference at least one declared source or
package channel. It cannot reuse the same target/channel key as an input
channel. The complete input envelopes remain attached and serializable with the
output object. External references identify the source result without embedding
the complete source package a second time.

`EvidenceOutputScale` may describe a meaning, units, normalization method,
optional numeric range, optional endpoint meanings, and an optional `scale_id`.
No numeric range, normalization formula, or shared semantic anchor is chosen
by this contract. A `scale_id` is a claim that the output uses a reviewed
semantic scale; a matching numeric range such as 0–1 alone is not evidence of
comparability.

## Comparison boundary

Each package owns its calculation function and may emit multiple outputs. The
shared type validates and records the output; it does not calculate support,
strength, probability, weights, or normalization. Missing and conflicting
outputs remain status-bearing and are never converted to zero.

A future fusion layer may combine numeric outputs only after their semantic
scale and interpretation are explicitly reviewed as compatible. It must
retain each package contribution and its source references. Outputs without a
reviewed common scale remain available as separate evidence and are not
silently omitted from package records. This spec does not define fusion.

## Cross-package readback and status

`EvidencePackageChannelReference` binds `package_id`, `output_identity`,
`target_identity`, and `channel`. A fresh dependency exposes the exact published
channel and preserves its own status verbatim; this matters for domain states
such as an unreachable route. A stale or unavailable dependency exposes no
usable channel and has effective `not_available`; its original channel is
available only through an explicitly named audit field. This prevents a
consumer from accidentally reading a stale observation as current input. A
derived output that references such a dependency must have
`observation=None`, even when its status is `partial`; status labels cannot
smuggle a historical numeric value back into the current result. The reader
does not map a channel status into a different domain status or infer query
compatibility; the consuming package owns that semantic check.

Dependencies participate in `output_identity`. Evaluation uses a typed source
output transiently to resolve a fresh reference; the published result retains
only package/output/target/channel identity and freshness, never the nested
source output object. Direct self-dependencies are rejected at output creation.
The graph validator rejects self-dependencies and longer cycles when the caller
supplies the complete declared package graph; if the caller omits it, indirect
cycle detection is not guaranteed. The shared core has no registry from which
to discover unrelated package edges and adds no execution scheduler. The
resolver gates the caller-supplied freshness value; it does not rebuild or
compare the package contract. There is no generic JSON deserializer for
`EvidencePackageOutput` in this slice, so persisted reads first require a
package-specific typed reconstruction.

## Preservation invariant

For every package output, all source `FieldResultEnvelope` instances and every
channel inside them remain present and unchanged. Package-derived channels are
stored separately in `outputs`; no output function may overwrite an input
channel, remove a channel, or treat a missing input as numeric zero. Output
serialization includes both complete inputs and derived outputs.

## Current package boundary

The geometry-relation package still emits only boundary-gap, contact, and
positive-area-overlap observations; its group-level aggregation remains
deferred. The trend-descriptor package still emits the two active group-level
descriptor channels. The independent `group-axis-potential` package owns the
reviewed aggregate baseline from `overall_group_axis` and keeps its additive
outputs separate from trend descriptors. The package also emits the four
reviewed pairwise axis-relation channels as additive outputs, with independent
channel status and endpoint lineage; these readings do not create an extra
global-resultant vote or claim external calibration. The contract does not
verify package formula correctness or define cross-package fusion.

## Verification

`test/test_evidence_package_output.py` checks complete input-channel
preservation, JSON serialization, source-channel lineage, output identity
versioning, rejection of channel replacement, package-channel readback and
dependency-cycle rejection, and explicit endpoint semantics for bounded
scales. Contract tests create no scene, geometry, IFC observation, or spatial
result. A separate integration smoke on the pinned IFC selected two real
authored furniture groups, passed their existing trend envelopes through a
`not_evaluated` contract probe, confirmed both source channels were preserved,
serialized the result, and verified the IFC fingerprint was unchanged. That
smoke checks wiring only; the two sampled groups mapped to four existing IFC
plane SVGs whose XML parsed successfully. It is not full-scene validation and
does not validate an evidence formula.
