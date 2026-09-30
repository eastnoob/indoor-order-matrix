"""Run a reproducible D6 B1-R1 synthetic Bayesian design experiment."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/project/evidence/d6-b1-r1-artifacts"
SEED = 61031
GROUPS = [f"g{i}" for i in range(5)]
STATUSES = ("computed", "missing", "invalid", "partial", "not_available", "conflict")
FAMILIES = ("geometry_merge", "shared_spatial_structure", "overlapping_candidate",
            "singleton_unassigned", "ambiguous_alternatives", "status_perturbation")
PRIORS = {"sparse": 0.20, "central": 0.40, "diffuse": 0.70}
DEPENDENCE = ("independent", "shared_node_source_discount")
CHANNELS = {"geometry": (0.82, 0.78), "trend": (0.76, 0.72),
            "clearance": (0.72, 0.70), "pair_support": (0.84, 0.82)}


def canonical(value: object) -> str:
    """Serialize records consistently for identity signatures."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of bytes."""
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    """Return the SHA-256 digest of an artifact."""
    return digest_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    """Write stable formatted JSON and create the output directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_compact_json(path: Path, value: object) -> None:
    """Write large nested artifacts compactly while preserving exact JSON data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def coin(rng: random.Random, p: float) -> bool:
    """Draw a deterministic binary observation from a local generator."""
    return rng.random() < p


def build_truth(index: int, rng: random.Random) -> tuple[str, dict[str, set[str]]]:
    """Generate synthetic computational truth separately from serialized observations."""
    family = FAMILIES[index % len(FAMILIES)]
    scopes = {}
    for k in range(3):
        scope = f"scope-{k}"
        if family == "geometry_merge":
            members = {"g0", "g1", "g2"} if k == 0 else set()
        elif family in {"shared_spatial_structure", "overlapping_candidate"}:
            members = ({"g0", "g1", "g2"}, {"g1", "g2", "g3"}, {"g4"})[k]
        elif family == "singleton_unassigned":
            members = {"g2" if k == 2 else "g0"}
        elif family == "ambiguous_alternatives":
            members = {"g0", "g1"} if k < 2 else {"g4"}
        else:
            members = {group for group in GROUPS if coin(rng, (0.58, 0.34, 0.16)[k])}
            if k == 2 and len(members) > 1:
                members = {sorted(members)[0]}
        scopes[scope] = members
    return family, scopes


def scheduled_status(fixture_index: int, row_index: int, channel_index: int) -> str:
    """Assign evidence status independently of truth and observed value."""
    return STATUSES[(fixture_index + row_index + channel_index) % len(STATUSES)]


def make_evidence(status: str, value: object, sources: list[str], reason: str) -> dict:
    """Encode each status without zero-filling or silently selecting conflict values."""
    record = {"status": status, "reason": reason, "source_records": sorted(sources)}
    if status == "computed":
        record["value"] = value
    elif status == "partial":
        record["components"] = {"observed_component": value, "unobserved_components": ["secondary_component"]}
    elif status == "invalid":
        record["invalid_payload"] = "malformed-or-non-finite-source"
    elif status == "conflict":
        record["alternatives"] = [{"source_id": sources[0], "value": value},
                                  {"source_id": sources[1], "value": not value if isinstance(value, bool) else value + 0.17}]
    return record


def usable_values(record: dict) -> tuple[list[bool], dict]:
    """Return evidence admitted by status policy and a trace for every status."""
    status = record["status"]
    trace = {"status": status, "reason": record["reason"], "source_records": record["source_records"],
             "likelihood_used": False, "used_components": []}
    if status == "computed":
        trace.update(likelihood_used=True, used_components=["value"])
        return [bool(record["value"])], trace
    if status == "partial" and record["components"].get("observed_component") is not None:
        trace.update(likelihood_used=True, used_components=["observed_component"])
        return [bool(record["components"]["observed_component"])], trace
    # missing, invalid, not_available, and conflict remain categorical and add no likelihood.
    return [], trace


def audit_only(record: dict, observation_id: str, role: str) -> dict:
    """Preserve a non-membership status and provenance in the inference trace."""
    audit = {"observation_id": observation_id, "channel_role": role, "status": record["status"],
             "reason": record.get("reason", "independent role evidence"),
             "source_records": record.get("source_records", []), "likelihood_used": False, "used_components": []}
    for field in ("alternatives", "invalid_payload", "components"):
        if field in record:
            audit[field] = record[field]
    return audit


def status_value(record: dict) -> object:
    """Read a computed scalar from either group/pair evidence or a role record."""
    return record.get("value")


def generate() -> tuple[dict, dict, dict]:
    """Generate scene-level observations, separate truth, and split/family metadata."""
    rng = random.Random(SEED)
    observations, truths, split_rows = [], [], []
    for fi in range(48):
        fixture_id = f"r1-fixture-{fi:03d}"
        split = "development" if fi < 32 else "holdout"
        family, truth = build_truth(fi, rng)
        active = set().union(*truth.values())
        quality = "clear" if rng.random() < 0.7 else "noisy"
        groups = []
        for gi, group_id in enumerate(GROUPS):
            src = f"{fixture_id}:group:{group_id}"
            channels = {}
            for ci, channel in enumerate(("geometry", "trend", "clearance")):
                status = scheduled_status(fi, gi, ci)
                sens, spec = CHANNELS[channel]
                if quality == "noisy":
                    sens, spec = 0.5 + (sens - 0.5) * 0.65, 0.5 + (spec - 0.5) * 0.65
                value = coin(rng, sens if group_id in active else 1 - spec)
                channels[channel] = make_evidence(status, value,
                    [f"{src}:{channel}:a", f"{src}:{channel}:b"], f"scheduled_{status}_{channel}")
            groups.append({"group_id": group_id,
                "source_provenance": {"authored_source": src, "shared_scene_source_group": f"{fixture_id}:scene"},
                "scene_observations": channels,
                "group_geometry_summary": {"extent_ratio": round(rng.random(), 6), "frame_id": f"{fixture_id}:analysis"},
                "trend_frame": {"axis_alignment": round(rng.random(), 6), "status": channels["trend"]["status"],
                                "source_id": f"{src}:world-frame"},
                "z_clearance": {"summary": round(rng.random(), 6), "status": channels["clearance"]["status"],
                                "source_id": f"{src}:vertical"} })
        signatures = {row["group_id"]: digest_bytes(canonical(row).encode()) for row in groups}
        pairs = list(itertools.combinations(GROUPS, 2))
        pair_truth = {pair: any(set(pair) <= members for members in truth.values()) for pair in pairs}
        raw_gap = {pair: (0.16 if pair_truth[pair] else 0.78) + rng.uniform(-0.08, 0.08) for pair in pairs}
        lo, hi = min(raw_gap.values()), max(raw_gap.values())
        relations = []
        for ri, pair in enumerate(pairs):
            pair_id = "|".join(sorted(pair))
            sources = sorted([f"{fixture_id}:pair:{pair_id}:geom-a", f"{fixture_id}:pair:{pair_id}:geom-b"])
            status = scheduled_status(fi, ri, 3)
            gap = (raw_gap[pair] - lo) / (hi - lo) if hi > lo else 0.5
            support = coin(rng, 0.84 if pair_truth[pair] else 0.18)
            support_status = scheduled_status(fi, ri, 4)
            space_status = scheduled_status(fi, ri, 5)
            relations.append({"pair_id": pair_id, "group_ids": list(sorted(pair)), "status": status,
                "gap_evidence": make_evidence(status, gap, sources, f"scheduled_{status}_gap"),
                "pair_support_evidence": make_evidence(support_status, support, sources, f"scheduled_{support_status}_contact"),
                "space_role_record": make_evidence(space_status, round(rng.random(), 6), sources,
                    f"scheduled_{space_status}_space_role"),
                "provenance": {"canonical_pair_key": pair_id, "source_ids": sources,
                    "source_group": f"{fixture_id}:pair-geometry-source"}})
        scopes = []
        all_pair_ids = ["|".join(pair) for pair in pairs]
        for k in range(3):
            scopes.append({"scope_id": f"scope-{k}", "group_ids": list(GROUPS),
                "scope_provenance": f"{fixture_id}:predeclared-scope:{k}",
                "shared_group_observation_refs": dict(signatures),
                "candidate_specific_evidence": {"kind": "scope projection of shared pair observations",
                    "pair_relation_refs": all_pair_ids, "records_duplicated": False}})
        observations.append({"fixture_id": fixture_id, "groups": groups,
            "pair_relations": relations, "candidate_scopes": scopes})
        truths.append({"fixture_id": fixture_id,
            "scopes": [{"scope_id": key, "included_group_ids": sorted(value)} for key, value in sorted(truth.items())],
            "truth_provenance": "seeded synthetic computational truth; scoring only"})
        split_rows.append({"fixture_id": fixture_id, "split": split, "family": family})
    return ({"schema": "d6-b1-r1-observations/v1", "seed": SEED, "fixtures": observations},
            {"schema": "d6-b1-r1-truth/v1", "seed": SEED, "fixtures": truths},
            {"schema": "d6-b1-r1-splits/v1", "seed": SEED, "fixtures": split_rows})


def log_lr(value: bool, channel: str) -> float:
    """Calculate the fixed synthetic binary-channel log likelihood ratio."""
    sens, spec = CHANNELS[channel]
    return math.log(sens / (1 - spec)) if value else math.log((1 - sens) / spec)


def infer(observation_fixture: dict, prior_name: str, dependence: str) -> dict:
    """Infer candidate membership from the observation schema only."""
    p = PRIORS[prior_name]
    group_map = {row["group_id"]: row for row in observation_fixture["groups"]}
    pair_map = {row["pair_id"]: row for row in observation_fixture["pair_relations"]}
    outputs = []
    for scope in observation_fixture["candidate_scopes"]:
        members = []
        for group_id in scope["group_ids"]:
            evidence_by_source, relation_by_source, trace = defaultdict(list), defaultdict(list), []
            group = group_map[group_id]
            for channel in ("geometry", "trend", "clearance"):
                values, audit = usable_values(group["scene_observations"][channel])
                audit["observation_id"] = f"{group_id}:{channel}"
                audit["channel_role"] = "membership_evidence"
                trace.append(audit)
                source = group["source_provenance"]["shared_scene_source_group"] if channel != "clearance" else f"{group_id}:vertical"
                evidence_by_source[source].extend(log_lr(value, channel) for value in values)
            for other in scope["group_ids"]:
                if other == group_id:
                    continue
                relation = pair_map["|".join(sorted((group_id, other)))]
                values, audit = usable_values(relation["pair_support_evidence"])
                audit["observation_id"] = f"pair:{relation['pair_id']}:support"
                audit["channel_role"] = "membership_evidence"
                trace.append(audit)
                relation_by_source[relation["provenance"]["source_group"]].extend(log_lr(value, "pair_support") for value in values)
                trace.append(audit_only(relation["gap_evidence"], f"pair:{relation['pair_id']}:gap", "scale_only"))
                trace.append(audit_only(relation["space_role_record"], f"pair:{relation['pair_id']}:space-role", "independent_space_role"))
            if dependence == "independent":
                llr = sum(map(sum, evidence_by_source.values())) + sum(map(sum, relation_by_source.values()))
            else:
                # Dependence sensitivity discounts multiple measures from shared sources to one source-block mean.
                llr = sum(sum(values) / len(values) for values in evidence_by_source.values() if values)
                llr += sum(sum(values) / len(values) for values in relation_by_source.values() if values)
            odds = math.log(p / (1 - p)) + llr
            members.append({"group_id": group_id, "posterior": 1 / (1 + math.exp(-odds)),
                            "prior_probability": p, "status_trace": trace})
        outputs.append({"scope_id": scope["scope_id"], "members": members, "overlap_allowed": True})
    return {"fixture_id": observation_fixture["fixture_id"], "prior_name": prior_name,
            "dependence": dependence, "scopes": outputs, "truth_consumed": False}


def quantile(values: list[float], q: float) -> float | None:
    """Use the H2 inclusive-linear quantile formula for relative scale recipes."""
    if not values:
        return None
    values = sorted(values)
    position = q * (len(values) - 1)
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] + (values[high] - values[low]) * (position - low)


def run_recipes(observation_fixture: dict) -> list[dict]:
    """Execute the existing H2 relative-gap, local-persistence, and space-profile semantics."""
    relations = {row["pair_id"]: row for row in observation_fixture["pair_relations"]}
    gap = {key: row["gap_evidence"]["value"] for key, row in relations.items()
           if row["status"] == "computed" and row["gap_evidence"]["status"] == "computed"}
    ranks = {group: [] for group in GROUPS}
    for pair_id, value in gap.items():
        left, right = relations[pair_id]["group_ids"]
        ranks[left].append((value, right))
        ranks[right].append((value, left))
    rank_map = {group: {other: rank for rank, (_, other) in enumerate(sorted(items), 1)}
                for group, items in ranks.items()}
    result = []
    for scope in observation_fixture["candidate_scopes"]:
        internal = set(scope["candidate_specific_evidence"]["pair_relation_refs"])
        for q in (0.25, 0.5, 0.75):
            bound = quantile(list(gap.values()), q)
            selected = sorted(pair for pair in internal & gap.keys() if bound is not None and gap[pair] <= bound)
            result.append(recipe_summary(scope, relations, "relative_gap_rank", {"quantile": q, "bound": bound}, selected, True))
        for window in (1, 2, 3):
            for persistence in (1, 2):
                selected = []
                for pair_id in sorted(internal & gap.keys()):
                    left, right = relations[pair_id]["group_ids"]
                    rank = max(rank_map[left].get(right, 10**6), rank_map[right].get(left, 10**6))
                    persistent = sum(rank <= candidate_window for candidate_window in (1, 2, 3))
                    if rank <= window and persistent >= persistence:
                        selected.append(pair_id)
                result.append(recipe_summary(scope, relations, "local_persistence_window",
                    {"window": window, "persistence": persistence}, selected, True))
        profiles = [status_value(relations[pair]["space_role_record"]) for pair in internal
                    if relations[pair]["space_role_record"]["status"] == "computed"]
        for q in (0.5, 0.75):
            bound = quantile(profiles, q)
            selected = sorted(pair for pair in internal if relations[pair]["space_role_record"]["status"] == "computed"
                and bound is not None and status_value(relations[pair]["space_role_record"]) is not None
                and status_value(relations[pair]["space_role_record"]) >= bound)
            result.append(recipe_summary(scope, relations, "space_profile_rank", {"quantile": q, "bound": bound}, selected, False))
    return result


def recipe_summary(scope: dict, relations: dict, recipe: str, params: dict,
                   selected: list[str], compare_truth: bool) -> dict:
    """Summarize deterministic recipe outputs at fixture/scope level."""
    degree = Counter(group for pair in selected for group in relations[pair]["group_ids"])
    statuses = Counter(relations[pair]["status"] for pair in scope["candidate_specific_evidence"]["pair_relation_refs"])
    return {"scope_id": scope["scope_id"], "recipe_id": recipe, "parameters": params,
        "selected_relation_ids": selected, "selected_pair_count_nested": len(selected),
        "overlapping_group_ids": sorted(group for group, count in degree.items() if count > 1),
        "status_counts": dict(statuses), "truth_comparison_permitted": compare_truth,
        "space_role_refs": [relations[pair]["space_role_record"] for pair in selected] if recipe == "space_profile_rank" else [],
        "diagnostic_only": True}


def pair_truth(truth_fixture: dict) -> set[str]:
    """Derive pair truth only after predictions are frozen."""
    scopes = [set(row["included_group_ids"]) for row in truth_fixture["scopes"]]
    return {"|".join(pair) for pair in itertools.combinations(GROUPS, 2) if any(set(pair) <= members for members in scopes)}


def bootstrap(values: list[float], seed: int, rounds: int = 1000) -> dict:
    """Bootstrap whole-fixture values, never nested memberships or pairs."""
    rng = random.Random(seed)
    samples = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(rounds))
    return {"unit": "fixture", "n_fixtures": len(values), "lower_95": samples[int(rounds * .025)],
            "upper_95": samples[int(rounds * .975)]}


def score(frozen_inference: list[dict], truth_data: dict, splits: dict, recipes: list[dict]) -> dict:
    """Score frozen outputs against separately supplied truth at whole-fixture level."""
    truth_map = {row["fixture_id"]: row for row in truth_data["fixtures"]}
    split_map = {row["fixture_id"]: row for row in splits["fixtures"]}
    dev = [key for key, row in split_map.items() if row["split"] == "development"]
    hold = [key for key, row in split_map.items() if row["split"] == "holdout"]
    prevalence = sum(len(scope["included_group_ids"]) for key in dev for scope in truth_map[key]["scopes"]) / (len(dev) * 15)
    configs = {}
    for prior in PRIORS:
        for dependence in DEPENDENCE:
            key = f"{prior}:{dependence}"
            post_by_id = {row["fixture_id"]: row for row in frozen_inference if row["prior_name"] == prior and row["dependence"] == dependence}
            metrics = []
            for fixture_id in hold:
                actual = {(scope["scope_id"], group) for scope in truth_map[fixture_id]["scopes"] for group in scope["included_group_ids"]}
                probs = {(scope["scope_id"], member["group_id"]): member["posterior"]
                         for scope in post_by_id[fixture_id]["scopes"] for member in scope["members"]}
                losses = [(p - int(item in actual)) ** 2 for item, p in probs.items()]
                base = [(prevalence - int(item in actual)) ** 2 for item in probs]
                metrics.append({"fixture_id": fixture_id, "family": split_map[fixture_id]["family"],
                    "brier": sum(losses) / len(losses), "baseline_brier": sum(base) / len(base),
                    "prior_posterior_shift": sum(abs(p - PRIORS[prior]) for p in probs.values()) / len(probs),
                    "membership_count_nested": len(probs)})
            configs[key] = {"prior": prior, "prior_probability": PRIORS[prior],
                "expected_candidate_size": 5 * PRIORS[prior], "dependence": dependence,
                "mean_fixture_brier": mean(row["brier"] for row in metrics),
                "mean_fixture_prevalence_baseline_brier": mean(row["baseline_brier"] for row in metrics),
                "mean_fixture_prior_posterior_shift": mean(row["prior_posterior_shift"] for row in metrics),
                "brier_cluster_bootstrap_95": bootstrap([row["brier"] for row in metrics], SEED + len(configs)),
                "fixture_metrics": metrics}
    by_recipe = defaultdict(list)
    for row in recipes:
        by_recipe[row["recipe_id"]].append(row)
    recipe_report = {}
    for recipe, rows in by_recipe.items():
        reports = []
        for fixture_id in hold:
            fixture_rows = [row for row in rows if row["fixture_id"] == fixture_id]
            allowed = [row for row in fixture_rows if row["truth_comparison_permitted"]]
            if not allowed:
                reports.append({"fixture_id": fixture_id, "truth_comparison": "prohibited for independent space-role evidence",
                    "mean_selected_role_pairs": mean(row["selected_pair_count_nested"] for row in fixture_rows)})
                continue
            truth_pairs = pair_truth(truth_map[fixture_id])
            f1s = []
            for row in allowed:
                pred = set(row["selected_relation_ids"])
                tp = len(pred & truth_pairs)
                precision = tp / len(pred) if pred else 0
                recall = tp / len(truth_pairs) if truth_pairs else 0
                f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
            reports.append({"fixture_id": fixture_id, "family": split_map[fixture_id]["family"],
                "mean_within_fixture_pair_f1": mean(f1s), "selected_pair_count_nested": mean(row["selected_pair_count_nested"] for row in allowed),
                "overlap_views": sum(bool(row["overlapping_group_ids"]) for row in allowed)})
        recipe_report[recipe] = {"fixture_metrics": reports, "truth_comparison_permitted": recipe != "space_profile_rank",
            "mean_fixture_pair_f1": mean(row["mean_within_fixture_pair_f1"] for row in reports)
                if recipe != "space_profile_rank" else None}
    return {"seed": SEED, "development_fixture_count": len(dev), "holdout_fixture_count": len(hold),
        "development_prevalence_only_baseline": prevalence, "prior_sensitivity": configs,
        "deterministic_recipe_comparison": recipe_report,
        "spatial_car": {"status": "not_identifiable", "reason": "five-node graph and no replicated graph realizations"},
        "posterior_predictive_checks": {"status": "not_run", "reason": "No jointly fitted generative model; calibration is not PPC."},
        "truth_joined_after_frozen_inference": True,
        "scope": "synthetic computational gate only; no real-layout or psychological validity claim"}


def mean(values) -> float:
    """Compute an arithmetic mean for a non-empty, prevalidated sequence."""
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def calibration_rows(frozen: list[dict], truths: dict, splits: dict) -> list[dict]:
    """Produce equal-fixture-weighted calibration cells, with nested counts labeled."""
    truth_map = {row["fixture_id"]: row for row in truths["fixtures"]}
    hold = {row["fixture_id"] for row in splits["fixtures"] if row["split"] == "holdout"}
    rows = []
    for posterior in frozen:
        if posterior["fixture_id"] not in hold:
            continue
        actual = {(scope["scope_id"], group) for scope in truth_map[posterior["fixture_id"]]["scopes"] for group in scope["included_group_ids"]}
        for b in range(5):
            cells = [(member["posterior"], int((scope["scope_id"], member["group_id"]) in actual))
                for scope in posterior["scopes"] for member in scope["members"]
                if b / 5 <= member["posterior"] < (b + 1) / 5 or b == 4 and member["posterior"] == 1]
            if cells:
                rows.append({"fixture_id": posterior["fixture_id"], "prior": posterior["prior_name"],
                    "dependence": posterior["dependence"], "bin": b,
                    "mean_posterior": mean(p for p, _ in cells), "truth_fraction": mean(y for _, y in cells),
                    "nested_membership_count": len(cells)})
    return rows


def render_calibration(rows: list[dict], path: Path) -> None:
    """Render all six calibration scenarios with fixture counts and a truthful caption."""
    svg = Element("svg", {"xmlns": "http://www.w3.org/2000/svg", "width": "980", "height": "590", "viewBox": "0 0 980 590"})
    SubElement(svg, "title").text = "R1 synthetic holdout calibration; each fixture contributes equally"
    SubElement(svg, "desc").text = "Calibration is against synthetic computational truth only. Counts beside points are fixtures with observations in each bin; memberships are nested. All prior and dependence scenarios are displayed."
    SubElement(svg, "text", {"x": "170", "y": "28", "font-size": "18"}).text = "Seed 61031 — synthetic truth; fixture-weighted calibration (PPC not run)"
    x0, y0, w, h = 90, 470, 780, 380
    SubElement(svg, "line", {"x1": str(x0), "y1": str(y0), "x2": str(x0+w), "y2": str(y0), "stroke": "#222"})
    SubElement(svg, "line", {"x1": str(x0), "y1": str(y0), "x2": str(x0), "y2": str(y0-h), "stroke": "#222"})
    SubElement(svg, "line", {"x1": str(x0), "y1": str(y0), "x2": str(x0+w), "y2": str(y0-h), "stroke": "#777", "stroke-dasharray": "7 5"})
    SubElement(svg, "text", {"x": "330", "y": "525", "font-size": "14"}).text = "Mean posterior probability"
    SubElement(svg, "text", {"x": "8", "y": "65", "font-size": "14"}).text = "Observed truth fraction"
    colors = {"sparse": "#0072B2", "central": "#009E73", "diffuse": "#D55E00"}
    for prior, dependence in itertools.product(PRIORS, DEPENDENCE):
        for b in range(5):
            selected = [row for row in rows if row["prior"] == prior and row["dependence"] == dependence and row["bin"] == b]
            if not selected:
                continue
            px, py = mean(row["mean_posterior"] for row in selected), mean(row["truth_fraction"] for row in selected)
            x, y = x0 + w*px, y0 - h*py
            if dependence == DEPENDENCE[0]:
                SubElement(svg, "circle", {"cx": str(x), "cy": str(y), "r": "6", "fill": colors[prior]})
            else:
                SubElement(svg, "rect", {"x": str(x-5), "y": str(y-5), "width": "10", "height": "10", "fill": colors[prior]})
            SubElement(svg, "text", {"x": str(x+7), "y": str(y-6), "font-size": "10"}).text = f"n={len({row['fixture_id'] for row in selected})}f"
    legend = ["Colors: sparse / central / diffuse prior", "Circle: independent; square: shared-source discount",
              "Point positions average contributing fixture-bin summaries equally; no pooled-iid uncertainty"]
    for i, line in enumerate(legend):
        SubElement(svg, "text", {"x": "90", "y": str(555 + i*14), "font-size": "11"}).text = line
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tostring(svg, encoding="utf-8", xml_declaration=True))


def status_counts(observations: dict, frozen: list[dict]) -> dict:
    """Summarize input and propagated statuses without treating records as samples."""
    inputs = Counter()
    outputs = Counter()
    for fixture in observations["fixtures"]:
        for group in fixture["groups"]:
            inputs.update(f"group:{record['status']}" for record in group["scene_observations"].values())
        for pair in fixture["pair_relations"]:
            inputs[f"gap:{pair['gap_evidence']['status']}"] += 1
            inputs[f"pair_support:{pair['pair_support_evidence']['status']}"] += 1
            inputs[f"space_role:{pair['space_role_record']['status']}"] += 1
    for fixture in frozen:
        for scope in fixture["scopes"]:
            for member in scope["members"]:
                outputs.update(f"{trace['channel_role']}:{trace['status']}:"
                               f"{'used' if trace['likelihood_used'] else 'unused'}"
                               for trace in member["status_trace"])
    return {"input_status_counts": dict(sorted(inputs.items())),
            "output_status_trace_counts": dict(sorted(outputs.items()))}


def assert_contract(observations: dict, truth: dict, splits: dict, inferred: list[dict]) -> None:
    """Check shared immutable records, split isolation, and all status transitions."""
    obs_ids = {row["fixture_id"] for row in observations["fixtures"]}
    truth_ids = {row["fixture_id"] for row in truth["fixtures"]}
    split_map = {row["fixture_id"]: row["split"] for row in splits["fixtures"]}
    dev, hold = {key for key, value in split_map.items() if value == "development"}, {key for key, value in split_map.items() if value == "holdout"}
    assert obs_ids == truth_ids == set(split_map) and len(dev) == 32 and len(hold) == 16 and not dev & hold
    input_statuses, output_statuses = set(), set()
    for fixture in observations["fixtures"]:
        groups = {row["group_id"]: row for row in fixture["groups"]}
        pairs = {row["pair_id"]: row for row in fixture["pair_relations"]}
        assert len(pairs) == 10 and all(key == "|".join(row["group_ids"]) and row["provenance"]["source_ids"] == sorted(row["provenance"]["source_ids"]) for key, row in pairs.items())
        first_refs = fixture["candidate_scopes"][0]["shared_group_observation_refs"]
        for scope in fixture["candidate_scopes"]:
            assert scope["shared_group_observation_refs"] == first_refs
            for group, signature in first_refs.items():
                assert signature == digest_bytes(canonical(groups[group]).encode())
            for pair_id in scope["candidate_specific_evidence"]["pair_relation_refs"]:
                assert pair_id in pairs
        for group in groups.values():
            for record in group["scene_observations"].values():
                input_statuses.add(record["status"])
                if record["status"] == "invalid":
                    assert "value" not in record
                if record["status"] == "partial":
                    assert record["components"]["observed_component"] is not None
                if record["status"] == "conflict":
                    assert len(record["alternatives"]) == 2 and "value" not in record
    for fixture in inferred:
        assert fixture["truth_consumed"] is False
        for scope in fixture["scopes"]:
            for member in scope["members"]:
                assert 0 <= member["posterior"] <= 1
                for trace in member["status_trace"]:
                    output_statuses.add(trace["status"])
                    if trace["status"] in {"missing", "invalid", "not_available", "conflict"}:
                        assert not trace["likelihood_used"]
                    if trace["status"] == "partial" and trace.get("channel_role") == "membership_evidence":
                        assert trace["likelihood_used"] and trace["used_components"] == ["observed_component"]
    assert set(STATUSES) <= input_statuses and set(STATUSES) <= output_statuses


def run() -> dict:
    """Generate separate artifacts, freeze inference before scoring, and write manifests."""
    observations, truth, splits = generate()
    inferred = [infer(fixture, prior, dependence) for fixture in observations["fixtures"]
                for prior in PRIORS for dependence in DEPENDENCE]
    assert_contract(observations, truth, splits, inferred)
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {name: OUT / filename for name, filename in {
        "observations": "observation-manifest.json", "truth": "truth-manifest.json",
        "splits": "fixture-split-manifest.json", "inference": "inference-frozen.json",
        "recipes": "deterministic-recipe-comparison.json", "calibration": "calibration-bin-fixture-rows.json",
        "figure": "calibration.svg", "report": "verification-report.json"}.items()}
    write_json(paths["observations"], observations)
    write_json(paths["truth"], truth)
    write_json(paths["splits"], splits)
    recipes = [{"fixture_id": fixture["fixture_id"], **row} for fixture in observations["fixtures"] for row in run_recipes(fixture)]
    write_compact_json(paths["recipes"], {"outputs": recipes, "space_role_not_membership_truth": True})
    write_compact_json(paths["inference"], {"inference": inferred, "truth_consumed": False,
        "input_sha256": digest_file(paths["observations"])})
    frozen = json.loads(paths["inference"].read_text(encoding="utf-8"))["inference"]
    report = score(frozen, truth, splits, recipes)
    calibration = calibration_rows(frozen, truth, splits)
    write_json(paths["calibration"], {"aggregation_unit": "fixture", "rows": calibration,
        "nested_membership_count_is_not_n": True})
    render_calibration(calibration, paths["figure"])
    report.update({"schema": "d6-b1-r1-report/v1", "status_input_mechanism": "deterministic scheduled independently of truth and values",
        "status_contract": "computed used; partial uses observed components; missing/invalid/not_available/conflict contribute no likelihood; invalid/conflict payload/provenance retained",
        "family_holdout_counts": dict(Counter(row["family"] for row in splits["fixtures"] if row["split"] == "holdout")),
        "sample_limit": "48 fixtures total; 16 holdout; family strata contain 2-3 holdout fixtures",
        "posterior_predictive_checks": {"status": "not_run", "reason": "Calibration is not PPC; no jointly fitted generative posterior exists."},
        **status_counts(observations, frozen)})
    write_json(paths["report"], report)
    record_paths = [*paths.values(), Path(__file__).resolve(),
        ROOT / "docs/project/evidence/d6-b1-r1-design-repair-record.md",
        ROOT / "docs/project/evidence/d6-b1-r1-verification-report.md"]
    manifest = OUT / "artifact-manifest.json"
    write_json(manifest, {"schema": "d6-b1-r1-artifacts/v1", "seed": SEED, "artifacts": [
        {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": digest_file(path), "bytes": path.stat().st_size}
        for path in record_paths]})
    return {"report": str(paths["report"].relative_to(ROOT)), "fixtures": 48,
        "holdout": report["holdout_fixture_count"], "posterior_configs": len(report["prior_sensitivity"]),
        "deterministic_views": len(recipes), "manifest_items": len(record_paths)}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
