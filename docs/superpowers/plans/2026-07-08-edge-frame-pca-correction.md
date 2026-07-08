# Edge Frame PCA Correction Plan

1. Add focused tests for the correction gate:
   - west lounge corrects the false PCA diagonal
   - weak ambiguous groups keep PCA
2. Replace the previous member-frame default with a gated correction in `_activity_group_frame`.
3. Keep metadata explicit through `group-axis-basis`.
4. Run focused pytest, full pytest, and execute `test/svg_id_inference_demo.ipynb`.
5. Save a separate jj change without including user-owned `test/SVG_abnormal.svg`.
