# Position Overlay Basemap Design

## Goal

Make focused position-order visuals readable without changing the public
position-order scoring design.

`P_position_fit` remains region-level:

```text
ActivityRegion / RoomScope -> FurnitureGroup positions
```

It does not score individual chairs and tables. Chairs and tables should appear
as a visual basemap so the scored furniture-group proxies are understandable.

## Required Layers

The focused position overlay must draw three layers:

1. `position-basemap-object`: faint original object footprint or polygon.
2. `position-grammar-group`: furniture-group proxy outline.
3. `position-grammar-slot` / `position-grammar-residual`: group-level slot and
   residual evidence.

Only the third layer is scoring evidence. The first layer is visual context.

## SVG Semantics

The SVG proxy fixtures must distinguish:

```text
region = north_tables
furniture_group = north_table_group_r1_c1
role = table / chair
```

Each north table set should contain one table and four chairs. The chair objects
must have stable ids so loader output is inspectable.

## Grill-Me Self-Check

- If the basemap is missing, can the user tell what the green proxy contains?
  No, so basemap is required.
- If yellow points are drawn per chair, does that corrupt `P_position_fit`?
  Yes, so yellow remains group-level only.
- If `north_table_group_r1_c1` contains five tables, can assembly evidence be
  trusted later?
  No, so SVG roles must be corrected now.
- If the score changes only because the basemap is visible, did we mix display
  and scoring?
  That must not happen; overlay changes must not feed evaluator rows.

## Acceptance

- Loader sees six north table furniture groups inside `north_tables`.
- Each north table furniture group has exactly one table and four chairs.
- Focused overlay contains faint object basemap elements.
- Focused overlay still has no `furniture_affordance_extent_` assignment ids.
- Existing focused position tests and MVP tests pass.

