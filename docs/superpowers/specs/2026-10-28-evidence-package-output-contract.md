# Evidence Package Output Contract

**Status:** working contract implemented in `features/field_core.py`; the
`group-axis-potential` aggregate baseline is reviewed, while rules for other or
future packages and cross-package fusion remain unapproved.

## Purpose

An evidence package may retain several measured channels and apply its own
domain-specific output function. The shared contract stores that result and
its scale description without replacing or flattening the source evidence.
This is an internal field-core contract, not a plugin system or public API.

## Execution template

`EvidencePackage` is the shared execution template for package-owned derived
outputs. Construction requires a non-empty package id, output-function id and
version, plus a callable. `evaluate()` passes the immutable source-envelope
tuple to that callable and accepts only an iterable of
`EvidenceOutputChannel` records that passes `EvidencePackageOutput` validation.
The shared validation checks record shape, status explanations, scale metadata,
source-channel lineage, duplicate outputs and preservation of every input
envelope/channel.

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
- `package_id`, `output_function`, and `output_function_version`;
- `output_identity`, derived from all input result identities, output
  declarations, scale metadata, output schema, and function version. Any
  additional parameter that can change a result must be included in the source
  envelope identity or the output function version.

Each output channel records its target, channel name, observation, status,
scale description, direct source-channel references, source ids, provenance,
and explanation. An output must reference at least one admitted channel from
the supplied source envelopes. It cannot reuse the same target/channel key as
an input channel. The complete input envelopes remain attached and
serializable with the output object.

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
versioning, rejection of channel replacement, and explicit endpoint semantics
for bounded scales. It also checks that a package must provide a callable and
that its result is validated through the shared output contract. These are
contract-only tests; they create no scene, geometry, IFC observation, or spatial
result. A separate integration smoke on the pinned IFC selected two real
authored furniture groups, passed their existing trend envelopes through a
`not_evaluated` contract probe, confirmed both source channels were preserved,
serialized the result, and verified the IFC fingerprint was unchanged. That
smoke checks wiring only; the two sampled groups mapped to four existing IFC
plane SVGs whose XML parsed successfully. It is not full-scene validation and
does not validate an evidence formula.
