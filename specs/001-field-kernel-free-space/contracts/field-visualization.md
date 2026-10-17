# Contract: Standalone Field Visualization Manifest (US2 implemented)

The implementation symbol is
`features.space_field_visualization.build_field_layer_manifest`. It is an
explicit consumer of `FieldSample` values from a loaded field or adapter view;
it must not read a B3 JSON package implicitly from the evaluator overlay path.
This US2 slice produces a deterministic JSON-friendly manifest only. SVG/HTML
rendering remains future work.

Each rendered layer records:

- `layer_id` and semantic channel
- sample coordinate/frame/plane/height band
- value and status
- source ids and provenance refs
- units, schema/algorithm versions, and tolerance

Unknown, invalid, outside, and conditional states must remain visually
distinct. In particular, unknown must never be styled as empty/free. The
existing `scene_metric_overlay_svg(scene, matrix)` output remains unchanged
unless a caller explicitly supplies a field layer.
