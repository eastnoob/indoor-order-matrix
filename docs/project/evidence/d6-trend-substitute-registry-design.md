# D6 trend substitute registry design

The registry in `scripts/design/group_level/trend_substitute_registry.json` is a
design-only checkpoint artifact. `trend_analysis` accepts only typed
`consumer=trend`, `substitute_kind=MassPatch`, and
`analysis_role=analysis_geometry_substitute` records. Every instance carries
its own `substitute_id`, `source_object_id`, and provenance; instance identity
is not stored in the registry.

The trend contract also requires provenance
`representation_identifier="Analysis"`; a Body representation is rejected
even when the other typed fields look valid.

Display labels, colors, and line styles are editable metadata and are never
consulted when resolving a contract. Body geometry, object names, source roles,
and labels therefore cannot authorize trend input. Missing or contradictory
typed fields return an auditable rejection reason, and duplicate instance ids
are rejected by batch validation.

This registry is intentionally design-only. It is not a production API and
does not select a trend estimand or winner.
