# RoomAnalysisModel Interface

`RoomAnalysisModel` is a static room-layer model returned by:

```python
evaluate_scene(scene)["room_analysis_model"]
```

Top-level keys:

- `base_layer`: room bounds and boundary records.
- `object_layer`: objects, affordance extents, furniture groups, entries, columns.
- `region_layer`: activity regions and room-scope fallback records.
- `network_layer`: spatial networks, gap-path graph, negative-space graph.
- `reference_layer`: boundary semantics, column grid, axes, room references.
- `metric_layer`: metric records attached to static model objects.
- `summary_layer`: room-level summaries derived from metric records.

Metric record minimum:

```text
metric, family, target_layer, target_id, value, status, geometry, anchor,
reference, confidence, method, evidence, uncertainty
```

Rule: `target_id` is a static model object id. It is not an experiment
`subject_id`.
