# Group trend alignment evidence package v2

日期：2026-10-28

当前公开单位是 `furniture_group`。Active channels are:

- `overall_group_axis`: the whole group geometry axis;
- `layout_axis`: the group member-centroid layout axis.

`member_frame` and `member_axis` remain in `group_self_description` and in
the envelope provenance as suppressed audit descriptors. They are not in the
active `channel_set`, do not create new visual layers, and do not participate
in candidate, membership, potential, or strength calculations.

The old v1 four-channel IFC run is retained as historical evidence in
[`group-trend-alignment-field-package-v1.md`](group-trend-alignment-field-package-v1.md).
This v2 boundary has focused contract coverage in
`test/test_group_evidence_unit_boundary.py`. A fresh full IFC v2 run is still
pending because the prior runner performs the expensive IFC extraction; the
old v1 artifacts must not be reported as v2 validation.
