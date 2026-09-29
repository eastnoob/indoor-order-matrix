"""Run isolated D6 H2 candidate probing and evaluation-side holdout scoring."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import run_inferred_group_candidate_field_probe as probe


ROOT = Path(__file__).resolve().parents[3]
BASE = Path("scripts/design/group_level")
EVIDENCE = Path("docs/project/evidence")
FIXTURES = BASE / "inferred_group_candidate_field_h1b_holdout_fixtures.json"
TRUTH = BASE / "inferred_group_candidate_field_h1b_computational_truth.json"
REGISTRY = BASE / "inferred_group_candidate_field_fixtures.json"
AGGREGATION_FIXTURE = BASE / "inferred_group_candidate_field_aggregation_semantics_fixture.json"
CANONICAL_KEY_FIXTURE = BASE / "inferred_group_candidate_field_canonical_space_key_fixture.json"
STATUS_MATRIX_FIXTURE = BASE / "inferred_group_candidate_field_status_matrix_fixture.json"
CANDIDATES = EVIDENCE / "d6-inferred-group-candidate-field-h2-candidates.json"
SCORING = EVIDENCE / "d6-inferred-group-candidate-field-h2-scoring.json"
VISUALS = EVIDENCE / "d6-inferred-group-candidate-field-h2-visual-manifest.json"
REPORT = EVIDENCE / "d6-inferred-group-candidate-field-h2-report.md"
DECISION_REVIEW = EVIDENCE / "d6-inferred-group-candidate-field-h2-design-review.md"
RECORD = EVIDENCE / "d6-inferred-group-candidate-field-h2-experiment.json"
ARTIFACT_MANIFEST = EVIDENCE / "d6-inferred-group-candidate-field-h2-repair-artifact-manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    """Read one repository-relative JSON artifact."""
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    """Hash exact artifact bytes for provenance and visual auditing."""
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def save_json(path: Path, value: dict[str, Any]) -> None:
    """Write stable, human-inspectable JSON without changing source inputs."""
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def replicas(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate materialized development and holdout units only."""
    return [item for family in manifest["families"] for split in ("development", "holdout") for item in family[split]]


def transformed(fixture: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    """Apply declared frame transforms to actual polygons, including implicit rectangles."""
    result = copy.deepcopy(fixture)
    scale = float(variant.get("scale", 1.0))
    angle = math.radians(float(variant.get("rotation_degrees", 0.0)))
    tx, ty = variant.get("translation", [0.0, 0.0])

    def point(value: list[float]) -> list[float]:
        """Map a planar vertex through positive scale, rotation, and translation."""
        x, y = value[0] * scale, value[1] * scale
        return [x * math.cos(angle) - y * math.sin(angle) + tx, x * math.sin(angle) + y * math.cos(angle) + ty]

    for group in result["groups"]:
        for member in group["members"]:
            if member.get("status", "computed") == "computed":
                # Explicit vertices prevent rotated H1b rectangles from silently reverting to axis-aligned boxes.
                vertices = member.get("points") or probe._polygon(member["center"], member["size"])
                member["points"] = [point(vertex) for vertex in vertices]
            if "center" in member:
                member["center"] = point(member["center"])
            if "size" in member:
                member["size"] = [dimension * scale for dimension in member["size"]]
    for item in result.get("context", []):
        item["center"] = point(item["center"])
        item["size"] = [dimension * scale for dimension in item["size"]]
    prefix = variant.get("rename_prefix", "")
    if prefix:
        mapping = {group["id"]: prefix + group["id"] for group in result["groups"]}
        for group in result["groups"]:
            group["id"] = mapping[group["id"]]
            for member in group["members"]:
                member["id"] = prefix + member["id"]
        result["space_relations"] = {
            f"{mapping[left]}|{mapping[right]}": value
            for pair_id, value in result.get("space_relations", {}).items()
            for left, right in [pair_id.split("|", 1)]
        }
    if variant.get("reverse_groups"):
        result["groups"].reverse()
    if variant.get("reverse_members"):
        for group in result["groups"]:
            group["members"].reverse()
    result["unit"] = variant.get("unit", result.get("unit", "m"))
    return result


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    """Retain candidate membership, status, and provenance without large geometry payloads."""
    views = []
    for view in result["d1"]["candidate_views"]:
        aggregation_views = []
        for aggregation in view["aggregation_views"]:
            candidates = [
                {
                    "members": item["members"], "candidate_status": item["candidate_status"],
                    "evidence_status": item["evidence_status"], "missingness": item["missingness"],
                    "mutual_exclusion_conflicts": item["mutual_exclusion_conflicts"],
                    "space_role_refs": item["space_role_refs"], "formal_membership_edge": item["formal_membership_edge"],
                    "candidate_relation_ids": item.get("candidate_relation_ids", []),
                    "aggregation_semantics": item.get("aggregation_semantics", {}),
                }
                for item in aggregation["candidates"]
            ]
            aggregation_views.append({"recipe_id": aggregation["aggregation_recipe"]["id"], "candidates": candidates,
                                      "overlapping_members": aggregation["overlapping_members"],
                                      "aggregation_semantics": aggregation.get("aggregation_semantics", {})})
        views.append({"recipe_id": view["recipe_id"], "parameters": view["parameters"],
                      "selected_relation_ids": view["selected_relation_ids"], "aggregation_views": aggregation_views})
    return {"authored_group_ids": result["audit"]["authored_group_ids"],
            "context_object_ids": result["audit"]["context_object_ids"],
            "normalized_space_keys": [{"pair_id": vector["relation_id"], **vector["space_record"]["provenance"]}
                                      for vector in result["d0"]["relation_vectors"]
                                      if vector["space_record"]["provenance"]["key_normalized"]],
            "group_statuses": {item["target_id"]: item["geometry_status"] for item in result["d0"]["evidence"]["group_geometry"]},
            "relation_statuses": {item["relation_id"]: item["status"] for item in result["d0"]["relation_vectors"]},
            "relation_missingness": {item["relation_id"]: item["missingness"] for item in result["d0"]["relation_vectors"]},
            "relation_signature": probe._signature(result), "candidate_views": views,
            "truth_consumed": False, "formal_membership_edge": False}


def probe_command() -> None:
    """Run D1 on fixture inputs in a process that never opens the truth manifest."""
    manifest, registry = read_json(FIXTURES), read_json(REGISTRY)
    variants = registry["invariance"]["variants"]
    output = []
    assert [recipe["id"] for recipe in registry["recipes"]["scale"]] == [
        "relative_gap_rank", "local_persistence_window", "space_profile_rank"]
    assert [recipe["id"] for recipe in registry["recipes"]["aggregation"]] == [
        "selected_relation_connected", "all_internal_pairs", "complete_link_diagnostic", "max_span", "min_gap"]
    semantics = probe.design_semantics_assertions(registry)
    for item in replicas(manifest):
        assert hashlib.sha256(item["seed_material"].encode()).hexdigest() == item["seed_digest_sha256"]
        fixture = {**item["materialized_fixture"], "family": item["family"]}
        canonical = hashlib.sha256(json.dumps(item["materialized_fixture"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        assert canonical == item["materialized_content_sha256"]
        result = probe._fixture_result(fixture, registry)
        if item["family"] == "geometry-conflict":
            recovered = next(vector["space_record"] for vector in result["d0"]["relation_vectors"]
                             if vector["relation_id"] == "ROUNDISH|TALL")
            assert recovered["status"] == "computed"
            assert recovered["provenance"]["source_pair_id"] == "TALL|ROUNDISH"
            assert recovered["provenance"]["key_normalized"] is True
        compact = compact_result(result)
        if item["evaluation_role"] == "generalization_holdout":
            assert compact_result(probe._fixture_result(fixture, registry)) == compact
        assert len(compact["candidate_views"]) == 11
        assert all(len(view["aggregation_views"]) == 5 for view in compact["candidate_views"])
        assert compact["authored_group_ids"] == sorted(group["id"] for group in fixture["groups"])
        assert not set(compact["context_object_ids"]) & set(compact["authored_group_ids"])
        checks = []
        if item["evaluation_role"] == "generalization_holdout":
            for variant in variants:
                changed = compact_result(probe._fixture_result(transformed(fixture, variant), registry))
                checks.append({"variant": variant["id"], "passed": changed["relation_signature"] == compact["relation_signature"],
                               "truth_consumed": False})
            assert all(check["passed"] for check in checks), item["replica_id"]
        output.append({"replica_id": item["replica_id"], "family": item["family"], "seed": item["seed"],
                       "split": item["split"], "evaluation_role": item["evaluation_role"],
                       "materialized_content_sha256": canonical, "invariance_checks": checks, **compact})
    assert len(output) == 32 and sum(item["evaluation_role"] == "generalization_holdout" for item in output) == 16
    result = {"schema": "d6-inferred-group-candidate-field-h2-candidates/v1", "design_only": True,
              "truth_consumed": False, "candidate_probe_inputs": {"fixtures": str(FIXTURES), "fixtures_sha256": digest(FIXTURES),
              "registry": str(REGISTRY), "registry_sha256": digest(REGISTRY),
              "aggregation_semantics_fixture": str(AGGREGATION_FIXTURE), "aggregation_semantics_fixture_sha256": digest(AGGREGATION_FIXTURE),
              "canonical_space_key_fixture": str(CANONICAL_KEY_FIXTURE), "canonical_space_key_fixture_sha256": digest(CANONICAL_KEY_FIXTURE),
              "status_matrix_fixture": str(STATUS_MATRIX_FIXTURE), "status_matrix_fixture_sha256": digest(STATUS_MATRIX_FIXTURE),
              "probe_source": str(BASE / "run_inferred_group_candidate_field_probe.py"),
              "probe_source_sha256": digest(BASE / "run_inferred_group_candidate_field_probe.py")},
              "recipe_registry": registry["recipes"], "design_semantics_assertions": semantics, "replicas": output,
              "mechanisms": {"D0": "computed", "D1": "computed", "B1": "not_run", "M1": "not_run"}}
    save_json(CANDIDATES, result)
    print(f"candidate probe: 32 replicas, 16 holdout, 11 scales, 5 aggregations; {CANDIDATES}")


def pairs(sets: list[list[str]]) -> set[tuple[str, str]]:
    """Union unordered co-membership pairs without turning overlap into a partition."""
    return {pair for members in sets for pair in itertools.combinations(sorted(members), 2)}


def ratio(numerator: int, denominator: int) -> float | None:
    """Represent undefined denominators as null rather than fabricated zero."""
    return numerator / denominator if denominator else None


def metrics(truth_sets: list[list[str]], candidates: list[dict[str, Any]], universe: set[str]) -> dict[str, Any]:
    """Score pair, set, and member recovery while retaining every emitted candidate."""
    emitted = [item for item in candidates if len(item["members"]) > 1 and not item["mutual_exclusion_conflicts"]
               and item["candidate_status"] != "unassigned"]
    predicted_sets = [item["members"] for item in emitted]
    truth_pairs, predicted_pairs = pairs(truth_sets), pairs(predicted_sets)
    tp = len(truth_pairs & predicted_pairs)
    precision, recall = ratio(tp, len(predicted_pairs)), ratio(tp, len(truth_pairs))
    f1 = (2 * precision * recall / (precision + recall) if precision + recall else 0.0) if precision is not None and recall is not None else None
    truth_members = set().union(*(set(members) for members in truth_sets)) if truth_sets else set()
    emitted_members = set().union(*(set(members) for members in predicted_sets)) if predicted_sets else set()
    ambiguous_members = set().union(*(set(item["members"]) for item in emitted if item["candidate_status"] in {"ambiguous", "overlapping"})) if emitted else set()
    unassigned = {member for item in candidates if item["candidate_status"] == "unassigned" and len(item["members"]) == 1 for member in item["members"]}
    # Keep the complete per-truth-set Jaccard distribution; a maximum is diagnostic, not a recipe selection.
    jaccard = [{"truth_members": members, "against_emitted_candidates": [
        len(set(members) & set(candidate)) / len(set(members) | set(candidate)) for candidate in predicted_sets]}
        for members in truth_sets]
    return {"pairwise": {"true_positive": tp, "predicted": len(predicted_pairs), "truth": len(truth_pairs),
                         "precision": precision, "recall": recall, "f1": f1},
            "candidate_set_jaccard": jaccard,
            "member_coverage": ratio(len(truth_members & emitted_members & universe), len(truth_members & universe)),
            "ambiguous_overlapping_coverage": ratio(len(truth_members & ambiguous_members & universe), len(truth_members & universe)),
            "unassigned_coverage": ratio(len(unassigned & universe), len(universe)),
            "emitted_candidate_sets": predicted_sets, "emitted_candidate_statuses": [item["candidate_status"] for item in emitted],
            "emitted_candidate_relation_ids": [item["candidate_relation_ids"] for item in emitted],
            "unassigned_members": sorted(unassigned & universe)}


def hard_gates(candidate: dict[str, Any], fixture: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    """Validate isolation, authored eligibility, vetoes, status propagation, and diagnostics before scoring."""
    authored = {group["id"] for group in fixture["groups"]}
    assert set(candidate["authored_group_ids"]) == authored
    assert not set(candidate["context_object_ids"]) & authored
    assert candidate["truth_consumed"] is False and candidate["formal_membership_edge"] is False
    assert candidate["materialized_content_sha256"] == truth["input_content_sha256"]
    assert all(check["passed"] and not check["truth_consumed"] for check in candidate["invariance_checks"])
    for status, ids in truth["status_targets"].items():
        assert all(candidate["group_statuses"][member] == status for member in ids)
    # Missing and invalid relation evidence must keep its category even when no numeric gap exists.
    if candidate["family"] == "missing-invalid":
        relation_states = set(candidate["relation_statuses"].values())
        assert {"partial", "invalid", "not_available"} <= relation_states
        assert all(candidate["relation_missingness"][pair] for pair, status in candidate["relation_statuses"].items()
                   if status != "computed")
    veto_pairs = {tuple(sorted(item["pair"])) for item in truth["hard_mutual_exclusion_veto_pairs"]}
    observed = set()
    overlap_seen = False
    unassigned_seen = False
    status_seen = set(candidate["group_statuses"].values())
    for view in candidate["candidate_views"]:
        for aggregation in view["aggregation_views"]:
            sets = []
            for item in aggregation["candidates"]:
                assert set(item["members"]) <= authored
                assert item["formal_membership_edge"] is False
                if item["mutual_exclusion_conflicts"]:
                    assert item["candidate_status"] == "unassigned"
                    observed |= veto_pairs & pairs([item["members"]])
                elif len(item["members"]) > 1 and item["candidate_status"] != "unassigned":
                    assert not (pairs([item["members"]]) & veto_pairs)
                    sets.append(item["members"])
                if item["candidate_status"] == "unassigned" and len(item["members"]) == 1:
                    unassigned_seen = True
            overlap_seen |= bool(aggregation["overlapping_members"])
            assert len(aggregation["candidates"]) >= len(sets)
    assert observed == veto_pairs, (candidate["replica_id"], observed, veto_pairs)
    assert status_seen <= {"computed", "partial", "invalid", "not_available"}
    expected_unassigned = set(truth["expected_unassigned_singleton_diagnostic"]["unassigned"])
    if expected_unassigned:
        observed_unassigned = {record["members"][0] for view in candidate["candidate_views"]
                               for aggregation in view["aggregation_views"] for record in aggregation["candidates"]
                               if record["candidate_status"] == "unassigned" and len(record["members"]) == 1}
        assert expected_unassigned <= observed_unassigned
    return {"authored_context_separation": True, "hard_veto": True, "status_propagation": True,
            "invariance_reproducibility": True, "truth_isolation": True,
            "overlap_retained": overlap_seen, "unassigned_singleton_retained": unassigned_seen,
            "status_values": sorted(status_seen)}


def score_command() -> None:
    """Open computational truth only in evaluation phase and score holdout units."""
    candidate_data, manifest, truth_data = read_json(CANDIDATES), read_json(FIXTURES), read_json(TRUTH)
    assert candidate_data["truth_consumed"] is False
    assert candidate_data["design_semantics_assertions"]["aggregation_semantics"]["passed"]
    assert candidate_data["design_semantics_assertions"]["canonical_space_key"]["passed"]
    assert candidate_data["design_semantics_assertions"]["status_matrix"]["passed"]
    truth_by_id = {item["replica_id"]: item for item in truth_data["replicas"]}
    fixture_by_id = {item["replica_id"]: item for item in replicas(manifest)}
    rows, gate_rows = [], []
    for candidate in candidate_data["replicas"]:
        item = fixture_by_id[candidate["replica_id"]]
        truth = truth_by_id[candidate["replica_id"]]
        assert item["materialized_content_sha256"] == truth["input_content_sha256"]
        if candidate["evaluation_role"] != "generalization_holdout":
            assert candidate["evaluation_role"] == "development_reference"
            continue
        gate_rows.append({"replica_id": candidate["replica_id"], **hard_gates(candidate, item["materialized_fixture"], truth)})
        universe = set(candidate["authored_group_ids"])
        for view in candidate["candidate_views"]:
            for aggregation in view["aggregation_views"]:
                candidates = aggregation["candidates"]
                by_status = {}
                for status, members in truth["status_targets"].items():
                    stratum = set(members)
                    stratum_truth = [sorted(set(group) & stratum) for group in truth["candidate_member_sets"]]
                    stratum_truth = [group for group in stratum_truth if len(group) > 1]
                    stratum_candidates = [{**record, "members": sorted(set(record["members"]) & stratum)} for record in candidates]
                    by_status[status] = {"member_count": len(stratum), **metrics(stratum_truth, stratum_candidates, stratum)}
                candidate_evidence = {}
                for status in ("computed", "partial", "invalid", "not_available"):
                    filtered = [record for record in candidates if record["evidence_status"] == status]
                    candidate_evidence[status] = {"candidate_count": len(filtered),
                                                  **metrics(truth["candidate_member_sets"], filtered, universe)}
                rows.append({"family": candidate["family"], "seed": candidate["seed"], "replica_id": candidate["replica_id"],
                             "evaluation_role": "generalization_holdout", "scale_recipe": view["recipe_id"],
                             "scale_parameters": view["parameters"], "aggregation_recipe": aggregation["recipe_id"],
                             "evidence_status": candidate_evidence, "truth_member_status": by_status,
                             "overall_descriptive": metrics(truth["candidate_member_sets"], candidates, universe),
                             "candidate_status_counts": {status: sum(record["candidate_status"] == status for record in candidates)
                                                        for status in sorted({record["candidate_status"] for record in candidates})},
                             "veto_diagnostic_count": sum(bool(record["mutual_exclusion_conflicts"]) for record in candidates)})
    assert len(gate_rows) == 16 and len(rows) == 16 * 11 * 5
    assert all(row["evaluation_role"] == "generalization_holdout" for row in rows)
    statuses = {status for row in rows for status in row["candidate_status_counts"]}
    assert {"ambiguous", "overlapping", "weak", "unassigned", "diagnostic_only"} <= statuses
    aggregation_outputs = {}
    for recipe_id in ("selected_relation_connected", "all_internal_pairs", "complete_link_diagnostic", "max_span", "min_gap"):
        aggregation_outputs[recipe_id] = [row["overall_descriptive"]["emitted_candidate_sets"] for row in rows if row["aggregation_recipe"] == recipe_id]
    assert len({json.dumps(value, sort_keys=True) for value in aggregation_outputs.values()}) >= 3
    assert aggregation_outputs["selected_relation_connected"] != aggregation_outputs["all_internal_pairs"]
    disagreement = []
    for replica_id in sorted({row["replica_id"] for row in rows}):
        unit_rows = [row for row in rows if row["replica_id"] == replica_id]
        signatures = [json.dumps(row["overall_descriptive"]["emitted_candidate_sets"], sort_keys=True) for row in unit_rows]
        disagreement.append({"replica_id": replica_id, "distinct_candidate_set_outputs": len(set(signatures)),
                             "all_55_views_preserved": len(signatures) == 55})
    result = {"schema": "d6-inferred-group-candidate-field-h2-scoring/v1", "status": "design_only_stop_for_design_review",
              "truth_type": truth_data["truth_type"], "holdout_replica_count": 16, "scored_view_count": len(rows),
              "hard_gates": gate_rows, "recipe_disagreement": disagreement, "rows": rows,
              "input_hashes": {str(path): digest(path) for path in (FIXTURES, TRUTH, REGISTRY, CANDIDATES)},
              "role_policy": {"scored": ["generalization_holdout"], "debug_only": ["development_reference"],
                              "excluded": ["replication_only", "invariance_only"]},
              "mechanisms": {"D0": "computed", "D1": "computed", "B1": "not_run", "M1": "not_run"},
              "aggregation_difference_assertion": {"passed": True, "compared": list(aggregation_outputs),
                                                   "distinct_output_families": len({json.dumps(value, sort_keys=True) for value in aggregation_outputs.values()})},
              "no_winner_or_threshold_selected": True}
    save_json(SCORING, result)
    print(f"scoring: {len(rows)} holdout views; 16 hard-gate records; {SCORING}")


def report_command() -> None:
    """Write family-by-recipe ranges without ranking or choosing any recipe."""
    scoring, visuals = read_json(SCORING), read_json(VISUALS)
    rows = scoring["rows"]
    lines = ["# D6 H2 membership-level holdout recovery", "", "日期：2026-09-29。状态：design-only repair/re-run，STOP FOR DESIGN REVIEW。",
             "", "仅 `generalization_holdout`：8 family × seed 303/404 × 11 scale views × 5 aggregation views = 880 视图。",
             "`development_reference` 仅调试；`replication_only`、`invariance_only` 未计分。B1、M1 = `not_run`。",
             "", "## 硬门槛与解释边界", "", "16/16 holdout 的 authored/context separation、veto、状态传播、",
             "invariance/reproducibility、truth isolation 已通过。candidate probe 只读取 H1b fixture manifest 和已注册 recipe。",
             "评分阶段单独读取 computational truth；此 truth 是 evaluation-side structural truth，非人的正确答案或心理效度。",
             "singleton/unassigned、overlap、ambiguity 均保留在 candidates JSON；无 formal membership edge。",
             "", "本 repair 分离 aggregation 语义：`selected_relation_connected` 保留选中的关系连通结构，`all_internal_pairs` 要求每个内部无序 pair 都 selected/available/computed-valid 且 gap 有限；`max_span` 实际检查候选内部最大 pairwise gap，",
             "`complete_link_diagnostic` 保留 maximal-clique 对照，`min_gap` 仅保留 pair witness，不解释为 group partition。",
             "`max_span` 的 gap 上界来自 gap-rank bound；其他 scale 用已选关系的最大 gap 作诊断参照，绝不把 space-profile bound 当作 gap。",
             "独立 semantics fixture 断言三者输出不同；没有据此选择 winner、scale、threshold 或 production selector。",
             "registry 已拆分 `selected_relation_connected` 与 `all_internal_pairs`；两者均为 design-only diagnostics，不选择 winner。",
             "该文字与修订语义的冲突留待 design review；不把修订后的探索结果称为预注册规则验证。",
             "", "`geometry-conflict` 保留 H1b 原始 `TALL|ROUNDISH` 字节。probe 查询在设计边界 canonicalize 为 `ROUNDISH|TALL`，",
             "并保留 `source_pair_id` 与 `key_normalized` provenance；受影响的 `space_profile_rank` 结果已重算。",
             "seed 303 的 q=.5/.75 profile bound 从 .72146709/.72146709 变为 .534910515/.6281888025；",
             "seed 404 从 .66264227/.66264227 变为 .490664895/.5766535825。两 seed 的 selected relation 均仍为 `CUBE|TALL`。",
             "", "## 分层结果", "", "完整 880 行含 family、seed、scale 参数、aggregation、四类 output evidence status 与 truth-member status。",
             "每行记录 pairwise precision/recall/F1、每个 truth set 对所有 emitted set 的 Jaccard 分布、",
             "member/ambiguous-overlapping/unassigned coverage、candidate status counts 与 veto diagnostics。",
             "空 truth 或空预测的无定义指标写 `null`，不伪装为 0。下表 F1 是两 seed、同一 recipe 类全部注册参数的范围；",
             "仅描述差异，不是 winner 排名或验收阈值。", "",
             "| Family | Scale recipe | Aggregation recipe | F1 range | Output patterns |",
             "|---|---|---|---|---:|"]
    for family in sorted({row["family"] for row in rows}):
        for scale in ("relative_gap_rank", "local_persistence_window", "space_profile_rank"):
            for aggregation in ("selected_relation_connected", "all_internal_pairs", "complete_link_diagnostic", "max_span", "min_gap"):
                subset = [row for row in rows if row["family"] == family and row["scale_recipe"] == scale
                          and row["aggregation_recipe"] == aggregation]
                values = [row["overall_descriptive"]["pairwise"]["f1"] for row in subset]
                defined = [value for value in values if value is not None]
                span = f"{min(defined):.3f}–{max(defined):.3f}" if defined else "null"
                patterns = len({json.dumps(row["overall_descriptive"]["emitted_candidate_sets"], sort_keys=True) for row in subset})
                lines.append(f"| {family} | `{scale}` | `{aggregation}` | {span} | {patterns} |")
    lines += ["", "## Recipe disagreement", ""]
    for item in scoring["recipe_disagreement"]:
        lines.append(f"- `{item['replica_id']}`：55 视图，{item['distinct_candidate_set_outputs']} 种 candidate-set 输出。")
    lines += ["", "全部分歧与每条 emitted set 保存在 scoring JSON；aggregation difference assertion 已通过。",
              "`candidate_relation_ids` 保留 emitted structure 的 selected pair evidence；`min_gap` 明确为 pair witness。",
              "", "## Provenance 与范围", "",
              "- 输入及 candidate JSON 的 SHA-256 见 scoring JSON `input_hashes`。",
              "- D1 recipe registry 与 probe 在起始 Git 状态为未跟踪文件；本提交将纳入两者，确保复现 H2。",
              "- 5 张确定性 SVG 的路径、大小和 SHA-256 见 visual manifest；每张图标注 geometry/variable diagnostic only。Blender 本 checkpoint 未运行。",
              "- 无数值 threshold、recipe winner、production selector、公共 API 或依赖变更。",
              "", "**STOP FOR DESIGN REVIEW**", ""]
    (ROOT / REPORT).write_text("\n".join(lines), encoding="utf-8")
    print(f"report: {len(lines)} lines; {REPORT}")


def record_command() -> None:
    """Freeze H2 artifact provenance, scope, and held-out evaluation roles."""
    scoring, visuals = read_json(SCORING), read_json(VISUALS)
    candidates = read_json(CANDIDATES)
    script = BASE / "run_inferred_group_candidate_field_h2.py"
    probe_script = BASE / "run_inferred_group_candidate_field_probe.py"
    output = {
        "schema": "d6-inferred-group-candidate-field-h2-experiment/v2",
        "date": "2026-09-29", "status": "design_only_stop_for_design_review",
        "estimand": "membership-level candidate member sets; overlap and unassigned allowed",
        "truth": {"kind": "evaluation-side structural truth; not a human correct answer",
                  "candidate_probe_access": False, "scoring_access": True},
        "registered_scales": [recipe["id"] for recipe in candidates["recipe_registry"]["scale"]],
        "registered_aggregations": [recipe["id"] for recipe in candidates["recipe_registry"]["aggregation"]],
        "effective_aggregation_semantics": {"selected_relation_connected": "selected-relation connected structure with explicit relation ids",
                                            "all_internal_pairs": "maximal candidate sets whose every unordered internal pair is selected, available, computed/valid, and has finite normalized gap",
                                            "max_span": "connected candidate with maximum internal normalized gap within gap-unit bound",
                                            "min_gap": "selected-pair witness; not a group partition",
                                            "complete_link_diagnostic": "maximal clique of selected-pair graph"},
        "roles": scoring["role_policy"], "development_seeds": [101, 202], "holdout_seeds": [303, 404],
        "holdout_replicas": 16, "scored_views": scoring["scored_view_count"],
        "hard_gates": {"holdout_passed": len(scoring["hard_gates"]),
                       "checks": ["authored/context separation", "hard mutual-exclusion veto with source reference",
                                  "categorical missing/invalid/partial/not_available propagation",
                                  "invariance and deterministic reproducibility", "truth isolation",
                                  "overlap/ambiguity/weak/unassigned/singleton diagnostic retained"]},
        "artifact_sha256": {str(path).replace("\\", "/"): digest(path)
                            for path in (FIXTURES, TRUTH, REGISTRY, AGGREGATION_FIXTURE, CANONICAL_KEY_FIXTURE, STATUS_MATRIX_FIXTURE,
                                         CANDIDATES, SCORING, VISUALS, REPORT, DECISION_REVIEW, probe_script, script)},
        "visual_artifacts": visuals["artifacts"],
        "recipe_disagreement": scoring["recipe_disagreement"],
        "mechanisms": {"D0": "computed", "D1": "computed", "B1": "not_run", "M1": "not_run"},
        "scope_audit": {"production_selector": "not_modified", "numerical_threshold": "not_selected",
                        "winner": "not_selected", "features_adapters_tests_neutral_scene_api_dependencies": "not_modified",
                        "blender": visuals["blender"],
                        "repair_scope": ["aggregation semantics", "canonical unordered space-key lookup", "holdout re-score", "deterministic SVG refresh"],
                        "known_probe_limitation": "space-key canonicalization accepts legacy unordered fixture keys; H1b input bytes remain unchanged",
                        "registry_rule_discrepancy": "resolved by splitting selected_relation_connected and all_internal_pairs; both remain design diagnostics"},
    }
    save_json(RECORD, output)
    print(f"experiment record: {RECORD}")


def artifact_manifest_command() -> None:
    """Write a non-circular hash manifest for the repair checkpoint artifacts."""
    record = read_json(RECORD)
    paths = sorted(record["artifact_sha256"])
    output = {"schema": "d6-inferred-group-candidate-field-h2-repair-artifact-manifest/v1",
              "status": "design_only_stop_for_design_review", "self_hash_excluded": True,
              "artifacts": [{"path": path, "sha256": record["artifact_sha256"][path],
                             "bytes": (ROOT / Path(path)).stat().st_size} for path in paths],
              "visual_artifacts": read_json(VISUALS)["artifacts"],
              "scope": {"repair": ["design probe aggregation semantics", "canonical unordered space-key lookup", "H2 holdout re-score", "SVG refresh"],
                        "production_selector": "not_modified", "threshold": "not_selected", "winner": "not_selected",
                        "B1": "not_run", "M1": "not_run"}}
    save_json(ARTIFACT_MANIFEST, output)
    print(f"artifact manifest: {ARTIFACT_MANIFEST}")


def svg_for(fixture: dict[str, Any], truth: dict[str, Any], row: dict[str, Any]) -> str:
    """Render deterministic 2D geometry, candidate sets, vetoes, roles, and status labels."""
    groups = fixture["groups"]
    points = {group["id"]: group["members"][0].get("center", [0.0, 0.0]) for group in groups}
    xs, ys = [point[0] for point in points.values()], [point[1] for point in points.values()]
    left, right, low, high = min(xs), max(xs), min(ys), max(ys)
    sx = 540 / max(right - left, 1.0)
    sy = 320 / max(high - low, 1.0)
    coords = {key: (100 + (xy[0] - left) * sx, 460 - (xy[1] - low) * sy) for key, xy in points.items()}
    colors = ["#1677b7", "#7b4eb2", "#19815e", "#b2741d", "#bb4d7d"]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="700" viewBox="0 0 1060 700">',
             '<rect width="1060" height="700" fill="#fff"/>',
             f'<text x="35" y="40" font-size="23" font-family="sans-serif">D6 H2 {escape(row["family"])} | seed {row["seed"]}</text>',
             f'<text x="35" y="70" font-size="15" font-family="sans-serif">recipe: {escape(row["scale_recipe"])} {escape(str(row["scale_parameters"]))} / {escape(row["aggregation_recipe"])}</text>',
             '<text x="35" y="96" font-size="14" font-family="sans-serif">Geometry/variable diagnostic only; not psychological validity evidence or production accuracy.</text>',
             '<text x="35" y="118" font-size="14" font-family="sans-serif">Gray boxes: authored furniture groups; colored edges: emitted candidate sets; red dashed: hard veto pair.</text>']
    for index, members in enumerate(row["overall_descriptive"]["emitted_candidate_sets"]):
        relation_ids = row["overall_descriptive"]["emitted_candidate_relation_ids"][index]
        pair_ids = relation_ids if row["aggregation_recipe"] == "selected_relation_connected" else ["|".join(sorted(pair)) for pair in itertools.combinations(members, 2)]
        for pair_id in pair_ids:
            a, b = pair_id.split("|", 1)
            if a in coords and b in coords:
                x1, y1 = coords[a]; x2, y2 = coords[b]
                lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{colors[index % len(colors)]}" stroke-width="{5 + index % 3}" opacity="0.65"/>')
    for veto in truth["hard_mutual_exclusion_veto_pairs"]:
        a, b = veto["pair"]
        x1, y1 = coords[a]; x2, y2 = coords[b]
        lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#d62828" stroke-width="4" stroke-dasharray="10 6"/>')
    status_map = {member: status for status, ids in truth["status_targets"].items() for member in ids}
    for group in groups:
        key = group["id"]; x, y = coords[key]; status = status_map.get(key, "computed")
        fill = {"computed": "#eceff1", "partial": "#fff1b8", "invalid": "#ffc9c9", "not_available": "#dddddd"}[status]
        lines.extend([f'<rect x="{x-37:.2f}" y="{y-22:.2f}" width="74" height="44" rx="7" fill="{fill}" stroke="#303030" stroke-width="2"/>',
                      f'<text x="{x:.2f}" y="{y+5:.2f}" text-anchor="middle" font-size="16" font-family="sans-serif">{escape(key)}</text>',
                      f'<text x="{x:.2f}" y="{y+39:.2f}" text-anchor="middle" font-size="11" font-family="sans-serif">{escape(status)}</text>'])
    lines.append('<rect x="700" y="135" width="325" height="488" fill="#f8fafb" stroke="#ccd2d6"/>')
    entries = ["Emitted candidate sets:"] + [f"{index+1}. {' + '.join(group)} [{status}]" for index, (group, status) in enumerate(zip(
        row["overall_descriptive"]["emitted_candidate_sets"], row["overall_descriptive"]["emitted_candidate_statuses"]))]
    entries += ["", "Evaluation-side structural truth:"] + [" + ".join(group) for group in truth["candidate_member_sets"]]
    entries += ["", "Unassigned: " + (", ".join(row["overall_descriptive"]["unassigned_members"]) or "none")]
    roles = sorted({role for relation in fixture.get("space_relations", {}).values() for role in relation.get("role_refs", [])})
    entries += ["", "Empty-space roles (evidence only):"] + (roles or ["not_available"])
    entries += ["", "Context: " + (", ".join(item["id"] for item in fixture.get("context", [])) or "none")]
    for index, entry in enumerate(entries):
        lines.append(f'<text x="716" y="{160 + index*24}" font-size="13" font-family="sans-serif">{escape(entry)}</text>')
    lines.append('<text x="35" y="660" font-size="13" font-family="sans-serif">Structural truth is evaluation-side computation, not a human correct answer or psychological validation.</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def visual_command() -> None:
    """Write five representative SVG diagnostics and a byte-hash manifest."""
    scoring, manifest, truth_data = read_json(SCORING), read_json(FIXTURES), read_json(TRUTH)
    fixture_by_id = {item["replica_id"]: item["materialized_fixture"] for item in replicas(manifest)}
    truth_by_id = {item["replica_id"]: item for item in truth_data["replicas"]}
    selection = {"gap-jump": ("relative_gap_rank", 0.5, "selected_relation_connected"),
                 "bridge-chain": ("space_profile_rank", 0.5, "min_gap"),
                 "overlapping-candidates": ("space_profile_rank", 0.5, "min_gap"),
                 "space-conflict": ("space_profile_rank", 0.5, "min_gap"),
                 "missing-invalid": ("relative_gap_rank", 0.5, "selected_relation_connected")}
    artifacts = []
    for family, (recipe, quantile, aggregation) in selection.items():
        row = next(item for item in scoring["rows"] if item["family"] == family and item["seed"] == 303
                   and item["scale_recipe"] == recipe and item["scale_parameters"].get("quantile") == quantile
                   and item["aggregation_recipe"] == aggregation)
        path = EVIDENCE / f"d6-h2-{family}-seed303.svg"
        (ROOT / path).write_text(svg_for(fixture_by_id[row["replica_id"]], truth_by_id[row["replica_id"]], row), encoding="utf-8")
        artifacts.append({"path": str(path).replace("\\", "/"), "sha256": digest(path), "bytes": (ROOT / path).stat().st_size,
                          "family": family, "seed": 303, "recipe_id": recipe, "scale_parameters": row["scale_parameters"],
                          "aggregation_recipe": aggregation, "truth_label": "evaluation-side structural truth"})
    save_json(VISUALS, {"schema": "d6-inferred-group-candidate-field-h2-visual-manifest/v2",
                        "status": "design_only_stop_for_design_review", "artifacts": artifacts,
                        "scoring_sha256": digest(SCORING), "blender": {"status": "not_run", "reason": "2D deterministic SVG diagnostics satisfy the optional visualization path"},
                        "interpretation": "Geometry and variable diagnostics only; no psychological validity or production accuracy claim."})
    print(f"visuals: {len(artifacts)} SVGs; {VISUALS}")


def verify_command() -> None:
    """Check JSON, scoring invariants, SVG XML, source hashes, and visual hashes."""
    import xml.etree.ElementTree as ET

    candidate_data, scoring, visuals, record = read_json(CANDIDATES), read_json(SCORING), read_json(VISUALS), read_json(RECORD)
    assert candidate_data["truth_consumed"] is False
    assert candidate_data["design_semantics_assertions"]["aggregation_semantics"]["passed"]
    assert candidate_data["design_semantics_assertions"]["canonical_space_key"]["passed"]
    assert candidate_data["design_semantics_assertions"]["status_matrix"]["passed"]
    for replica in candidate_data["replicas"]:
        if replica["family"] == "geometry-conflict" and replica["evaluation_role"] == "generalization_holdout":
            assert any(item["pair_id"] == "ROUNDISH|TALL" and item["source_pair_id"] == "TALL|ROUNDISH"
                       for item in replica["normalized_space_keys"])
    assert scoring["scored_view_count"] == 880 and len(scoring["rows"]) == 880
    assert scoring["aggregation_difference_assertion"]["passed"]
    assert all(all(value for key, value in gate.items() if key in {"authored_context_separation", "hard_veto", "status_propagation", "invariance_reproducibility", "truth_isolation"}) for gate in scoring["hard_gates"])
    assert all(row["evaluation_role"] == "generalization_holdout" and set(row["evidence_status"]) == {"computed", "partial", "invalid", "not_available"} for row in scoring["rows"])
    for row in scoring["rows"]:
        for result in [row["overall_descriptive"], *row["evidence_status"].values(), *row["truth_member_status"].values()]:
            pair = result["pairwise"]
            assert 0 <= pair["true_positive"] <= min(pair["predicted"], pair["truth"])
            assert pair["precision"] == ratio(pair["true_positive"], pair["predicted"])
            assert pair["recall"] == ratio(pair["true_positive"], pair["truth"])
            if pair["precision"] is not None and pair["recall"] is not None:
                expected = (2 * pair["precision"] * pair["recall"] / (pair["precision"] + pair["recall"])
                            if pair["precision"] + pair["recall"] else 0.0)
                assert pair["f1"] == expected
            else:
                assert pair["f1"] is None
            assert all(0 <= value <= 1 for group in result["candidate_set_jaccard"] for value in group["against_emitted_candidates"])
            assert all(value is None or 0 <= value <= 1 for key, value in result.items() if key.endswith("coverage"))
    assert all(digest(Path(path)) == value for path, value in scoring["input_hashes"].items())
    assert visuals["scoring_sha256"] == digest(SCORING)
    assert record["artifact_sha256"][str(REPORT).replace("\\", "/")] == digest(REPORT)
    assert record["artifact_sha256"][str(DECISION_REVIEW).replace("\\", "/")] == digest(DECISION_REVIEW)
    assert all(digest(Path(path)) == value for path, value in record["artifact_sha256"].items())
    for artifact in visuals["artifacts"]:
        path = Path(artifact["path"])
        assert digest(path) == artifact["sha256"] and (ROOT / path).stat().st_size == artifact["bytes"]
        ET.parse(ROOT / path)
    assert record["artifact_sha256"][str(AGGREGATION_FIXTURE).replace("\\", "/")] == digest(AGGREGATION_FIXTURE)
    assert record["artifact_sha256"][str(CANONICAL_KEY_FIXTURE).replace("\\", "/")] == digest(CANONICAL_KEY_FIXTURE)
    assert record["artifact_sha256"][str(STATUS_MATRIX_FIXTURE).replace("\\", "/")] == digest(STATUS_MATRIX_FIXTURE)
    manifest = read_json(ARTIFACT_MANIFEST)
    assert all(digest(Path(item["path"])) == item["sha256"] and (ROOT / Path(item["path"])).stat().st_size == item["bytes"] for item in manifest["artifacts"])
    print("verified: JSON/schema, 880 scoring rows, 16 hard gates, source hashes, 5 SVG/XML hashes")


def main() -> None:
    """Run one isolated H2 stage selected by the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["probe", "score", "visual", "report", "record", "manifest", "verify"])
    stage = parser.parse_args().stage
    {"probe": probe_command, "score": score_command, "visual": visual_command, "report": report_command,
     "record": record_command, "manifest": artifact_manifest_command, "verify": verify_command}[stage]()


if __name__ == "__main__":
    main()
