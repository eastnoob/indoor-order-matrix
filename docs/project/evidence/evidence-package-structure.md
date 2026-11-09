# Evidence Package Structure

An evidence package is a result container for one target/scope and one
materialized analysis snapshot. It groups related channels; it does not turn
the channels into one shared algorithm or one automatic score.

There are two layers. The outer package contract/status/manifest records the
target, query/scope/plane, input versions, dependency fingerprints, freshness,
recompute reasons, and published views. The runtime
`EvidencePackageOutput` currently carries only the immutable source envelopes,
additive channel outputs, compact external dependency references, package
function identity, and the derived output identity. Freshness and
visualization manifest are therefore package-level records beside the runtime
output, not fields on `EvidencePackageOutput` itself.

```text
Evidence package
├── Outer package records
│   ├── package contract: target/query/scope/plane and input snapshot
│   ├── package status: freshness, recompute_required, reasons, affected targets
│   └── visualization manifest: published JSON/SVG/HTML locators
├── Runtime EvidencePackageOutput
│   ├── source_envelopes       original field evidence, retained in full
│   ├── outputs                additive derived channels
│   ├── dependencies           compact package/output/target/channel references
│   └── output_identity        stable identity of the complete result boundary
└── Channel records
    ├── algorithm declaration  channel-owned method/recipe and version
    ├── input snapshot         source envelope lineage and external references
    ├── output                 observation, status, scale/units, explanation
    └── provenance             source IDs, lineage, and audit metadata
```

The four channel parts are logical responsibilities, not four nested classes:

1. **Algorithm declaration:** each channel should name the method/recipe and
   version that produce it. Different channels may point to the same method,
   but their identity and meaning remain separate. The current runtime only
   records package-level `output_function` and `output_function_version`; a
   typed channel-specific algorithm ID/version is a known follow-up gap.
2. **Input snapshot:** each channel names the exact source channels it used;
   package-level `source_envelopes` retain the common materialized input
   snapshot, and `derived_from` points to each channel's actual inputs.
   Cross-package inputs add an explicit package/output/target/channel
   reference and participate in `output_identity`. Separate per-channel input
   snapshot fingerprints are not yet a typed runtime field.
3. **Output:** each `EvidenceOutputChannel` carries its observation, status,
   scale/units, and explanation. Derived channels are additive and cannot
   replace a source channel.
4. **Provenance:** source IDs, lineage, and provenance remain attached so a
   result can be audited without guessing which input was used.

One package can read a published channel from another package, then append a
new derived channel. `read_evidence_package_channel()` is an identity-only raw
reader for an already reconstructed `EvidencePackageOutput`.
`resolve_evidence_package_channel()` gates the caller-declared freshness value:
fresh input exposes the original channel, while stale or unavailable input
exposes no usable `channel` and retains only a redacted `audit_channel` when a
typed source output exists. The resolver does not calculate freshness; the
package contract/status layer or its caller supplies that decision. A stale or
unavailable external dependency cannot publish any output with a non-`None`
observation, regardless of whether its status is `partial` or `computed`.
Without a typed source output, an unavailable dependency has no audit
observation.

The dependency reference is part of the consuming package's output identity.
`source_output` is an evaluation-time handle only. Published outputs and JSON
serialization keep compact references and do not recursively retain upstream
package outputs. There is no generic JSON-to-`EvidencePackageOutput`
deserializer in this slice; persisted readback requires a package-specific
reconstruction step before the typed reader can be used.

The shared core does not maintain a package registry or scheduler. The caller
may pass a complete package dependency graph to
`EvidencePackage.evaluate(..., dependency_graph=...)`; when supplied, it is
validated before the callback runs. If the graph is omitted, direct self
dependencies are still rejected at output construction, but indirect-cycle
checking is not guaranteed. Cross-package fusion formulas remain owned by the
consuming package and are not inferred by the shared core.
