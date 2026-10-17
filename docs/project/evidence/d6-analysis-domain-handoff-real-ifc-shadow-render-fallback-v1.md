# D6 frozen Blender diagnostic render fallback v1

Date: **2026-10-08 (Europe/Berlin)**

Evidence class: **disposable visual diagnostic from frozen real-IFC-associated Blender geometry**

Result: **readable PNG rendered; real AnalysisDomain confirmation remains refused**

The final [PNG](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/attempt_003/preview.png) shows the 38 captured source meshes by role and the saved provisional S1 polygon as a separate magenta outline. Orange door and cyan window display copies share each source mesh's exact triangle data and are lifted vertically so the overhead camera can show them. The 38 source objects remain at the recorded world-space coordinates in the disposable [Blender file](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/attempt_003/diagnostic.blend). The outline and display copies are tagged as diagnostics; their lift is not factual geometry. The image is not a full furniture model: this frozen cohort contains no furniture.

The render retains the five required labels: `FROZEN IFC-ASSOCIATED SNAPSHOT`, `LIVE BLENDER NOT INSPECTED`, `DOMAIN CONFIRMATION REFUSED — A11/A12`, `EXACT PROJECTION ROUND-TRIP REFUSED`, and `NO FREE-SPACE / ROUTE RESULT`. It also labels S1 provisional and names the display lift. The image was opened and visually inspected, and the PNG decoded at 2600 × 1600 RGBA pixels. A raster check found 6,167 orange door pixels, 7,407 cyan window pixels, and 12,077 magenta S1 pixels in the model viewport. These checks support visibility; they do not qualify spatial inference.

## Frozen identity and geometry

- The three inputs matched the byte counts and SHA-256 values in the original [provenance](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/provenance.json) before rendering: `live_snapshot.json` 5,692,042 bytes / `96f40383297fdebb12ed7a26ef9dac38188ed05fcfa7def43c202fceaeb3daad`; `source_scene.json` 17,731,702 bytes / `7f2ff08d5c305e1bd348df0b3a00445619d101058b56a817f7bdebdcbb000776`; `semantic_result.json` 15,313,537 bytes / `72ae9cd1f57d91d15e2b739026138682177df02f4c8200297b69cb87962e6a03`.
- All 38 external STEP/GlobalId identities were matched to saved NeutralSceneV2 records. Source roles are 11 walls, 16 columns, 6 doors, and 5 windows. Across them, the render copied 71,561 world-space metre vertices and 142,716 triangles. Each source vertex list and triangle list matched the frozen capture exactly before Blender conversion; the Blender mesh audit found the same triangle indices and 0.0 m maximum source coordinate error. The captured non-identity transforms were checked against NeutralSceneV2 provenance and were **not** applied again to already transformed vertices. New display source objects use identity transforms and no modifiers. Per-object counts, recorded transforms, GlobalIds, and errors are in [render_verification.json](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/attempt_003/render_verification.json).
- The S1 outline uses all 4,402 saved GeoJSON ring points, with no simplification. Its maximum XY difference after Blender float32 conversion was 0.00000095367431640625 m. The 4.65 m display lift does not create an AnalysisDomain. Saved S1 area remains 307.5600036764141 m², and A11/A12 are unresolved.
- The 15 original files enumerated in [baseline.json](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/baseline.json), including the prior report/manifest and frozen inputs, retained their bytes and SHA-256 in [verification.json](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/verification.json). The source IFC was not rescanned or edited; the user's live Blender scene/file was not opened or modified.

## Actual execution

The launcher used the existing Pixi Python and spawned only `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe` in a hidden-window, factory-startup background process. The executable's SHA-256 was `0060916d6921eb4d46c57254609d805a2ea711917399051391a52ba14beb6327`. The final command, also recorded as exact argv and Windows command line in [execution.json](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/attempt_003/execution.json), was:

```text
D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe --background --factory-startup --disable-autoexec --python-exit-code 1 --python D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\d6_analysis_domain_handoff_real_ifc_shadow\run_001\render_fallback_v1\render.py -- D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\d6_analysis_domain_handoff_real_ifc_shadow\run_001\render_fallback_v1\attempt_003
```

| Attempt | UTC start–end | Elapsed | Exit | Evidence |
| --- | --- | ---: | ---: | --- |
| 001 | 14:22:01.776979–14:22:08.067375 | 6.290 s | 1 | A check incorrectly required all recorded source transforms to be identity. The capture's already transformed world vertices and original transforms are both retained. Failed log preserved. |
| 002 | 14:22:41.420600–14:22:59.141526 | 17.721 s | 0 | Render completed, but top-view walls visually hid doors/windows. Render and log preserved. |
| 003 | 14:23:56.473119–14:24:12.028229 | 15.555 s | 0 | Final readable PNG and `.blend`; exact mesh display copies expose doors/windows. |

The final PNG is 3,602,559 bytes, SHA-256 `38baf7c1abf4f58d77aa63d9009a2f0c4f78ebb578e924d5827aa84c8cc6e6cf`. [artifact_manifest.json](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/artifact_manifest.json) lists each fallback script, log, render, baseline, and verification file with size and hash. The final [execution.log](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/render_fallback_v1/attempt_003/execution.log) reports saved PNG and Blender file. Blender's optional thumbnail and roaming cache writes were denied by Windows; Blender still exited 0 and both outputs decoded/saved. The original shadow `execution.log` only contains a final result JSON, and there is no original `execution.json`; this fallback does not claim raw historical failed-run logs exist.

## Qualification boundary

S1 remains a provisional inferred polygon. Real confirmation was refused because A11/A12 remain unresolved, and the exact inferred support-mesh projection round trip still returns `inferred_projection_mismatch`. There is no active AnalysisDomain, free-space field, topology graph, or route result. The live Blender MCP previously failed with `WinError 10053`, so this rendering did not inspect the current live scene. Frozen snapshot-to-disk IFC geometry parity remains unverified. This fallback changes none of the original shadow findings and is **not B4 acceptance**. It used no native IFC loader, full pytest suite, source IFC edit, user blend edit, or B3/B4 implementation.
