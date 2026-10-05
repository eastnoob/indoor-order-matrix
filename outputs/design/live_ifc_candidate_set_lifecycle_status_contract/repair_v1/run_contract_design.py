"""Build the repaired, design-only D6 lifecycle status-contract package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INPUT = REPO_ROOT / "outputs/design/live_ifc_candidate_set_lifecycle_experiment"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/repair_v1"
DATE = "2026-10-05"
CORE_FILES = (
    "status_contract_matrix.json",
    "lifecycle_transition_fixtures.json",
    "lifecycle_transition_truth.json",
    "provenance.json",
    "lifecycle_transition_diagram.mmd",
)


def read_json(path: Path) -> Any:
    """Read one UTF-8 JSON evidence artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Write sorted, newline-terminated JSON for deterministic reruns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text artifact with one terminal newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_real_context(input_root: Path) -> dict[str, Any]:
    """Extract the approved real-IFC lifecycle facts without reopening the IFC."""
    case = read_json(input_root / "real_ifc_case.json")
    records = case["records"]
    candidates = [
        {
            "candidate_id": record["candidate_id"],
            "candidate_version_id": f"{record['candidate_id']}:v1",
            "lifecycle_state": "provisional",
            "evidence_state": "diagnostic_only",
            "derived_display_labels": ["provisional_diagnostic_only"],
        }
        for record in records
    ]
    return {
        "record_class": "real_ifc",
        "source_artifact": "outputs/design/live_ifc_candidate_set_lifecycle_experiment/real_ifc_case.json",
        "candidate_set_id": case["candidate_set_id"],
        "candidate_count": case["candidate_count"],
        "candidate_ids": [record["candidate_id"] for record in records],
        "candidates": candidates,
        "candidate_set_facts": {
            "unassigned": True,
            "ambiguous": False,
            "singleton": False,
            "explicit_selection_state": "none",
            "selection_relation_present": True,
            "selection_relation": {"selection_state": "none", "selected_candidate_id": None, "recorded_at": DATE},
        },
        "qualified_authored_domain": False,
        "automatic_candidate_promoted": False,
        "evidence_only": True,
        "synthetic_controls_must_not_be_interpreted_as_real_ifc": True,
    }


def lifecycle_event(event_id: str, event_type: str, target_ids: list[str], sequence: int) -> dict[str, Any]:
    """Create an ordered, auditable synthetic lifecycle event."""
    return {
        "event_id": event_id,
        "event_type": event_type,
        "target_ids": target_ids,
        "event_sequence": sequence,
        "recorded_at": DATE,
        "actor": "synthetic_owner",
        "reason_code": f"design_control_{event_type}",
        "is_production_action": False,
        "provenance_required": True,
    }


def build_status_matrix() -> dict[str, Any]:
    """Return the repaired layer and status proposal without freezing an API."""
    concepts = [
        {"term": "provisional", "layer": "lifecycle_state", "classification": "candidate-level lifecycle state", "semantics": "Automatic candidate is retained and has no confirmation, rejection, or replacement action."},
        {"term": "user_confirmed", "layer": "lifecycle_state", "classification": "candidate-level lifecycle state", "semantics": "An explicit actor confirmed a stable candidate version or authored domain."},
        {"term": "rejected", "layer": "lifecycle_state", "classification": "candidate-level lifecycle state", "semantics": "An explicit actor rejected a candidate version; evidence remains retained."},
        {"term": "replaced", "layer": "lifecycle_state", "classification": "candidate-level lifecycle state", "semantics": "A prior version was superseded by an explicit replacement relation."},
        {"term": "conflict", "layer": "lifecycle_relation", "classification": "cross-source relation / derived set and candidate label", "semantics": "Automatic and authored/user records disagree and the disagreement remains unresolved."},
        {"term": "diagnostic_only", "layer": "evidence_state", "classification": "candidate/set evidence-quality state", "semantics": "Evidence is displayable and auditable but cannot promote a formal domain."},
        {"term": "not_available", "layer": "downstream_availability", "classification": "derived availability state", "semantics": "A consumer evaluated dependencies and cannot produce the requested downstream result."},
        {"term": "partial", "layer": "evidence_state", "classification": "candidate/set evidence-quality state", "semantics": "Some required evidence is present and some is missing or incomplete."},
        {"term": "invalid", "layer": "evidence_state", "classification": "candidate/set evidence-quality state", "semantics": "A present record fails an applicable validity check."},
        {"term": "unsupported", "layer": "evidence_state", "classification": "candidate/set evidence-quality state", "semantics": "The representation or operation is outside the supported evidence contract."},
        {"term": "unassigned", "layer": "candidate_set_facts", "classification": "set-level fact / derived label", "semantics": "No authored or user assignment relation is recorded."},
        {"term": "ambiguous", "layer": "candidate_set_facts", "classification": "set-level fact / derived label", "semantics": "Multiple plausible candidates or unresolved interpretations remain without selection."},
        {"term": "singleton", "layer": "candidate_set_facts", "classification": "set-level cardinality fact", "semantics": "Exactly one active, non-replaced candidate remains; this never confirms it."},
        {"term": "explicit_selection_state", "layer": "candidate_set_facts", "classification": "set-level selection fact", "semantics": "Recorded selection relation state; none plus null selected ID means explicit no-selection."},
        {"term": "provisional_diagnostic_only", "layer": "derived_display_label", "classification": "derived label only", "semantics": "Display label derived from lifecycle_state=provisional and evidence_state=diagnostic_only; never serialized as an independent source-of-truth state."},
    ]
    return {
        "proposal_only": True,
        "production_enum_names_frozen": False,
        "production_public_api_frozen": False,
        "production_selector_implemented": False,
        "layers": {
            "lifecycle_state": ["provisional", "user_confirmed", "rejected", "replaced"],
        "evidence_state": ["diagnostic_only", "partial", "invalid", "unsupported"],
        "downstream_availability": ["available", "not_available", "partial"],
            "candidate_set_facts": ["unassigned", "ambiguous", "singleton", "explicit_selection_state"],
            "lifecycle_relations_events": ["confirm", "reject", "replace", "assign_authored_domain", "record_conflict", "manual_boundary_edit"],
            "derived_display_labels": ["provisional_diagnostic_only"],
        },
        "concepts": concepts,
        "selection_semantics": {
            "explicit_no_selection": "selection_relation_present=true, selection_state=none, selected_candidate_id=null",
            "selection_not_recorded": "selection_relation_present=false and no selection relation object",
            "rule": "Explicit no-selection and absent selection relation are distinct and must not be conflated.",
        },
        "contract_shapes": {
            "status_fields": {"strengths": ["simple reads", "compact UI binding"], "risks": ["overloaded status", "lost event history", "ambiguous evidence/lifecycle meaning"], "role": "derived view only"},
            "explicit_relations_events_plus_derived_views": {"strengths": ["orthogonal layers", "auditable history", "conflict preservation", "no enum freeze"], "risks": ["requires deterministic aggregation", "requires event validation"], "role": "recommended design-only source-of-truth shape"},
            "recommendation": "Use explicit relations/events as source of truth and derive any display status. This is not a production schema decision.",
        },
        "transition_rules": {
            "allowed": [
                {"from": "provisional", "event": "confirm", "to": "user_confirmed", "condition": "explicit actor, stable version, ordered event, no unresolved blocking conflict"},
                {"from": "provisional", "event": "reject", "to": "rejected", "condition": "explicit actor, reason, ordered event"},
                {"from": "active_version", "event": "replace", "to": "replaced", "condition": "new version and prior version reference retained"},
                {"from": "candidate_set", "event": "assign_authored_domain", "to": "authored_assignment", "condition": "explicit relation; automatic candidates remain provenance"},
                {"from": "candidate_set", "event": "record_conflict", "to": "conflict", "condition": "both sides retained; future resolution remains deferred"},
                {"from": "active_version", "event": "manual_boundary_edit", "to": "replaced", "condition": "before/after geometry and version references retained"},
            ],
            "forbidden": [
                {"from": "singleton", "event": "auto_promote", "to": "user_confirmed", "reason": "singleton is a fact only"},
                {"from": "diagnostic_only", "event": "promote_domain", "to": "user_confirmed", "reason": "evidence quality cannot create confirmation"},
                {"from": "partial", "event": "treat_as_complete", "to": "available", "reason": "limitations remain visible"},
                {"from": "invalid", "event": "fallback_to_bbox", "to": "available", "reason": "unqualified fallback is forbidden"},
                {"from": "rejected", "event": "delete_evidence", "to": "absent", "reason": "rejection preserves evidence"},
                {"from": "replaced", "event": "delete_prior_version", "to": "absent", "reason": "replacement preserves history"},
                {"from": "conflict", "event": "silent_resolve", "to": "user_confirmed", "reason": "future resolution event is explicitly deferred"},
            ],
        },
        "precedence_and_conflict": [
            "Qualified authored/user input has precedence for downstream domain use by owner principle, while automatic candidates remain provenance.",
            "Automatic and authored/user disagreement remains an unresolved conflict; no production resolution rule is invented here.",
            "Unresolved conflict cannot silently yield downstream availability; a future explicit resolution event is deferred.",
        ],
        "aggregation": {
            "candidate_set": ["candidate_count retains history", "active_candidate_count excludes replaced versions", "singleton is active count equal to one", "ambiguous is multiple plausible active candidates or unresolved interpretation", "unassigned is no assignment relation"],
            "candidate": ["lifecycle_state comes from ordered explicit events", "evidence_state is independent and may remain diagnostic_only after confirmation", "rejected and replaced versions remain queryable"],
        },
        "event_ordering": {
            "proposal": "Use a monotonic event_sequence per candidate-set lineage as the primary order.",
            "alternative": "Full timestamp plus stable event-id tie-break is an acceptable later design alternative.",
            "status": "Design proposal only; not a frozen production schema.",
        },
        "null_and_not_available": {
            "null": "Null records absence of a relation or selected ID.",
            "not_available": "Not_available is a downstream availability result after dependency evaluation; it is not a lifecycle state.",
            "rules": ["Explicit no-selection uses selected_candidate_id=null plus selection_state=none.", "Absent selection relation is not recorded and must remain distinguishable.", "Missing domain, unresolved conflict, invalid required evidence, unsupported required representation, or incomplete required evidence propagates not_available.", "No empty geometry, zero, or diagnostic frame substitutes for unavailable qualified output."],
        },
        "identity_provenance_ui": {
            "stable_ids": ["candidate_set_id", "candidate_id", "candidate_version_id", "event_id", "relation_id"],
            "required_provenance": ["real_ifc or synthetic_control class", "source IDs/artifact", "units/coordinate frame/analysis plane", "actor/date/sequence/reason", "prior and replacement version refs", "uncertainty and assumptions"],
            "ui": ["Confirmation requires explicit candidate and provenance.", "Rejection hides from active view but keeps evidence history.", "Replacement/manual edit creates a new version and shows prior history.", "Conflict shows both sides and disables silent promotion.", "Singleton displays confirmation-needed, never confirmed."],
        },
        "unresolved_owner_decisions": ["Final production names and serialization.", "Whether qualified authored input can be consumed while conflict remains visible.", "Conflict-resolution authority and override event.", "Active-count rules across rejected/replaced histories.", "Formal AnalysisDomain promotion and all selector/backend/threshold decisions."],
    }


def control(fixture_id: str, candidate_set: dict[str, Any], records: list[dict[str, Any]], events: list[dict[str, Any]], expected: dict[str, Any]) -> dict[str, Any]:
    """Build one isolated synthetic control fixture."""
    return {"fixture_id": fixture_id, "record_class": "synthetic_control", "candidate_set": candidate_set, "candidate_records": records, "events": events, "expected_after_events": expected}


def candidate(candidate_id: str, version_id: str, lifecycle_state: str = "provisional", evidence_state: str = "diagnostic_only", **extra: Any) -> dict[str, Any]:
    """Build a candidate record with separated lifecycle and evidence fields."""
    record = {"candidate_id": candidate_id, "candidate_version_id": version_id, "lifecycle_state": lifecycle_state, "evidence_state": evidence_state}
    record.update(extra)
    return record


def build_fixtures(real_context: dict[str, Any]) -> dict[str, Any]:
    """Build the real-IFC context and synthetic controls for every repaired rule."""
    auto = "synthetic:auto:001"
    v1 = "synthetic:edit:v1"
    v2 = "synthetic:edit:v2"
    explicit_none = {"selection_state": "none", "selected_candidate_id": None, "recorded_at": DATE}
    return {
        "fixture_version": "repair-v1-design-only-2026-10-05",
        "proposal_only": True,
        "real_ifc_context": real_context,
        "synthetic_controls": [
            control("explicit_no_selection", {"candidate_set_id": "synthetic:set:no-selection:001", "unassigned": True, "ambiguous": False, "singleton": True, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate(auto, auto + ":v1")], [], {"selection_state": "none", "selected_candidate_id": None, "lifecycle_state": "provisional", "evidence_state": "diagnostic_only", "derived_display_label": "provisional_diagnostic_only", "downstream_availability": "not_available"}),
            control("selection_relation_absent", {"candidate_set_id": "synthetic:set:selection-absent:001", "unassigned": True, "ambiguous": False, "singleton": True, "explicit_selection_state": None, "selection_relation_present": False}, [candidate(auto, auto + ":v1")], [], {"selection_relation_recorded": False, "selected_candidate_id": None, "meaning": "selection_not_recorded"}),
            control("explicit_confirmation_preserves_diagnostic_evidence", {"candidate_set_id": "synthetic:set:confirm:001", "unassigned": False, "ambiguous": False, "singleton": True, "explicit_selection_state": "candidate_id", "selection_relation_present": True, "selection_relation": {"selection_state": "candidate_id", "selected_candidate_id": auto, "recorded_at": DATE}}, [candidate(auto, auto + ":v1")], [lifecycle_event("evt:confirm:001", "confirm", [auto + ":v1"], 1)], {"lifecycle_state": "user_confirmed", "evidence_state": "diagnostic_only", "derived_display_label": None, "evidence_improved_automatically": False}),
            control("explicit_rejection_preserves_evidence", {"candidate_set_id": "synthetic:set:reject:001", "unassigned": True, "ambiguous": False, "singleton": True, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate(auto, auto + ":v1", geometry_retained=True)], [lifecycle_event("evt:reject:001", "reject", [auto + ":v1"], 1)], {"lifecycle_state": "rejected", "evidence_state": "diagnostic_only", "evidence_retained": True}),
            control("replacement_preserves_history_and_evidence", {"candidate_set_id": "synthetic:set:replace:001", "unassigned": True, "ambiguous": False, "singleton": True, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate(v1, v1), candidate(v2, v2, prior_candidate_version_refs=[v1])], [lifecycle_event("evt:replace:001", "replace", [v1, v2], 1)], {"prior_version_lifecycle_state": "replaced", "new_version_lifecycle_state": "provisional", "prior_version_evidence_state": "diagnostic_only", "new_version_evidence_state": "diagnostic_only", "prior_version_retained": True}),
            control("manual_boundary_edit_is_ordered_replacement", {"candidate_set_id": "synthetic:set:edit:001", "unassigned": True, "ambiguous": False, "singleton": True, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate(v1, v1, geometry="before"), candidate(v2, v2, geometry="after", prior_candidate_version_refs=[v1])], [lifecycle_event("evt:edit:001", "manual_boundary_edit", [v1, v2], 1)], {"prior_version_lifecycle_state": "replaced", "old_geometry_mutated": False, "manual_edit_provenance": True}),
            control("authored_domain_precedence_retains_automatic", {"candidate_set_id": "synthetic:set:authored:001", "unassigned": False, "ambiguous": False, "singleton": False, "explicit_selection_state": "authored_domain", "selection_relation_present": True, "selection_relation": {"selection_state": "authored_domain", "selected_candidate_id": "synthetic:authored:001", "recorded_at": DATE}}, [candidate("synthetic:auto:a", "synthetic:auto:a:v1"), candidate("synthetic:auto:b", "synthetic:auto:b:v1"), candidate("synthetic:authored:001", "synthetic:authored:001:v1", lifecycle_state="user_confirmed", evidence_state="diagnostic_only")], [lifecycle_event("evt:author:001", "assign_authored_domain", ["synthetic:authored:001"], 1)], {"authored_precedence": True, "automatic_candidates_retained": True, "automatic_winner": False}),
            control("unresolved_conflict_defers_resolution", {"candidate_set_id": "synthetic:set:conflict:001", "unassigned": False, "ambiguous": True, "singleton": False, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate("synthetic:auto:conflict", "synthetic:auto:conflict:v1"), candidate("synthetic:authored:conflict", "synthetic:authored:conflict:v1", lifecycle_state="user_confirmed")], [lifecycle_event("evt:conflict:001", "record_conflict", ["synthetic:auto:conflict", "synthetic:authored:conflict"], 1)], {"conflict": True, "unresolved": True, "future_resolution_event": "deferred", "downstream_availability": "not_available", "automatic_winner": False}),
            control("evidence_quality_does_not_create_winner", {"candidate_set_id": "synthetic:set:evidence:001", "unassigned": True, "ambiguous": True, "singleton": False, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [candidate("synthetic:partial", "synthetic:partial:v1", evidence_state="partial"), candidate("synthetic:invalid", "synthetic:invalid:v1", evidence_state="invalid"), candidate("synthetic:unsupported", "synthetic:unsupported:v1", evidence_state="unsupported")], [], {"evidence_states_retained": ["partial", "invalid", "unsupported"], "automatic_winner": False, "downstream_availability": "not_available"}),
             control("missing_domain_propagates_not_available", {"candidate_set_id": "synthetic:set:missing:001", "unassigned": True, "ambiguous": False, "singleton": False, "explicit_selection_state": "none", "selection_relation_present": True, "selection_relation": explicit_none}, [], [], {"selected_candidate_id": None, "downstream_availability": "not_available", "availability_reason": "missing_qualified_authored_domain"}),
        ],
    }


def build_truth() -> dict[str, Any]:
    """Return transition truth and repair-specific invariants."""
    return {
        "proposal_only": True,
        "transition_truth": [
            {"from": "provisional", "event": "confirm", "to": "user_confirmed", "allowed": True},
            {"from": "provisional", "event": "reject", "to": "rejected", "allowed": True},
            {"from": "active_version", "event": "replace", "to": "replaced", "allowed": True},
            {"from": "candidate_set", "event": "assign_authored_domain", "to": "authored_assignment", "allowed": True},
            {"from": "candidate_set", "event": "record_conflict", "to": "conflict", "allowed": True},
            {"from": "active_version", "event": "manual_boundary_edit", "to": "replaced", "allowed": True},
            {"from": "singleton", "event": "auto_promote", "to": "user_confirmed", "allowed": False},
            {"from": "diagnostic_only", "event": "promote_domain", "to": "user_confirmed", "allowed": False},
            {"from": "partial", "event": "treat_as_complete", "to": "available", "allowed": False},
            {"from": "invalid", "event": "fallback_to_bbox", "to": "available", "allowed": False},
            {"from": "conflict", "event": "silent_resolve", "to": "user_confirmed", "allowed": False},
        ],
        "invariants": [
            "provisional_diagnostic_only is a derived label only and never an independent source-of-truth state.",
            "Confirmation changes lifecycle_state to user_confirmed while evidence_state may remain diagnostic_only.",
            "Rejection and replacement retain evidence states and version history.",
            "Explicit no-selection is selection_relation_present=true plus selection_state=none and selected_candidate_id=null.",
            "Absent selection relation is selection_relation_present=false and means selection was not recorded.",
            "Unresolved conflict retains automatic and authored/user records and blocks silent downstream availability.",
            "event_sequence is monotonic per candidate-set lineage; date-only recorded_at is not the ordering key.",
            "Synthetic controls cannot be used as real-IFC conclusions.",
        ],
        "required_event_fields": ["event_id", "event_type", "target_ids", "event_sequence", "recorded_at", "actor", "reason_code", "is_production_action", "provenance_required"],
        "deferred_events": ["resolve_conflict"],
    }


def build_provenance(real_context: dict[str, Any]) -> dict[str, Any]:
    """Record repair scope, current Git facts, evidence limits, and provenance."""
    return {
        "artifact_type": "d6_lifecycle_status_contract_repair_v1",
        "date": DATE,
        "proposal_only": True,
        "repair_of": "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/",
        "repair_blocker": "provisional_diagnostic_only conflated lifecycle and evidence layers in the original package.",
        "sources": ["AGENTS.md", "docs/project/evidence/d6-space-field-candidate-set-lifecycle-final-owner-decision.md", "docs/project/evidence/d6-space-field-candidate-set-lifecycle-render-repair-v1.md", "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/"],
        "real_ifc_context": real_context,
        "git_facts": {"branch": "codex/d6-pairwise-channel-run2-repair-v2", "preexisting_untracked_paths": 46, "outputs_design_ignored_by_git_info_exclude": True, "tracked_production_changes": False, "new_branch_created": False},
        "ignored_outputs_handling": "The repaired package is under outputs/design, which is ignored by .git/info/exclude. The repair record under docs/project/evidence is the auditable tracked-scope candidate; no git add . was used.",
        "scope": {"production_code_modified": False, "adapters_modified": False, "neutral_scene_modified": False, "public_api_modified": False, "tests_modified": False, "dependencies_modified": False, "source_ifc_opened": False, "user_blender_files_modified": False, "full_ifc_adapter_rerun": False, "full_pytest_rerun": False, "selector_implemented": False, "candidate_promoted_to_analysis_domain": False},
        "skills_and_method": ["stop-that-shit", "experimental-design", "scientific-critical-thinking", "scientific-visualization", "verification-before-completion"],
        "evidence_limitations": ["Real IFC is reused from serialized evidence only.", "Synthetic controls demonstrate contract relationships, not real-IFC behavior.", "Production enum names, APIs, conflict resolution, selectors, thresholds, geometry backend, and downstream promotion remain deferred."],
    }


def build_diagram() -> str:
    """Return a Mermaid diagram with explicit layers and unresolved conflict."""
    return """flowchart TD
  SF[Candidate-set facts] --> UA[unassigned]
  SF --> AM[ambiguous]
  SF --> SG[singleton]
  SF --> ES[explicit_selection_state]
  LS[lifecycle_state] --> PR[provisional]
  LS --> UC[user_confirmed]
  LS --> RJ[rejected]
  LS --> RP[replaced]
  EV[evidence_state] --> DO[diagnostic_only]
  EV --> PA[partial]
  EV --> IV[invalid]
  EV --> US[unsupported]
  AV[downstream_availability] --> OK[available]
  AV --> ENA[not_available]
  AV --> APART[partial availability]
  PR -->|confirm event| UC
  PR -->|reject event| RJ
  PR -->|replace event| RP
  RP --> NV[new candidate version]
  ME[manual_boundary_edit] --> RP
  AU[assign_authored_domain] --> AP[authored precedence view]
  PR -. retained provenance .-> AP
  AU -->|disagreement| CF[conflict unresolved]
  PR -. competing automatic evidence .-> CF
  CF -. future resolve_conflict deferred .-> CF
  ES -->|none + selected id null| NS[explicit no-selection]
  ES -. relation absent .-> NR[selection not recorded]
  UC --> DA[downstream availability]
  AP --> DA
  UA --> DNA[downstream not_available]
  CF --> DNA
  DO --> AV
  PA --> AV
  IV --> AV
  US --> AV
  UA --> AV
  CF --> AV
  AV --> DNA
  SG -. never confirms .-> PR
  PR -. derived with diagnostic_only .-> DL[provisional_diagnostic_only display label]
  classDef fact fill:#dbeafe,stroke:#1d4ed8,color:#111827;
  classDef life fill:#dcfce7,stroke:#15803d,color:#111827;
  classDef evidence fill:#fef3c7,stroke:#b45309,color:#111827;
  classDef availability fill:#ede9fe,stroke:#6d28d9,color:#111827;
  classDef blocked fill:#fee2e2,stroke:#b91c1c,color:#111827;
  class SF,UA,AM,SG,ES,NS,NR fact;
  class LS,PR,UC,RJ,RP,NV,ME,AU,AP,DL life;
  class EV,DO,PA,IV,US evidence;
  class AV,OK,ENA,APART availability;
  class CF,DA,DNA blocked;
"""


def main() -> None:
    """Write repaired core artifacts without touching the original package."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_root = args.output.resolve()
    real_context = load_real_context(args.input.resolve())
    write_json(output_root / "status_contract_matrix.json", build_status_matrix())
    write_json(output_root / "lifecycle_transition_fixtures.json", build_fixtures(real_context))
    write_json(output_root / "lifecycle_transition_truth.json", build_truth())
    write_json(output_root / "provenance.json", build_provenance(real_context))
    write_text(output_root / "lifecycle_transition_diagram.mmd", build_diagram())
    print(json.dumps({"status": "written", "output": str(output_root), "core_files": list(CORE_FILES)}, sort_keys=True))


if __name__ == "__main__":
    main()
