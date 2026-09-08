# Substitute Contract

An accepted analysis substitute binding has these fields:

| Field | Meaning |
| --- | --- |
| `source_global_id` | Stable identity of the authoritative source object. |
| `substitute_id` | Identity of the authored or previously generated substitute. |
| `substitute_kind` | Functional substitute kind, for example `MassPatch`. |
| `analysis_role` | Why the substitute exists, normally `analysis_geometry_substitute`. |
| `visibility_policy` | Display guidance, normally `analysis_only`. |
| `provenance` | Read-only evidence of the binding source. |
| `confidence` | Evidence confidence such as `high`, `medium`, or `low`. |

Discovery must preserve missing and ambiguous candidates rather than guessing.
Generation belongs to `masspatch-generation`; IFC serialization belongs to
`ifc-export`.
