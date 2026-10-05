# D6 Git Provenance Checkpoint 鈥?2026-10-06

- Branch: codex/d6-analysis-domain-layout-handoff
- HEAD at audit start: a149420faf5dfef9d89293a4c415a08df4964581
- Branch purpose: design-only D6 AnalysisDomain/layout handoff and lifecycle evidence checkpoint.
- Upstream: none configured (command exit 128).
- Stop marker: STOP FOR D6 PROGRESS AND GIT PROVENANCE CHECKPOINT REVIEW

## Acceptance gates

1. Branch and HEAD match codex/d6-analysis-domain-layout-handoff at a149420faf5dfef9d89293a4c415a08df4964581.
2. The three lifecycle checkpoint commits are ancestors of HEAD: status-contract repair, amendment v1, and conflict-preservation.
3. This is a normal checkout; no new worktree was created. Existing linked worktrees were left untouched.
4. Lifecycle amendment and conflict-preservation are accepted as limited design evidence only. Production implementation, selector, public API, and model decisions remain deferred.

## Git and worktree evidence

worktree D:/PROJECTS/understandOtherPackage/order_analyzer
HEAD a149420faf5dfef9d89293a4c415a08df4964581
branch refs/heads/codex/d6-analysis-domain-layout-handoff

worktree C:/Users/tianf/.codex/worktrees/8971/order_analyzer
HEAD 594b1d86157913d39b02585ec5a16795335f9f19
detached

worktree C:/Users/tianf/.codex/worktrees/9114/order_analyzer
HEAD fd72f9231e1799ee119ba979f8b5da95299e3295
detached

worktree D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/rhino-instance-export-fix/order_analyzer
HEAD 7498b8e71a7f27f2e6bf6d1995f3e1ffa56b3c73
branch refs/heads/codex/rhino-instance-export-fix

  archive/local-reference-bim-wip-20260816       f5736d9 feat: add local reference field evidence and overlays
  backup-before-frame-explainability-diagnostics 649767a restore: before region shape selection experiment
  backup-before-member-frame-trend               c76f559 feat: clean up inferred region semantics
  backup-before-region-shape-selection           aa7fbb0 feat: infer activity regions from furniture groups
  codex/d3-d5-evidence-research                  de1c53b chore: checkpoint D6 evidence before boundary repair
* codex/d6-analysis-domain-layout-handoff        a149420 docs: checkpoint D6 lifecycle conflict preservation
  codex/d6-lifecycle-status-contract-design      9672588 docs: checkpoint D6 lifecycle status-contract repair
  codex/d6-pairwise-channel-run2-design          de1c53b chore: checkpoint D6 evidence before boundary repair
  codex/d6-pairwise-channel-run2-repair-v1       f25d367 Repair D6 pairwise channel run 002 evidence contract
  codex/d6-pairwise-channel-run2-repair-v2       9672588 docs: checkpoint D6 lifecycle status-contract repair
  codex/ifc4-bim-description-pipeline            9ce888a feat: add weight-free multi-channel boundary evidence
+ codex/rhino-instance-export-fix                7498b8e (D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/rhino-instance-export-fix/order_analyzer) test: verify live Rhino IFC export
  codex/visualarq-source-adapter                 234b95c chore: ignore local worktrees
  feature/continuous-affordance-coverage         c4c3705 feat: score affordance coverage by continuous area
  feature/continuous-conflict-evaluator          1694110 docs: mark continuous conflict complete
  feature/entry-access-point                     0068432 feat: add explicit entry access points
  feature/local-reference-field                  ab12280 docs: specify and plan local reference field
  master                                         14eca2e feat: complete terminal geometry trend pipeline

No reset, rebase, squash, force push, branch deletion, git clean, git add ., or bulk move/delete was used. The baseline had 46 pre-existing untracked paths; the plan is excluded from that baseline.

## Explicit commit scope

- docs/project/evidence/d6-space-field-design-progress.md 鈥?Dated progress and handoff gate appended by this audit.
- docs/superpowers/plans/2026-10-06-d6-progress-git-provenance-checkpoint.md 鈥?Skill-required audit plan for reproducible checkpoint work.
- docs/project/evidence/d6-space-field-git-provenance-checkpoint-2026-10-06.md 鈥?Human-readable provenance report with complete baseline inventory.
- docs/project/evidence/d6-space-field-git-provenance-manifest-2026-10-06.json 鈥?Machine-readable provenance, hashes, scope, and self-consistency record.
- docs/project/evidence/d6-space-field-candidate-set-lifecycle-final-owner-decision.md 鈥?Completed owner decision accepting lifecycle principles as limited design evidence.

The final owner decision is the only pre-existing untracked design record selected for explicit staging. Review-stop bundles and temporary logs remain untracked.

## Full pre-existing untracked inventory

| Path | Baseline bytes | Baseline SHA-256 | Category | Integrity | Recommendation |
|---|---:|---|---|---|---|
| docs/project/evidence/d6-space-field-hard-column-comparison-validation.json | 4459 | 5f8f5062bb44aafaa56fd58b87870a14264406bf1d27b2681adee5a12e54df57 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-scope-audit.json | 2043 | 3cb693de27d4848d5428fb9d2c43583db1d52273bfe5338d5b7f75ec62499e29 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison.md | 5276 | 5ee974e559aa93fe0cbc98d51540c6c67582ffa53b35ef36d3ec81415753e11b | hard_column_comparison_bundle | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-real-ifc-boundary-candidate-comparison.md | 11211 | 145685a97ca28dbc4d7f20e730fd4e3946122341665a11be083c7120e8cd57c2 | real_ifc_design_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-real-ifc-boundary-candidate-comparison-owner-decision.md | 4013 | 233ea0cca5772bdab3621754fccf18309f40a1bdbb0a76bf15c4cede0ae9627f | real_ifc_design_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-schema.json | 640 | bf14e6ff35e4f3ac0f70bcd3db00c3ba3af4939a2ba173f17af732d3d665dd6f | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-fixtures.json | 26198 | 731926d3fc4dd14223baff875a3d419ef7b775b3df9368eb8b2c489faa1b9a95 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-before-after.json | 279845 | 9fae4a09b3ce362a09d464f038a75f2379dc4b4f90233898051d8ef7ee6776e7 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-owner-review.md | 2163 | 16503904ce90a4063009502431ed471c49a6604cf1150d311d14a278cdd00a11 | hard_column_comparison_bundle | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-real-ifc.json | 240581 | c913462abbd11e2db7281a333cb60d201ab6ce13b2dcf7b31f3d427683845b32 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-provenance.json | 1851 | 5f7a54300abea7d71d0d3280138bbba18535238d6007fb539106794039238bd3 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-real-ifc-pairwise-relationship-experiment.md | 5752 | 7c3bd96f4d748ccd0742ae23e2ef5c838621682803504e8a630be3676d44501b | real_ifc_design_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-scope-audit.json | 2184 | d528aeab1902c33d3ca71b80be2fb7822f8f4b5f7cba18087b866163e8f284fd | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-provenance.json | 1920 | d390fe8c1bdd5b93a6465d72fcba3228c450b6ab6dfdc12226082404a6081b11 | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1.md | 6397 | ec97fd5717e74d066efd4addc9330c8e5870f839e296087dad5b64b991dda4d8 | soft_field_boundary_repair_bundle | read_ok_nonempty_markdown | retain_untracked |
| full_pytest_checkpoint1b.log | 1099 | 98f80aa48382ed42a03ba8ab38f09a4e5cf1629380f57022ddebc6715d26db2b | temporary_log_or_artifact | preserved_preexisting_log; no rerun | retain_untracked |
| full_pytest_checkpoint1b.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | temporary_log_or_artifact | preserved_empty_stderr_log; no rerun | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-owner-review.md | 3005 | 1455bda9214d98f01dc1473a08397d436eaf1993e8b857e1dddfc70646f8e1de | soft_field_boundary_repair_bundle | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-before-after.json | 998 | 5a9f581f772f3298032cdd37619b0c5a936e4d8e65086a7ab7017dabc494f2b7 | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-artifact-manifest.json | 14984 | 5c0e6b22d68b2324eecdd6c6d53594981cf074c4b93be17683cc26e3a64eb8ea | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-candidates.json | 85668 | 44385072ca5d0479d017a1056f772a6cc35e9384afe1d56a290675d6d5efe357 | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-field.json | 967898 | 852d2b973a814d010f79021a1b37d8ec1f428575d31a232a562ccababa157349 | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-empty-space.json | 1330260 | 864d17b6a6e2ca8b372431e0ef87e37847292e4498e1bf3fdef234112b638d7d | soft_field_boundary_repair_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-candidate-set-lifecycle-precedence-experiment.md | 11309 | 5827c7870786b93387f20e9b32b196e7cfeb4dd6581e8cb1bd824465a9e1d8a0 | lifecycle_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-candidate-set-lifecycle-final-owner-decision.md | 3222 | ac7137c5fb22b5e47cb1ce64e93fff8b173d1557ac59d4b75cd07fa815996be5 | lifecycle_evidence | read_ok_nonempty_markdown | commit_explicit |
| docs/project/evidence/d6-space-field-candidate-set-lifecycle-precedence-owner-decision.md | 2061 | 370b5d4b8ef2c768c8545a0b24560c3e51bf565e98a57750d14293fae55acab4 | lifecycle_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-artifact-manifest.json | 9365 | ebe3abd77dc26808284c8ff426a8d017611dd5326b4e78073f711430fafe28c8 | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-candidate-set-lifecycle-render-repair-v1.md | 3773 | ccd6fe97c0d522113af8701cb24ace21facb8ee94aba372573363c75561e626a | lifecycle_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-repair-v4.md | 1966 | 8cd97a886f293810db27499634e5c2b6242a4d37dcd6a10ba6fc8cfc21efc53a | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-repair-v1-independent-review.md | 20992 | 8cb3470c5e050c22ec941031dae64d2543e33ab1d10a3412844071c94b50a484 | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-independent-review.md | 10603 | 4c404932cefc9c92fbe0df4740c86c77f0425fb3d17ad16b2843ef2b9f0be77b | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-repair-v3-status-contract.md | 635 | 790f16a3f5b73a9efe5593752b6caa5a9f9d59ffab94294ce0e6264ae613fae1 | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-repair-v4-status-contract.md | 740 | ee5e05d404ab09dcfde74a6e9240ddfd3a0782fd5f6000d0e8387a430eba779b | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-pairwise-channel-run002-repair-v3.md | 3144 | 68b34a6269694f4ae4228b3b98d21c66dcb330a423d3400c8817e2812162c577 | pairwise_run002_review_evidence | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-fixtures.json | 106114 | f22b870de038329b91fe0db540697ae4a362a97cf4fce650104f9d70f72689eb | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-validation.json | 5008 | 8a08f66b19bdacc54790d6042ab4eb2d74b118ebd44e7c3a6e3f2511478f5da9 | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-updated-diagnostic.json | 135419 | 47d82c5d2cc674e46ff74d060f429bf89900fbe38a934f64ddfab1b659b7a2ed | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit.md | 4108 | c3dbfd6c7ab166a9b913dea842f36d0ec9d2ae21a30e2a2a671fc4ca790ed09d | column_channel_audit_bundle | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-hard-column-comparison-artifact-manifest.json | 16263 | 99ce25a7829a232571ca22575a09d8d32783f5516a3e34ccded57b2ae7acb4a0 | hard_column_comparison_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-design-progress.md | 16068 | 20dcf9c8aebb1212b51e98abc913e15e6bdb1e5f1e636c8b96e813e18ab9d249 | progress_record | read_ok_nonempty_markdown | commit_explicit |
| docs/project/evidence/d6-space-field-column-channel-audit-scope.json | 808 | a11c456b4221e8cebe350394e891c1df4a447c7dd3a98d5c5d5720ae4c62942c | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-owner-review.md | 1043 | 535acd12416338bc3500f6a7ca03acd0bbd887af4a468c5d0aaa5cf75be9dd3e | column_channel_audit_bundle | read_ok_nonempty_markdown | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-git-scope.json | 586 | fc58f59fac68b1a327db2706ad72f46b86692116cf4f15b0b84b69714c4ff3ad | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-provenance.json | 1759 | 677e491de469646466bd2987e10490957959148e113c8cec6f1dd9ee9c28eb24 | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-schema.json | 410 | b8102211eaf99b6a992feeef0ce8c4567b040fba14bdeb8638c59117f8521e62 | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |
| docs/project/evidence/d6-space-field-column-channel-audit-real-ifc.json | 21782 | f043537b61a2d2a2a7cd5e6727e9714a920cd6b0c13ec544d0ed51667c1c2e31 | column_channel_audit_bundle | json_parse_ok; companion manifest/hash checks where present | retain_untracked |

## Retained untracked paths and correction rule

44 paths remain untracked and are preserved with baseline bytes/SHA-256 in the manifest. If a later owner decision explicitly accepts one bundle, stage only named paths after rehashing and confirming companion review/manifest/verification.

Correction rule: if any baseline path disappears, changes without changed_by_audit=true, fails JSON/hash/byte checks, or has a scope record inconsistent with its owner-review gate, stop and keep uncertain files untracked.

## Scope and validation

- Historical contract remains 23822 bytes with SHA-256 b8870bd8f5a1e4be60ac42a7a5a7792ff43b9cc43b5e628aaccd580a40dfca6d.
- 24 focused D6 JSON files parsed; broader scan parsed 30 D6/pairwise evidence JSON files.
- Three existing bundle manifests were rehashed read-only: 63 entries, no mismatch.
- Global diff-check and focused pre-stage diff-check exited 0.
- No full pytest, full IFC adapter, Blender, Bayesian/ML, selector, or production API work was run.
- Existing full_pytest_checkpoint1b.log and empty .err remain historical temporary artifacts, not fresh test evidence.
- Report and manifest exclude their own hashes to avoid a cyclic reference; all baseline rows and other created-file hashes are recomputable.

## AnalysisDomain/UI handoff design gate

The next gate is design-only. It must define candidate input/lifecycle, automatic versus authored/user precedence, explicit confirmation/rejection/replacement/manual closed-boundary actions, hover/highlight/green-region display, status-to-UI mapping, wall/column/door/window/opening/furniture/context roles, and refusal of free-space, connectivity, and membership results without a qualified domain or after unresolved conflict. It must preserve source provenance and candidate lineage while keeping automatic candidates retained and ambiguity visible.

Real IFC is limited to input mapping and visualization exploration. The next gate must not choose selector, threshold, resolution, geometry backend, Bayesian/ML method, or production API, and must not claim production integration.

## Unresolved questions

- Which authored/user domain inputs count as qualified after the design gate.
- How UI actions serialize actor/time/reason and how conflict review resolves a relation.
- Final display vocabulary and UI component boundaries.
- How future downstream contracts express domain refusal without prematurely introducing a production enum.

## Audit command ledger

| Command | Exit |
|---|---:|
| git branch --show-current | 0 |
| git rev-parse HEAD | 0 |
| git log --oneline --decorate --graph -25 | 0 |
| git branch -vv | 0 |
| git rev-parse --abbrev-ref --symbolic-full-name @{u} | 128 |
| git worktree list --porcelain | 0 |
| git status --short --branch --untracked-files=all | 0 |
| git ls-files --others --exclude-standard | 0 |
| three git merge-base --is-ancestor checks | 0 |
| pixi run python -B - JSON/hash/manifest audit | 0 |
| git diff --no-ext-diff --check | 0 |

## Final status at report generation

The report and manifest are new audit artifacts for explicit commit. The 46 baseline paths are preserved; only the progress record is intentionally modified. Post-stage and post-commit status, staged names, cached whitespace, and commit SHA are recorded after explicit staging.

## Pre-commit staging evidence

Explicit staging produced exactly these five `A` paths:

- `docs/project/evidence/d6-space-field-candidate-set-lifecycle-final-owner-decision.md`
- `docs/project/evidence/d6-space-field-design-progress.md`
- `docs/project/evidence/d6-space-field-git-provenance-checkpoint-2026-10-06.md`
- `docs/project/evidence/d6-space-field-git-provenance-manifest-2026-10-06.json`
- `docs/superpowers/plans/2026-10-06-d6-progress-git-provenance-checkpoint.md`

`git diff --cached --check` exited 0 with no diagnostics. No other path was staged. The 44 retained baseline untracked paths remain outside the index.

## Checkpoint commit

- Commit: `b44eaedb72204a41c9ecedbfdfe720534e494e0c`
- Parent: `a149420faf5dfef9d89293a4c415a08df4964581`
- Message: `docs: checkpoint D6 progress and Git provenance`
- Commit command exit code: 0
- Post-commit index: clean
- Post-commit status command exit code: 0
- Post-commit untracked count: 44; all retained baseline paths remained present and unmodified.

STOP FOR D6 PROGRESS AND GIT PROVENANCE CHECKPOINT REVIEW
