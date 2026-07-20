# RoomAnalysisModel Development Standard

When adding a new layout abstraction or metric:

1. Add or reuse a neutral scene/model object first.
2. Attach metrics to `target_layer` and `target_id`.
3. Keep SVG parsing inside the adapter layer.
4. Keep scoring algorithms outside the model builder.
5. Add one focused pytest proving the new output lands in the correct layer.

Do not add experiment fields, BIM-plugin assumptions, or SVG-only semantics to
the model.
