# Open Mesh MassPatch Substitute Design

**Date:** 2026-09-08

## Goal

Allow `MassPatch` generation to create conservative low-count substitutes from open or mixed-topology meshes without pretending that open geometry is a reliable closed solid.

## Problem

The current MassPatch chain treats topology uncertainty too broadly. `_component_meshes()` splits a logical object into factual components, but it copies the parent mesh `is_closed` and `is_manifold` flags into every component. One open chair-frame part can therefore make closed seats, legs, and backs look uncertain.

A second guard rejects collection validation whenever any source component is open or non-manifold. That is correct for closed-solid validation, but too strict for Rhino/CAD substitute generation. Open meshes can still provide an outer envelope for plan occupancy and height extent, as long as the result is labeled as uncertain envelope evidence.

## Design

1. `MassPatch` remains the only physical substitute type. No convex-hull substitute and no open-mesh substitute class.
2. Component topology is derived from each split component, not inherited from the parent logical mesh. For a single component with an explicit uncertain source flag, the authored uncertainty remains authoritative.
3. Closed/manifold sources keep the existing hard validation path: plan recall, plan overreach, height intervals, gap preservation, and occlusion comparison.
4. Open or non-manifold sources may use conservative component envelope candidates. They skip closed-solid height and occlusion claims, and report `open_envelope_uncertain`.
5. Envelope generation is componentwise. The generator must not make one whole-object box around a chair because that fills the space between legs, seats, and backs.
6. The implementation uses the existing component AABB candidate path for open/detail parts. Curved-component segmentation remains a separate upgrade because it needs its own geometry fixtures and validation rules.
7. Selection stays weight-free: feasible evidence first, then fewer patches, then lower geometry complexity.

## Output Contract

`generate_mass_patches()` may return `selected_collection_method="open_envelope_collection"` when selected patches are conservative envelopes for uncertain source topology. The patches are closed cuboids for downstream query compatibility, but their provenance and collection report include the uncertainty reason.

Exact fallback remains mandatory. If envelope generation produces no useful candidate, the generator returns exact source components with uncertainty reports.

## Grill Me Self-Check

- Does this create fake solid truth from an open mesh? No. Open candidates are envelope evidence and skip closed-solid interval/occlusion claims.
- Does this fill gaps between disconnected chair parts? No. The envelope path is componentwise and collection queries use union semantics.
- Does this break closed mesh behavior? It must not. Closed/manifold validation remains on the existing path and current regressions stay green.
- Is this overbuilt? No new dependency, no new substitute type, no BIM/UI work. It fixes the shared backend root cause.

## Acceptance Criteria

- A mixed closed/open logical mesh reports per-component topology correctly.
- An open box-like mesh can produce a conservative cuboid envelope instead of only an exact high-poly fallback.
- Open-envelope results carry explicit uncertainty in reports and provenance.
- A single component explicitly marked uncertain still remains conservative.
- Closed hollow or sloped sources still reject unsafe filled boxes.
- Existing MassPatch collection, boundary, and geometry tests remain green.
