# MassPatch Generation Contract

The generator consumes `MeshGeometry3D` and an optional
`MassPatchGenerationConfig`, then returns the existing
`MassPatchGenerationResult` contract.

Generation is source-read-only and explicit. A caller that only wants to find
already-authored substitutes must use `analysis-substitute-discovery`.
Generation does not imply IFC export, IFC validation, Bonsai import, or layout
scoring.
