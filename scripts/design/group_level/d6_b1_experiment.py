"""Generate a deterministic D6 B1 synthetic membership experiment."""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/project/evidence/d6-b1-artifacts"
SEED = 61030
N_FIXTURES = 48
CHANNELS = ("geometry", "relation", "context")
SENSITIVITY = {"clear": 0.84, "noisy": 0.62}
SPECIFICITY = {"clear": 0.86, "noisy": 0.64}
QUALITY_PRIOR = {"clear": 0.7, "noisy": 0.3}


def digest(path: Path) -> str:
    """Return a stable SHA-256 digest for an artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    """Write canonical, human-readable JSON for reproducibility."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bernoulli(rng: random.Random, probability: float) -> int:
    """Draw one binary observation from the seeded generator."""
    return int(rng.random() < probability)


def build_fixtures() -> tuple[list[dict], list[dict]]:
    """Create observed evidence and a separately serialized computational truth set."""
    rng = random.Random(SEED)
    fixtures, truths = [], []
    families = ("geometry_merge", "shared_spatial_structure", "overlapping_candidate",
                "singleton_unassigned", "ambiguous_alternatives", "status_perturbation")
    for index in range(N_FIXTURES):
        fixture_id = f"fixture-{index:03d}"
        split = "development" if index < 32 else "holdout"
        family = families[index % len(families)]
        quality = "clear" if rng.random() < QUALITY_PRIOR["clear"] else "noisy"
        groups = [f"g{n}" for n in range(5)]
        scopes, truth_scopes = [], []
        for scope_index in range(3):
            scope_id = f"scope-{scope_index}"
            # Vary computational truth by scenario, including sparse/singleton scopes.
            labels = [bernoulli(rng, (0.58, 0.34, 0.16)[scope_index]) for _ in groups]
            if family == "geometry_merge":
                labels = [int(group_id in {"g0", "g1", "g2"}) if scope_index == 0 else 0 for group_id in groups]
            elif family in {"shared_spatial_structure", "overlapping_candidate"}:
                selected = ({"g0", "g1", "g2"}, {"g1", "g2", "g3"}, {"g4"})[scope_index]
                labels = [int(group_id in selected) for group_id in groups]
            elif family == "singleton_unassigned":
                labels = [int(group_id == ("g2" if scope_index == 2 else "g0")) for group_id in groups]
            elif family == "ambiguous_alternatives":
                selected = {"g0", "g1"} if scope_index < 2 else {"g4"}
                labels = [int(group_id in selected) for group_id in groups]
            if scope_index == 2 and sum(labels) > 1:
                labels = [int(i == labels.index(1)) for i in range(len(labels))]
            members = []
            for group_id, included in zip(groups, labels):
                evidence = {}
                for channel in CHANNELS:
                    sens = SENSITIVITY[quality]
                    spec = SPECIFICITY[quality]
                    value = bernoulli(rng, sens if included else 1 - spec)
                    status = "computed"
                    if rng.random() < 0.07:
                        status, value = rng.choice(("missing", "invalid", "partial", "not_available", "conflict")), None
                    evidence[channel] = {"status": status, "value": value,
                                         "reliability": quality, "source_group": channel}
                # Detailed channels are retained as separate fields; these grouped
                # indicators are not multiplied as independent likelihoods.
                members.append({
                    "authored_group_id": group_id,
                    "evidence": evidence,
                    "normalized_boundary_gap": round(rng.random(), 6),
                    "contact_2d": bool(bernoulli(rng, 0.55 if included else 0.25)),
                    "overlap_3d": bool(bernoulli(rng, 0.35 if included else 0.08)),
                    "member_pair_provenance": [f"{group_id}|{groups[(int(group_id[1:]) + 1) % 5]}"],
                    "group_geometry": {"extent_ratio": round(rng.random(), 6)},
                    "trend_frame": {"alignment": round(rng.random(), 6), "status": "computed"},
                    "z_clearance": {"value": round(rng.random(), 6), "status": "computed"},
                    "wall_opening_barrier": {"value": bool(bernoulli(rng, 0.1)), "status": "computed"},
                    "empty_space_role_evidence": {"status": "not_available", "posterior": None},
                })
            scopes.append({"scope_id": scope_id, "members": members,
                           "scope_provenance": "predeclared_synthetic_scope"})
            truth_scopes.append({"scope_id": scope_id, "included_group_ids": [g for g, y in zip(groups, labels) if y]})
        fixtures.append({"fixture_id": fixture_id, "split": split, "family": family,
                         "fixture_reliability_latent": quality, "scopes": scopes})
        truths.append({"fixture_id": fixture_id, "scopes": truth_scopes,
                       "family": family, "truth_provenance": "seeded family-specific generative labels; evaluation-only"})
    return fixtures, truths


def posterior_for(observations: list[dict], prior_p: float = 0.4) -> list[float]:
    """Compute membership marginals under a predeclared reliability mixture."""
    out = []
    for item in observations:
        # Missing-like statuses contribute no likelihood. Three evidence families
        # are grouped to limit pseudo-replication among their detailed subfields.
        log_odds = math.log(prior_p / (1 - prior_p))
        for channel in CHANNELS:
            obs = item["evidence"][channel]
            if obs["status"] != "computed":
                continue
            # Marginalize the predeclared reliability mixture without claiming a fitted joint effect.
            l1 = sum(QUALITY_PRIOR[q] * (SENSITIVITY[q] if obs["value"] else 1 - SENSITIVITY[q]) for q in SENSITIVITY)
            l0 = sum(QUALITY_PRIOR[q] * (1 - SPECIFICITY[q] if obs["value"] else SPECIFICITY[q]) for q in SPECIFICITY)
            log_odds += math.log(l1 / l0)
        out.append(1 / (1 + math.exp(-log_odds)))
    return out


def score(fixtures: list[dict], truths: list[dict]) -> tuple[dict, list[dict]]:
    """Score holdout memberships and deterministic evidence at fixture level."""
    truth_by_id = {row["fixture_id"]: row for row in truths}
    development_labels = [int(group_id in set(scope["included_group_ids"]))
                          for fixture in fixtures if fixture["split"] == "development"
                          for scope in truth_by_id[fixture["fixture_id"]]["scopes"]
                          for group_id in (f"g{n}" for n in range(5))]
    prevalence_baseline = sum(development_labels) / len(development_labels)
    rows, fixture_metrics = [], []
    for fixture in fixtures:
        if fixture["split"] != "holdout":
            continue
        truth_scope = {row["scope_id"]: set(row["included_group_ids"])
                       for row in truth_by_id[fixture["fixture_id"]]["scopes"]}
        brier, baseline_brier, det_correct, n = [], [], [], 0
        for scope in fixture["scopes"]:
            posts = posterior_for(scope["members"])
            for item, post in zip(scope["members"], posts):
                y = int(item["authored_group_id"] in truth_scope[scope["scope_id"]])
                available = [v["value"] for v in item["evidence"].values() if v["status"] == "computed"]
                det = sum(available) / len(available) if available else 0.5
                brier.append((post - y) ** 2)
                baseline_brier.append((prevalence_baseline - y) ** 2)
                det_correct.append(int((det >= 0.5) == bool(y)))
                rows.append({"fixture_id": fixture["fixture_id"], "scope_id": scope["scope_id"],
                             "group_id": item["authored_group_id"], "truth": y,
                             "posterior": round(post, 8), "deterministic_strength": round(det, 8)})
                n += 1
        fixture_metrics.append({"fixture_id": fixture["fixture_id"], "family": fixture["family"], "membership_count": n,
                                "bayes_brier": sum(brier) / len(brier),
                                "prevalence_baseline_brier": sum(baseline_brier) / len(baseline_brier),
                                "deterministic_accuracy": sum(det_correct) / len(det_correct)})
    # Fixture is the replication unit; candidates and memberships remain nested.
    summary = {"holdout_fixture_count": len(fixture_metrics),
               "mean_fixture_brier": sum(x["bayes_brier"] for x in fixture_metrics) / len(fixture_metrics),
               "development_prevalence_baseline": prevalence_baseline,
               "mean_fixture_prevalence_baseline_brier": sum(x["prevalence_baseline_brier"] for x in fixture_metrics) / len(fixture_metrics),
               "mean_fixture_deterministic_accuracy": sum(x["deterministic_accuracy"] for x in fixture_metrics) / len(fixture_metrics),
               "fixture_metrics": fixture_metrics,
               "family_metrics": {family: {
                   "fixture_count": sum(row["family"] == family for row in fixture_metrics),
                   "mean_fixture_brier": sum(row["bayes_brier"] for row in fixture_metrics if row["family"] == family)
                                         / sum(row["family"] == family for row in fixture_metrics),
                   "mean_fixture_baseline_brier": sum(row["prevalence_baseline_brier"] for row in fixture_metrics if row["family"] == family)
                                                  / sum(row["family"] == family for row in fixture_metrics),
               } for family in sorted({row["family"] for row in fixture_metrics})},
               "calibration_bins": calibration_bins(rows),
               "truth_used_for_scoring_only": True}
    return summary, rows


def calibration_bins(rows: list[dict]) -> list[dict]:
    """Summarize calibration with equal-width bins and explicit membership nesting."""
    bins = []
    for index in range(5):
        selected = [r for r in rows if index / 5 <= r["posterior"] < (index + 1) / 5 or (index == 4 and r["posterior"] == 1)]
        bins.append({"lower": index / 5, "upper": (index + 1) / 5,
                     "count_nested": len(selected),
                     "mean_posterior": sum(r["posterior"] for r in selected) / len(selected) if selected else None,
                     "observed_fraction": sum(r["truth"] for r in selected) / len(selected) if selected else None})
    return bins


def svg_plot(summary: dict, path: Path) -> None:
    """Write a simple accessible calibration SVG with labels and data table values."""
    root = Element("svg", {"xmlns": "http://www.w3.org/2000/svg", "width": "720", "height": "440", "viewBox": "0 0 720 440"})
    SubElement(root, "title").text = "Synthetic holdout calibration by posterior bin"
    SubElement(root, "desc").text = "Observed computational truth fraction versus mean Bayesian membership posterior; points aggregate nested memberships and are not independent replicates."
    for x1, y1, x2, y2 in ((80, 350, 650, 350), (80, 60, 80, 350)):
        SubElement(root, "line", {"x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2), "stroke": "#222", "stroke-width": "2"})
    SubElement(root, "text", {"x": "250", "y": "410", "font-size": "16"}).text = "Mean posterior membership"
    SubElement(root, "text", {"x": "15", "y": "45", "font-size": "16"}).text = "Observed truth fraction"
    SubElement(root, "line", {"x1": "80", "y1": "350", "x2": "650", "y2": "60", "stroke": "#777", "stroke-dasharray": "7 5"})
    for row in summary["calibration_bins"]:
        if row["mean_posterior"] is None:
            continue
        x = 80 + 570 * row["mean_posterior"]
        y = 350 - 290 * row["observed_fraction"]
        SubElement(root, "circle", {"cx": str(x), "cy": str(y), "r": "7", "fill": "#0072B2"})
        SubElement(root, "text", {"x": str(x + 9), "y": str(y - 8), "font-size": "12"}).text = f"n={row['count_nested']}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tostring(root, encoding="utf-8", xml_declaration=True))


def self_check(fixtures: list[dict], truths: list[dict]) -> None:
    """Assert fixed-seed reproducibility, split isolation, and explicit status handling."""
    replay_fixtures, replay_truths = build_fixtures()
    assert fixtures == replay_fixtures and truths == replay_truths
    dev_ids = {row["fixture_id"] for row in fixtures if row["split"] == "development"}
    holdout_ids = {row["fixture_id"] for row in fixtures if row["split"] == "holdout"}
    assert len(dev_ids) == 32 and len(holdout_ids) == 16 and dev_ids.isdisjoint(holdout_ids)
    assert {row["status"] for f in fixtures for s in f["scopes"] for m in s["members"]
            for row in m["evidence"].values()} <= {"computed", "missing", "invalid", "partial", "not_available", "conflict"}
    assert all(0 <= p <= 1 for f in fixtures for s in f["scopes"] for p in posterior_for(s["members"]))


def main() -> None:
    """Generate fixtures, isolated truth, report, figure, and hashed manifest."""
    fixtures, truths = build_fixtures()
    self_check(fixtures, truths)
    OUT.mkdir(parents=True, exist_ok=True)
    fixture_path, truth_path = OUT / "fixture-manifest.json", OUT / "truth-manifest.json"
    write_json(fixture_path, {"seed": SEED, "fixture_count": N_FIXTURES, "fixtures": fixtures})
    write_json(truth_path, {"seed": SEED, "truth_access": "scoring_only", "fixtures": truths})
    report, rows = score(fixtures, truths)
    report.update({"design": "development 32 / whole-fixture holdout 16", "seed": SEED,
                   "holdout_family_counts": {name: sum(f["split"] == "holdout" and f["family"] == name for f in fixtures)
                                             for name in sorted({f["family"] for f in fixtures})},
                   "model_status": "synthetic prototype; per-membership marginal reliability mixture; joint spatial dependence not fitted",
                   "deterministic_comparator": "simple mean of available grouped binary channels; not a D1 recipe reproduction",
                   "posterior_predictive_checks": "not_run; prototype lacks joint fitted model",
                   "membership_rows_are_iid": False, "psychological_validity_claim": False})
    report_path, score_path = OUT / "holdout-report.json", OUT / "holdout-scores.json"
    write_json(report_path, report)
    write_json(score_path, {"rows": rows, "nested_under_fixture": True})
    figure_path = OUT / "holdout-calibration.svg"
    svg_plot(report, figure_path)
    files = [fixture_path, truth_path, report_path, score_path, figure_path, Path(__file__).resolve(),
             ROOT / "docs/project/evidence/d6-b1-bayesian-design-record.md",
             ROOT / "docs/project/evidence/d6-b1-calibration-holdout-report.md"]
    write_json(OUT / "artifact-manifest.json", {"seed": SEED, "artifacts": [
        {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": digest(p), "bytes": p.stat().st_size}
        for p in files]})
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "holdout_fixtures": report["holdout_fixture_count"],
                      "mean_fixture_brier": report["mean_fixture_brier"], "artifacts": len(files)}, indent=2))


if __name__ == "__main__":
    main()
