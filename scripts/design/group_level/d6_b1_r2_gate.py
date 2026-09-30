"""Run the D6 B1-R2 Bayesian model-selection and implementation-design gate.

This script consumes the frozen R1 observations, truth, inference, and recipe
artifacts. It never passes truth into inference and never fits a richer model;
the richer route is recorded as a design candidate with explicit deferrals.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring


ROOT = Path(__file__).resolve().parents[3]
R1 = ROOT / "docs/project/evidence/d6-b1-r1-artifacts"
OUT = ROOT / "docs/project/evidence/d6-b1-r2-artifacts"
SEED = 61031


def digest(path: Path) -> str:
    """Return the SHA-256 digest used to bind this gate to R1 inputs."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    """Write stable, reviewable JSON evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load(name: str) -> object:
    """Load one R1 JSON artifact without modifying it."""
    return json.loads((R1 / name).read_text(encoding="utf-8"))


def status_audit(observations: dict) -> dict:
    """Count statuses by evidence role while retaining fixture-level semantics."""
    counts = Counter()
    fixture_counts = defaultdict(Counter)
    for fixture in observations["fixtures"]:
        for group in fixture["groups"]:
            for channel, record in group["scene_observations"].items():
                key = f"group_{channel}"
                counts[key, record["status"]] += 1
                fixture_counts[fixture["fixture_id"]][key, record["status"]] += 1
        for relation in fixture["pair_relations"]:
            for key, field in (("normalized_gap", "gap_evidence"),
                               ("contact_overlap", "pair_support_evidence"),
                               ("space_role", "space_role_record")):
                counts[key, relation[field]["status"]] += 1
                fixture_counts[fixture["fixture_id"]][key, relation[field]["status"]] += 1
    return {"global": {f"{role}:{status}": count for (role, status), count in sorted(counts.items())},
            "fixture_count": len(fixture_counts),
            "aggregation_unit": "fixture; nested records are audit counts only"}


def validate_isolation(observations: dict, truth: dict, splits: dict, inference: dict) -> dict:
    """Check truth isolation, whole-fixture holdout, and shared observation identity."""
    obs_ids = {row["fixture_id"] for row in observations["fixtures"]}
    truth_ids = {row["fixture_id"] for row in truth["fixtures"]}
    split_map = {row["fixture_id"]: row["split"] for row in splits["fixtures"]}
    dev = {key for key, value in split_map.items() if value == "development"}
    hold = {key for key, value in split_map.items() if value == "holdout"}
    assert obs_ids == truth_ids == set(split_map)
    assert len(dev) == 32 and len(hold) == 16 and not dev & hold
    assert inference["truth_consumed"] is False
    assert inference["input_sha256"] == digest(R1 / "observation-manifest.json")
    shared_refs = 0
    candidate_specific = 0
    for fixture in observations["fixtures"]:
        groups = {row["group_id"]: row for row in fixture["groups"]}
        scopes = fixture["candidate_scopes"]
        reference_sets = [scope["shared_group_observation_refs"] for scope in scopes]
        assert all(refs == reference_sets[0] for refs in reference_sets)
        shared_refs += len(reference_sets[0]) * len(scopes)
        for scope in scopes:
            evidence = scope["candidate_specific_evidence"]
            assert evidence["records_duplicated"] is False
            assert evidence["kind"] == "scope projection of shared pair observations"
            candidate_specific += len(evidence["pair_relation_refs"])
            for group_id, signature in reference_sets[0].items():
                row = groups[group_id]
                encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                assert hashlib.sha256(encoded).hexdigest() == signature
    return {"observation_fixture_count": len(obs_ids), "development_fixtures": len(dev),
            "holdout_fixtures": len(hold), "shared_group_scope_refs": shared_refs,
            "candidate_specific_pair_refs": candidate_specific,
            "truth_consumed_by_inference": False, "truth_joined_after_frozen_inference": True,
            "nested_units_are_not_iid": True}


def route_decision() -> dict:
    """Return the owner-facing decision matrix for diagnostic and richer routes."""
    return {
        "A_diagnostic_only_bayesian": {
            "status": "APPROVE_AS_DIAGNOSTIC_ONLY",
            "estimand": "P(Z[g,k]=1 | E,K,M) for authored group g in externally frozen candidate scope k",
            "output": "posterior probability plus status/provenance trace; no selector action",
            "admitted_first_version": [
                "group geometry summary when computed or partial with named observed component",
                "trend/frame binary diagnostic when computed or partial",
                "Z/clearance binary diagnostic when computed or partial",
                "contact/overlap support when computed or partial",
            ],
            "audit_only_or_deferred": [
                "continuous normalized gap (scale evidence only in A)",
                "wall/opening barrier (not_available in R1; deferred)",
                "empty-space role evidence (independent role output; never membership likelihood)",
                "CAR/spatial covariance (not_identifiable)",
            ],
            "boundary": "synthetic and diagnostic interpretation; not a production selector, accuracy claim, or psychological validity claim",
        },
        "B_richer_bayesian_design": {
            "status": "DESIGN_ONLY__FIT_NOT_RUN",
            "estimand": "same membership-level estimand, with joint evidence and explicit dependence model",
            "likelihood": [
                "continuous normalized gap likelihood with scale/provenance calibration",
                "trend/frame direction likelihood",
                "Z/clearance and wall/opening barrier only when source availability and orientation are validated",
            ],
            "dependence": [
                "shared-node/shared-source hierarchical blocks",
                "candidate overlap and singleton/unassigned/ambiguous states as estimand outputs",
                "CAR/spatial covariance remains not_identifiable until replicated spatial graphs exist",
            ],
            "status_policy": "computed admitted; partial admits named components; missing/invalid/not_available/conflict propagate and do not silently contribute",
            "calibration_and_ppc": "must be predeclared; PPC is required for a joint generative fit and cannot be replaced by calibration",
            "implementation": "not entered in B1-R2",
        },
    }


def same_input_comparison(report: dict, recipes: dict) -> dict:
    """Summarize R1 Bayesian and deterministic views on identical observations."""
    priors = report["prior_sensitivity"]
    bayes_rows = []
    for key, row in sorted(priors.items()):
        bayes_rows.append({"configuration": key, "prior": row["prior"],
                           "dependence": row["dependence"],
                           "holdout_mean_fixture_brier": row["mean_fixture_brier"],
                           "prevalence_baseline_brier": row["mean_fixture_prevalence_baseline_brier"],
                           "mean_prior_posterior_shift": row["mean_fixture_prior_posterior_shift"],
                           "interpretation": "synthetic computational gate; no winner selected"})
    deterministic = []
    for name, row in sorted(report["deterministic_recipe_comparison"].items()):
        deterministic.append({"recipe": name,
                              "holdout_mean_fixture_pair_f1": row["mean_fixture_pair_f1"],
                              "truth_comparison_permitted": row["truth_comparison_permitted"],
                              "interpretation": "deterministic strength/support; not probability"})
    assert len(recipes["outputs"]) == 1584
    return {"same_observation_manifest_sha256": digest(R1 / "observation-manifest.json"),
            "bayesian_diagnostic_rows": bayes_rows,
            "deterministic_recipe_rows": deterministic,
            "space_profile_membership_truth": "prohibited",
            "winner_or_threshold_selected": False,
            "nested_member_pair_scope_iid_assumption": False}


def render_matrix(path: Path, decisions: dict) -> None:
    """Render a compact route/evidence decision figure without implying a score."""
    rows = [
        ("geometry", "A: admitted", "B: joint likelihood design"),
        ("trend/frame", "A: admitted if valid", "B: direction likelihood"),
        ("Z/clearance", "A: admitted if valid", "B: availability-gated"),
        ("contact/overlap", "A: admitted if valid", "B: shared-source dependence"),
        ("normalized gap", "A: audit-only scale", "B: continuous likelihood design"),
        ("wall/opening barrier", "deferred/not_available", "deferred until validated"),
        ("empty-space role", "independent role only", "independent role only"),
        ("CAR/spatial covariance", "not_identifiable", "not_identifiable"),
    ]
    svg = Element("svg", {"xmlns": "http://www.w3.org/2000/svg", "width": "1120", "height": "470"})
    SubElement(svg, "title").text = "D6 B1-R2 route decision matrix"
    SubElement(svg, "desc").text = "Design comparison only. Route B is not fitted and no selector or winner is chosen."
    SubElement(svg, "text", {"x": "24", "y": "28", "font-size": "18"}).text = "D6 B1-R2 Bayesian route gate (design evidence)"
    headers = [(24, "Evidence channel"), (300, "A diagnostic-only Bayesian"), (720, "B richer Bayesian design")]
    for x, label in headers:
        SubElement(svg, "text", {"x": str(x), "y": "58", "font-size": "13", "font-weight": "bold"}).text = label
    for i, (channel, a, b) in enumerate(rows):
        y = 84 + i * 42
        SubElement(svg, "line", {"x1": "20", "x2": "1100", "y1": str(y + 12), "y2": str(y + 12), "stroke": "#ddd"})
        SubElement(svg, "text", {"x": "24", "y": str(y), "font-size": "12"}).text = channel
        SubElement(svg, "text", {"x": "300", "y": str(y), "font-size": "12"}).text = a
        SubElement(svg, "text", {"x": "720", "y": str(y), "font-size": "12"}).text = b
    SubElement(svg, "text", {"x": "24", "y": "440", "font-size": "11"}).text = "No posterior predictive checks were run: R1 has no jointly fitted generative model."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tostring(svg, encoding="utf-8", xml_declaration=True))


def run() -> dict:
    """Build all B1-R2 evidence and fail closed on contract violations."""
    observations = load("observation-manifest.json")
    truth = load("truth-manifest.json")
    splits = load("fixture-split-manifest.json")
    inference = load("inference-frozen.json")
    r1_report = load("verification-report.json")
    recipes = load("deterministic-recipe-comparison.json")
    isolation = validate_isolation(observations, truth, splits, inference)
    statuses = status_audit(observations)
    decisions = route_decision()
    comparison = same_input_comparison(r1_report, recipes)
    evidence = {
        "A_diagnostic_only": {
            "geometry": "admit computed/partial",
            "trend_frame": "admit computed/partial",
            "z_clearance": "admit computed/partial",
            "contact_overlap": "admit computed/partial",
            "normalized_gap": "audit_only_scale",
            "wall_opening_barrier": "not_available_or_deferred",
            "empty_space": "independent_space_role_only",
        },
        "B_richer_design": {
            "normalized_gap": "continuous_likelihood_deferred_until_calibrated",
            "trend_frame": "direction_likelihood_deferred_until_orientation_contract",
            "z_clearance": "availability_gated",
            "wall_opening_barrier": "deferred_until_source_validation",
            "shared_node_shared_source": "required dependence design",
            "missing_invalid_partial_not_available_conflict": "explicit status propagation; no silent imputation",
        },
        "status_counts": statuses,
    }
    gate = {
        "schema": "d6-b1-r2-model-selection-gate/v1",
        "date": "2026-09-30",
        "seed": SEED,
        "input_artifacts": {name: digest(R1 / name) for name in (
            "observation-manifest.json", "truth-manifest.json", "fixture-split-manifest.json",
            "inference-frozen.json", "deterministic-recipe-comparison.json", "verification-report.json")},
        "decisions": {
            "conditional_membership_estimand": "APPROVED_FOR_DIAGNOSTIC_ONLY",
            "candidate_universe": "EXTERNAL_FROZEN_INPUT",
            "richer_hierarchical_fit": "REQUIRED_BEFORE_ANY_IMPLEMENTATION_OR_PRODUCTION_USE",
            "first_version_posterior_evidence": "A_ONLY_LISTED_CHANNELS",
            "car_spatial_covariance": "PERMANENTLY_DEFERRED_FOR_THIS DESIGN LINE; NOT_IDENTIFIABLE",
            "deterministic_recipes": "COMPARATOR_ONLY",
            "production_selector": "PROHIBITED",
        },
        "implementation_design_entry_conditions": [
            "freeze candidate universe and membership-level output states",
            "freeze status/provenance and source identity policy",
            "calibrate continuous gap and direction likelihoods on independent development fixtures",
            "predeclare shared-node/shared-source dependence model and sensitivity grid",
            "run whole-fixture holdout calibration and joint-model posterior predictive checks",
            "specify output uncertainty/state contract without a selector",
        ],
        "implementation_design_exit_conditions": [
            "any truth leakage or fixture split overlap",
            "unresolved conflict or missingness propagation",
            "non-identifiable dependence treated as fitted",
            "calibration substituted for PPC",
            "threshold, winner, production selector, or psychological validity claim introduced",
        ],
        "truth_isolation": isolation,
        "route_decisions": decisions,
        "evidence_admission_matrix": evidence,
        "same_input_comparison": comparison,
        "posterior_predictive_checks": {"status": "not_run", "reason": "No jointly fitted generative model in R1; calibration is not PPC."},
        "acceptance_boundary": "Brier and recipe scores are synthetic computational gates only; they do not represent layout accuracy, psychological validity, or production readiness.",
        "status": "STOP FOR B1 DESIGN REVIEW",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {
        "gate": OUT / "model-selection-gate.json",
        "evidence": OUT / "evidence-admission-matrix.json",
        "comparison": OUT / "same-input-deterministic-comparison.json",
        "figure": OUT / "route-decision-matrix.svg",
        "verification": OUT / "verification-report.json",
    }
    write_json(paths["gate"], gate)
    write_json(paths["evidence"], evidence)
    write_json(paths["comparison"], comparison)
    render_matrix(paths["figure"], decisions)
    fromstring(paths["figure"].read_bytes())
    verification = {
        "schema": "d6-b1-r2-verification/v1",
        "status": "verified",
        "checks": {
            "truth_isolation": True,
            "whole_fixture_holdout": isolation["holdout_fixtures"] == 16,
            "shared_observation_identity": isolation["nested_units_are_not_iid"],
            "same_observation_hash_bound": True,
            "deterministic_comparison_views": len(recipes["outputs"]),
            "no_winner_or_threshold": comparison["winner_or_threshold_selected"] is False,
            "ppc_status": "not_run",
            "svg_xml_parse": True,
        },
        "input_hashes": gate["input_artifacts"],
    }
    write_json(paths["verification"], verification)
    record_paths = [*paths.values(), Path(__file__).resolve(),
        ROOT / "docs/project/evidence/d6-b1-r2-model-selection-gate.md",
        ROOT / "docs/project/evidence/d6-b1-r2-verification-report.md"]
    manifest = OUT / "artifact-manifest.json"
    write_json(manifest, {"schema": "d6-b1-r2-artifacts/v1", "seed": SEED,
        "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                       "sha256": digest(path), "bytes": path.stat().st_size}
                      for path in record_paths if path.exists()]})
    return {"status": gate["status"], "artifact_count": len(record_paths), "holdout": 16,
            "deterministic_views": len(recipes["outputs"]), "output": str(manifest.relative_to(ROOT))}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
