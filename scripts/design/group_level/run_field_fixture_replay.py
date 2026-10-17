"""Replay the design-only evidence fixtures with deterministic audit output.

This script reuses the existing group-level probe formulas only as a replay
oracle.  Its output is deliberately labelled design-only and must not be read
as a production Field, free-space, or inferred-group result.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


FORMULA_SCOPE = "probe_only_not_production"
SCRIPT_PATH = Path(__file__).with_name("run_self_description_competition_probe.py")


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one local evidence file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_probe(path: Path) -> Any:
    """Load probe-local helpers without importing production features."""
    spec = importlib.util.spec_from_file_location("field_fixture_probe", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load probe module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalise_result(result: dict[str, Any]) -> dict[str, Any]:
    """Sort fixture and candidate records without changing channel values."""
    normalised = copy.deepcopy(result)
    normalised["candidates"] = sorted(
        normalised["candidates"],
        key=lambda item: tuple(sorted(item["candidate"])),
    )
    for candidate in normalised["candidates"]:
        candidate["pair_observations"] = sorted(
            candidate["pair_observations"],
            key=lambda item: tuple(item["groups"]),
        )
    return normalised


def _canonical_observations(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create the stable fixture/candidate observation sequence used for hashing."""
    return sorted(
        (_normalise_result(result) for result in results),
        key=lambda item: item["fixture_id"],
    )


def _fixture(fixtures: list[dict[str, Any]], fixture_id: str) -> dict[str, Any]:
    """Return one declared fixture by stable identifier."""
    return next(item for item in fixtures if item["id"] == fixture_id)


def _candidate(result: dict[str, Any], members: list[str]) -> dict[str, Any]:
    """Return one probe candidate by its unordered member ids."""
    wanted = set(members)
    return next(item for item in result["candidates"] if set(item["candidate"]) == wanted)


def _geometry_signature(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only geometry observations for channel-local comparisons."""
    def rounded(geometry: dict[str, Any]) -> dict[str, Any]:
        return {
            key: round(value, 8) if isinstance(value, float) else value
            for key, value in geometry.items()
        }

    return [
        {
            "candidate": sorted(candidate["candidate"]),
            "geometry": [
                {
                    "groups": observation["groups"],
                    "geometry": rounded(observation["geometry"]),
                }
                for observation in candidate["pair_observations"]
            ],
        }
        for candidate in sorted(result["candidates"], key=lambda item: tuple(sorted(item["candidate"])))
    ]


def _run_transform(
    name: str,
    baseline: Callable[[dict[str, Any]], dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run one deterministic perturbation and retain its audit explanation."""
    if name == "identifier_order":
        source = copy.deepcopy(fixtures[0])
        source["groups"] = list(reversed(source["groups"]))
        source["candidates"] = list(reversed(source["candidates"]))
        original = baseline(fixtures[0])
        changed = baseline(source)
        passed = _normalise_result(original) == _normalise_result(changed)
        detail = "reordering identifiers and candidate input preserves canonical observations"
    elif name == "translation":
        source = copy.deepcopy(_fixture(fixtures, "geometry_conflict"))
        for group in source["groups"]:
            group["center"] = [group["center"][0] + 7.5, group["center"][1] - 3.25]
        original = baseline(_fixture(fixtures, "geometry_conflict"))
        changed = baseline(source)
        passed = _geometry_signature(original) == _geometry_signature(changed)
        detail = "rigid translation preserves probe-local geometry channel values"
    elif name == "supported_rotation":
        source = copy.deepcopy(_fixture(fixtures, "geometry_conflict"))
        for group in source["groups"]:
            x, y = group["center"]
            group["center"] = [-y, x]
        original = baseline(_fixture(fixtures, "geometry_conflict"))
        changed = baseline(source)
        passed = _geometry_signature(original) == _geometry_signature(changed)
        detail = "wall-free quarter-turn preserves probe-local geometry relations"
    elif name == "opening_mutation":
        source = copy.deepcopy(_fixture(fixtures, "space_barrier"))
        source["walls"][0]["opening"] = True
        original = baseline(_fixture(fixtures, "space_barrier"))
        changed = baseline(source)
        left = _candidate(original, ["A", "B"])
        right = _candidate(changed, ["A", "B"])
        passed = (
            left["pair_observations"][0]["geometry"] == right["pair_observations"][0]["geometry"]
            and left["pair_observations"][0]["semantic"] == right["pair_observations"][0]["semantic"]
            and left["pair_observations"][0]["space"]["barrier"] == "blocked"
            and right["pair_observations"][0]["space"]["barrier"] == "opening"
        )
        detail = "declared opening changes only the space barrier observation"
    elif name == "missing_domain":
        source = copy.deepcopy(_fixture(fixtures, "context_reference"))
        source["domain"] = False
        original = baseline(_fixture(fixtures, "context_reference"))
        changed = baseline(source)
        left = _candidate(original, ["A", "B"])
        right = _candidate(changed, ["A", "B"])
        passed = (
            left["pair_observations"][0]["geometry"] == right["pair_observations"][0]["geometry"]
            and right["pair_observations"][0]["space"]["domain_status"] == "not_available"
            and right["support"]["space"] == 0.0
        )
        detail = "missing domain preserves geometry and marks space evidence unavailable"
    else:
        raise ValueError(f"Unknown perturbation: {name}")
    return {
        "name": name,
        "passed": bool(passed),
        "formula_scope": FORMULA_SCOPE,
        "design_only": True,
        "detail": detail,
    }


def build_report(fixtures_path: Path) -> dict[str, Any]:
    """Build a deterministic replay report from the declared fixture file."""
    probe = _load_probe(SCRIPT_PATH)
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    fixtures = payload["fixtures"]
    if len(fixtures) != 8:
        raise ValueError(f"Expected eight fixtures, received {len(fixtures)}")
    run_fixture = probe._run_fixture
    results = [run_fixture(fixture) for fixture in fixtures]
    checks = probe._assertions(results)
    canonical = _canonical_observations(results)
    canonical_bytes = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    perturbations = [
        _run_transform(name, run_fixture, fixtures)
        for name in ("identifier_order", "translation", "supported_rotation", "opening_mutation", "missing_domain")
    ]
    if not all(item["passed"] for item in perturbations):
        raise AssertionError(perturbations)
    blocked_cases = [
        {
            "name": name,
            "blocked": True,
            "design_only": True,
            "formula_scope": FORMULA_SCOPE,
            "reason": reason,
        }
        for name, reason in (
            ("invalid_geometry_to_missing", "fixture schema has invalid but no distinct missing geometry state"),
            ("rotated_wall_representation", "fixture wall schema only represents vertical x plus y-range walls"),
            ("section_vs_whole_height", "fixtures have XY geometry but no height-band or whole-height channel"),
        )
    ]
    status_matrix = [
        {
            "fixture_id": result["fixture_id"],
            "statuses": [
                {"candidate": candidate["candidate"], "status": candidate["status"]}
                for candidate in result["candidates"]
            ],
        }
        for result in canonical
    ]
    provenance = [
        {
            "fixture_id": result["fixture_id"],
            "candidate": candidate["candidate"],
            "provenance": candidate["provenance"],
            "formula_scope": FORMULA_SCOPE,
        }
        for result in canonical
        for candidate in result["candidates"]
    ]
    return {
        "schema": "field-kernel-free-space-fixture-replay/v1",
        "fixture_path": str(fixtures_path),
        "fixture_sha256": _sha256(fixtures_path),
        "probe_path": str(SCRIPT_PATH),
        "probe_sha256": _sha256(SCRIPT_PATH),
        "fixture_count": len(fixtures),
        "analysis_frame": payload.get("analysis_frame"),
        "design_only": True,
        "formula_scope": FORMULA_SCOPE,
        "canonical_observations": canonical,
        "canonical_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        "canonical_bytes": len(canonical_bytes),
        "fixtures": canonical,
        "assertions": checks,
        "status_matrix": status_matrix,
        "provenance": provenance,
        "channel_isolation": {
            "passed": len(checks),
            "total": len(checks),
            "design_only": True,
            "assertions": checks,
        },
        "perturbations": perturbations,
        "blocked_cases": blocked_cases,
    }


def main() -> None:
    """Write one replay report without timestamps in canonical content."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.fixtures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"fixture_count": report["fixture_count"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
