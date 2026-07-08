# Edge Frame PCA Correction Design

## Goal

Keep PCA as the default inferred activity-group trend, but correct the specific case where a semienclosed L/U-shaped furniture group produces a false diagonal trend. The correction must not globally replace PCA with member orientation averaging.

## Design

`features/scene_inference.py` remains the only implementation layer. SVG loading still only supplies neutral geometry and metadata.

The group trend pipeline is:

1. Compute the existing affordance point-cloud PCA frame.
2. Compute a lightweight member-frame consensus from elongated furniture records.
3. Use the member frame only when it is strong enough and disagrees clearly with PCA.
4. Keep PCA otherwise.

This makes the correction a veto for false diagonal PCA, not a new default trend engine.

## Strength

When correction is used, `axis-strength` remains bounded by PCA clarity and member agreement. A diagonal coffee table cannot pull the direction, but it lowers the agreement score.

## Acceptance

- Baseline west lounge corrects from the semienclosed PCA diagonal to a rectangular frame.
- Chaotic west lounge keeps the rectangular frame but reports reduced agreement.
- Weak or ambiguous groups keep PCA rather than switching to member orientation.
- Full pytest and the SVG inference notebook execute successfully.
