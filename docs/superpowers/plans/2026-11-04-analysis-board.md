# Analysis Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Display existing free-space results on a persistent floor-bound Blender board with selectable palettes and opacity.

**Architecture:** Add a focused board module beside overlay.py using the existing strict result reader and native mesh builder. A stable Empty owns one display child, while hidden source objects retain result geometry; external JSON remains authoritative. Extend the existing runtime and five-panel UI at their current publication/load seams.

**Tech Stack:** Python 3.12/Pixi, stdlib-only addon imports, bpy 5.2 LTS, existing result wire, jj.

**Spec:** `docs/superpowers/specs/2026-11-04-analysis-board-design.md`

## Global Constraints

- The calculation plane remains the managed IFC drawing at its analysis height.
- The authoritative result mesh remains present and hidden by default.
- Changing display elevation never changes the calculation plane.
- Never infer a slab datum from world zero.
- Reopening performs a strict historical read without restoring runtime currentness, native observation or Domain consent.
- A missing or mismatched sidecar is reported and its display hidden; mesh colors/attributes must never reconstruct authoritative data.
- Current free-space values are categorical: empty False and occupied True use fixed palette endpoints; other statuses keep distinct styles and legend labels.
- Display changes must not invalidate Domain consent, currentness, numerical results or cache identity.
- Root alone writes jj history; preserve all sibling workspaces and original IFC.
- Use Pixi, Python 3.12 and only portable Blender at `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`.
- New/modified functions have English docstrings; no new dependencies or free-space schema changes.

## Workline and gates

Workspace `free-space-cache`: `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`.
Base `d08cd0eb0b0d`, initial change `slqmkxol` / `8e4cd236`; sole version writer root.
Remote checkpoint `codex/free-space-cache@origin` already verified at base.
Use new bookmark `codex/analysis-board` for accepted board work, retaining the backup.
Ledger: `docs/project/evidence/analysis-board-2026-11-04.md`.
Task briefs/reports and hash-frozen review packages live in `.superpowers/sdd/2026-11-04-analysis-board/`.
The bundled Bash scripts assume a colocated Git tree, absent in this jj workspace;
use bounded Python/PowerShell equivalents for extraction and `jj diff` packaging.
Do not delete workspace or evidence. Project independent reruns override the
generic skill's suggestion to rely only on implementer test reports.

### Task 1: Board data, style and native presentation

**Files:** Create `blender_addon/order_analyzer_ui/board.py`, `palettes.py`, palette license/attribution; test `test/test_blender_analysis_board.py`. Modify `overlay.py` and its tests only for native SI unit conversion / finite lift validation.

**Interfaces consumed:** `wire.ResultRef`, `ResultReadContext`, `open_analysis_result(documents, *, result_ref, context)`, `ValidatedAnalysisResult`, `overlay.build_native_mesh(result, *, bpy_module=None, name=..., display_lift_m=...)`.

**Interfaces produced (keep signatures for Task 2):**

```python
def attach_result(result, *, result_path, bpy_module=None):
    """Create/reuse a bound board and hidden source, returning the board Empty."""
def select_result(board, result_id, *, bpy_module=None):
    """Strictly open a registered external result and show it historically."""
def update_style(board, *, palette=None, reverse=None, opacity=None,
                 range_mode=None, range_min=None, range_max=None,
                 display_elevation_m=None, bpy_module=None):
    """Validate, persist and apply display settings without numerical mutation."""
def restore_boards(*, bpy_module=None):
    """Restore this scene's boards historically; report missing refs on the board."""
def owned_display_datablock(datablock):
    """Recognize only explicitly owned board presentation datablocks."""
def board_record(board):
    """Return the validated saved descriptor for UI and selection."""
def scene_boards(*, bpy_module=None):
    """Return this scene's owned board Empties."""
```

- [x] Write focused tests for exact external-ref roundtrip/rejection, stable binding, categorical/status mapping, finite/range/opacity/reversal and units. For native interfaces use small fake bpy seams; shader/native persistence are checked in Task 3.
- [x] Run `pixi run pytest test/test_blender_analysis_board.py test/test_blender_analysis_overlay.py -q` before implementation and record useful failing cases.
- [x] Implement one JSON descriptor custom property on the board with stable board/project/domain/slab/storey identity, explicit result entries, active result, style and historical/unavailable status. Save expected identity/backend mappings independently from the external file being checked. Compare full datum receipt when switching; preserve board identity/style across matching result publication; reject mismatched projects/domains/grounds.
- [x] Implement cividis/viridis/magma samples from installed Matplotlib with attribution/license; use stdlib lookup and a pure finite numeric mapper. Empty/occupied fixed endpoints; conditional, unknown, outside, invalid, not_available distinct from established empty. Native materials use actual shader inputs, support transparent rendering and separate board style when meshes are shared. Tag owned mesh/material/node tree resources narrowly.
- [x] Reuse/build hidden result mesh by exact ref, create/reuse one display child with shared geometry, use object material override, preserve world XY and move Z from existing plane/lift to slab datum plus lift. Divide world metres by valid scene unit scale. No silent default for absent datum; attach_result raises a clear ValueError in that case. Keep prior display intact if switching fails, or hide it with explicit unavailable status when restoring.
- [x] Rerun focused tests, write self-review report. Visual: omitted here; Task 3 covers actual shader/placement questions. Freeze candidate hashes and jj diff; independent verifier reruns tests and supplies spec/quality verdicts; root accepts with jj after matching tested bytes.

### Task 2: Runtime lifecycle and existing UI

**Files:** Modify `runtime.py`, addon `__init__.py`, `adapters/blender_analysis_capture.py`; tests `test_blender_analysis_runtime.py`, `test_blender_analysis_ui.py`, `test_blender_analysis_capture.py`. If confirmed by reconnaissance, correct `adapters/blender_analysis_session.py:build_display_fragments` and overlay tests for plane-local/world conversion.

**Interfaces consumed:** Task 1 functions above and record's documented fields; current `_replace_native_overlay`, publication/load/update guards. Keep five panel IDs unchanged.

**Interfaces produced:** Existing publication calls board.attach_result with `job.directory / "result.json"` (or exact document job path); current overlay handle points at hidden source. UI selects explicit saved board/result and invokes display-only style update. Load calls restore_boards without assigning runtime current result/observation or Domain consent.

- [ ] Add regressions showing new board/result/display roles excluded from physical capture, owned material/node updates neutral, source material updates still invalidate, board persists across matching publication, old datum-free API fixtures remain supported, and load stays historical.
- [ ] Keep legacy datum-free publication as hidden result-only with explicit unavailable-board message; ordinary slab-bound result creates/reuses board. Stop deleting retained board result sources. Do not weaken current publication before/after guards.
- [ ] Add properties/operators in existing Analysis Results panel: active board, attached result selection, palette, reverse, opacity, auto/manual range (clearly inapplicable to Boolean free-space), display elevation and status/legend. Display callbacks never call `_analysis_input_update`; unregister removes every property/operator.
- [ ] Extend narrow owned-display update classification for board objects/meshes/materials/node trees, without globally exempting materials. Reopen restores only historical board display; missing sidecar is explicit. Existing native inspection continues using authoritative current result reader.
- [ ] Detect actual scene `scale_length` changes before the existing neutral Scene-update classifier. Invalidate factual observation/consent and rebuild board presentation historically at the new scale, or hide it explicitly on failure. Source reuse must match exact ref and stored native scale. Check `1 -> 0.001 -> 1` with no wrong-size/current board surviving.
- [ ] Verify translated/rotated planes produce fragments by projecting domain into plane-local XY, clipping lattice there and transforming vertices back to world SI. Preserve holes and area; test nonzero translation, XY rotation and nonunit native scale. Reuse established frame helpers; change only if actual bug confirmed.
- [ ] Run `pixi run pytest test/test_blender_analysis_board.py test/test_blender_analysis_overlay.py test/test_blender_analysis_runtime.py test/test_blender_analysis_ui.py test/test_blender_analysis_capture.py -q`; write report, frozen hashes/diff and independent rerun/spec/quality gate. Synchronize architecture map. Visual: reuse/required in Task 3; state/cache properties use assertions.

### Task 3: Native Blender acceptance and whole-scope review

**Files:** Task-scoped native acceptance scripts and evidence under `scripts/design/analysis_board/`, `outputs/design/analysis_board/`, durable ledger/architecture docs. Product fixes only through a bounded implementation dispatch and scoped re-review.

**Interfaces consumed:** Registered production addon and Task 1/2 APIs, existing actual exact S3 result `fe3243c13b3f45daac8744efc46f3962` and its retained external file.

- [ ] Refresh actual addon modules without a second runtime namespace, verify loaded file hashes and portable Blender identity. Preserve original IFC and unrelated scene resources.
- [ ] Attach the actual S3 result historically. Assert stable board binding, source hidden/render-hidden, visible child shares data, cell/status attrs unchanged, SI XY/domain area retained and visible world Z=slab top+lift while plane stays 1.6 m.
- [ ] Assert cividis/viridis/magma, reversal and opacity touch only owned display; numerical digest/external bytes/cache keys and runtime Domain consent/currentness do not change. Switch two explicit actual stored compatible results, verify one visible child and same board ID. Restore a missing/mismatched sidecar using a disposable acceptance fixture and prove unavailable display with no authoritative reconstruction.
- [ ] Save a new `.blend` copy and reopen with only the authorized portable Blender (separate background process if live reopen would disturb the user). Verify external strict historical restore, stable bindings/style and no observation/Domain consent/current flag recovery.
- [ ] Visual: required. Produce actual S3 native board plan/context and compact palette/opacity comparison. Resolve visible source/domain alignment, floor placement and whether 0.5 opacity is readable. Deliver visuals; record human visual review pending unless user replies.
- [ ] Independent verifier runs native evidence checks and affected final regressions, freezes hashes and writes whole-scope specification/quality verdicts. Root updates checklist/architecture, commits accepted tested bytes with jj and updates authorized task bookmark remotely; no merge or workspace deletion.

