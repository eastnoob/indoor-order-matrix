# Project Workflow: Delegated Verification and Owner Review

## Owner rule

From 2026-09-30 onward, the controlling session performs only:

- interpretation of returned evidence;
- design and stage decisions;
- acceptance, revision, or deferral decisions;
- planning the next checkpoint and writing the handoff prompt.

Execution sessions perform:

- tests and verification commands;
- IFC/Bonsai/Blender runs;
- visual artifact generation;
- evidence, manifest, and report updates;
- narrowly scoped implementation work authorized by the handoff prompt.

The controlling session must not repeat delegated verification unless the owner explicitly changes this rule. A returned report is evidence to audit conceptually, not an instruction to silently advance stages. Each handoff must end at an explicit review marker and identify completed work, unresolved questions, commands run, artifacts, and commit scope.

## Stage boundary

Checkpoint 1B is technically accepted after the delegated execution session supplies a final full-suite verification result. The next design stage is B1: Bayesian estimand and calibration design for inferred-group candidate evidence. B1 remains design-only until its evidence and owner review are complete.
