# Persistent analysis board

The user approved a reusable display board for the existing free-space result.
The calculation plane remains the managed IFC drawing at its analysis height;
the board is an ordinary Blender helper bound to the result's project, domain,
storey and selected slab datum. It has no physical occupancy or IFC authorship.

The stable board is a Blender Empty with a visible mesh child. The authoritative
result mesh remains present and hidden by default. The child shares its mesh
geometry and cell attributes where native material binding permits, and moves
that frozen world-SI geometry to the verified slab top plus a small display lift.
Changing display elevation never changes the calculation plane. Domain edges,
holes, world XY rotation/translation and scene unit scale must remain correct.
Never infer a slab datum from world zero. Legacy datum-free publications remain
supported as result meshes; the UI explains why no ground board can be created.

The board retains its stable binding and an explicit list of attached external
results. Each entry stores the exact ResultRef, path, independent identity and
backend expectations. Switching only opens an explicit entry. Bindings, style
and active selection persist in the blend file. Reopening performs a strict
historical read without restoring runtime currentness, native observation or
Domain consent. A missing or mismatched sidecar is reported and its display
hidden; mesh colors/attributes must never reconstruct authoritative data.

Styles offer cividis, viridis and magma, reversal, automatic/manual numeric
range and global opacity (default 0.5). Current free-space values are categorical:
empty False and occupied True use fixed palette endpoints; other statuses keep
distinct styles and legend labels. A pure numeric display mapper can support
finite scalars, including a constant auto-range midpoint, without broadening the
free-space wire schema or adding a metric. Sample fixed palette data from the
existing Matplotlib installation with its license and attribution; Blender must
not import Matplotlib or need network access to display results.

All result presentation is on the board. Keep the existing five Analyzer panels
and put board/result selection, palette, reversal, range, opacity, display height
and legend/status in Analysis Results. Display resources (objects, owned meshes,
materials and node trees) are excluded from physical capture. Display changes
must not invalidate Domain consent, currentness, numerical results or cache
identity. Ordinary source material/object changes retain their invalidation.

Use Pixi, Python 3.12 and only portable Blender at
`D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`.
Root alone writes jj history; preserve all sibling workspaces and original IFC.
New/modified functions have English docstrings and important geometry/handoff
steps explain why. No new dependencies, metric kernel, generic plugin framework,
automatic latest selection, source IFC edits or distance execution.

Necessary visual acceptance is one actual S3 plan/context view proving board
placement/alignment and a palette/opacity comparison. Tests and exact references
prove serialization/cache/state properties without extra pictures. User visual
acceptance is recorded separately; silence never means approval.
