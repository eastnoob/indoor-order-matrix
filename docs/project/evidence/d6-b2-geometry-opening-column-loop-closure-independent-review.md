# D6 B2 Geometry, Opening, and Column Loop-Closure Independent Review

- Review date: **2026-10-07**
- Repair commit: `f7f71a303a6775b958c299035c650350ed2eba7a`
- Owner decision: `9b50bb1f44c0ae7dc2807c17da084d1ab8163393`
- Decision: **REVISE**
- Evidence class reviewed: **bounded synthetic design evidence**

## Review result

The nine fixtures cover the declared cases: F01 interior column occupancy; F02 exact-contact loop support; F03 a 0.125 fixture-unit near-contact gap; F04 a hosted opening with geometry provenance; F05 a closed-door scenario assumption; F06 missing, unresolved, and conflicting host relations; F07 malformed and unsupported opening geometry; F08 a valid polygon with disconnected sources; and F09 an invalid polygon with a connected closed source loop.

The outputs keep occupancy separate from conditional boundary support. F01–F03 retain included column occupancy, while only F02 records conditional support. The reused `_topology_status()` helper uses exact endpoint equality; F03 remains two components and partial. Neither the runner nor the report selects a production tolerance. F04 preserves host and geometry references and performs no subtraction. F05 identifies the closed-door assumption as not a source fact. F06 and F07 retain distinct local diagnostics. F08 and F09 demonstrate that polygon validity and source connectivity are independent observations.

The result records diagnostic refusal and `not_evaluated` downstream free-space/route claims. It does not promote a room or domain, select a candidate, compute free-space or route results, or define a public status enum. The commit adds only the seven declared repair files; it changes no production code, adapter, public API, test, dependency, IFC/Blender file, or historical evidence.

The report does not materially overclaim the evidence. F04’s “true boundary opening” is supported only by its synthetic relation and reference fields; no physical opening geometry is validated or subtracted. The report labels the evidence synthetic, leaves production implementation unapproved, and retains real IFC as `not_verified`.

## Blocker

The owner decision’s B2 evidence requirements explicitly include **uncertainty propagation**. None of the nine fixtures, result records, or probe oracles includes an uncertainty input or tests how uncertainty propagates into contact support, opening qualification, or refusal. The artifacts therefore do not yet satisfy the full owner-defined B2 repair gate. Add a synthetic uncertainty case with an expected propagated diagnostic/refusal (or amend the requirement through a later owner decision), then obtain another independent review. Until then, B2 remains `REVISE` and this evidence does not authorize geometry implementation design.

## Independent checks

- Re-ran the probe with `pixi run python` into a fresh `%TEMP%` directory. All nine assertions passed. `results.json` and `summary.svg` were byte-identical to the committed artifacts: SHA-256 `47f4bf594874f4cf6ec7f973086dd3737884409484563d3ac3325656aaa8ba19` and `f826956401df47afc6f405ecbc7c9a03c75dcc6f2a97f4b9f377154cd9098dab`, respectively.
- Independently parsed the fixtures, results, manifest, and SVG/XML; checked that the nine fixture/result IDs align and the SVG has nine cards. All six manifest-declared byte counts and SHA-256 digests match. The manifest itself is 4,236 bytes with SHA-256 `ed95efde93bbe6bed4b4c907c83ed1ca15ab26b22416db52b18f39970eee0656`.
- Inspected the owner decision from commit `9b50bb1f44c0ae7dc2807c17da084d1ab8163393` and the repair commit’s complete path list. No pytest, real IFC, or Blender run was needed for this bounded evidence review.

STOP FOR D6 B2 INDEPENDENT REVIEW
