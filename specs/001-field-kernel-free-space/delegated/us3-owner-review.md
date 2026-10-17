# US3 deterministic fixture replay owner review

## Result

The design-only replay ran twice from the repository root and produced
byte-identical canonical observations for all eight fixtures.

- Canonical SHA-256: `a734362f175c04bd1da21cd4155e46ba1546058800320106dc240c5e6c019a04`
- Canonical byte count: `9656`
- Formula scope: `probe_only_not_production`
- Both reports: `design_only=true`, `fixture_count=8`
- Replay artifacts: `us3-replay-run1.json`, `us3-replay-run2.json`

The replay report records eight channel assertions and five executable
perturbations: identifier/order, translation, supported wall-free rotation,
declared opening mutation, and missing-domain propagation.

## Deferred fixture cases

These remain explicit `blocked` and `design_only` records:

1. Invalid geometry versus a distinct missing-geometry representation.
2. Rotation involving wall geometry, because the fixture wall schema is only a
   vertical `x` plus `y_range` representation.
3. Eye-height `z=1.6 m` versus whole-height semantics, because the fixtures
   contain no height-band or whole-height channel.

## Boundary

This artifact validates replay and channel-local probe invariants only. It does
not create a production `FreeSpaceField`, infer clearance/connectivity, alter
the B3 loader, promote B3 data, or wire the live evaluator.
