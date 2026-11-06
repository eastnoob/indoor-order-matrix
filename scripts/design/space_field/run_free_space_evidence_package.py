"""Authenticate and publish a retained free-space result through the shared package.

The reusable adapter owns computation/cache. This CLI reads an explicit saved
ResultRef and independent consumer expectations; it never claims live currentness.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import time
from xml.etree import ElementTree as ET

from adapters.blender_analysis_result_wire import (
    ResultReadContext, ResultRef, load_json, open_analysis_result, plain,
)
from adapters.free_space_evidence_package import evaluate_saved_free_space_package
from features.field_core import (
    evaluate_evidence_package_freshness, serialize_evidence_package_output,
)
from features.free_space_evidence_package import build_free_space_package_contract


def _file_hash(path: Path) -> str:
    """Hash exact artifact bytes without interpreting their contents."""
    with path.open("rb") as stream:
        return sha256(stream.read()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    """Replace complete strict JSON atomically, preserving prior bytes on failure."""
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _visualization_manifest(serialized: dict, document: dict, output_dir: Path) -> dict:
    """Bind every package target to its retained cell and actual display fragments."""
    fragments = defaultdict(list)
    for index, fragment in enumerate(document.get("display_fragments", ())):
        fragments[fragment["cell_index"]].append(index)
    targets = []
    n_cols = document["tables"]["lattice"]["n_cols"]
    for item in serialized["outputs"]:
        locator = item["observation"]["cell_locator"]
        row, column = locator["row"], locator["column"]
        cell_index = row * n_cols + column
        targets.append({
            "target_id": item["target"]["identity"], "row": row, "column": column,
            "cell_index": cell_index, "svg_element": f"cell-{row}-{column}",
            "fragment_indices": fragments[cell_index],
        })
    return {
        "schema": "free-space-evidence-visualization/v1",
        "output_identity": serialized["output_identity"], "channel": "free_space",
        "source_result_ref": {key: document[key] for key in ("kind", "result_id", "digest")},
        "freshness_scope": "historical retained result; live scene not observed",
        "artifact_bindings": {
            "plan_svg": str((output_dir / "free_space_plan.svg").resolve()),
            "blender": str((output_dir / "free_space_evidence.blend").resolve()),
            "preview_png": str((output_dir / "free_space_evidence.png").resolve()),
        },
        "targets": targets,
    }


def _write_plan(serialized: dict, document: dict, manifest: dict, path: Path) -> None:
    """Project actual retained fragments to the declared plane for a categorical SVG."""
    lattice = document["tables"]["lattice"]
    plane = document["tables"]["snapshot"]["request"]["plane"]
    width, height = lattice["n_cols"] * lattice["spacing"], lattice["n_rows"] * lattice["spacing"]
    x0, y0 = lattice["origin"]
    margin = width * .04
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    def tag(name: str) -> str:
        """Use the standard SVG namespace for parser-verifiable geometry."""
        return "{http://www.w3.org/2000/svg}" + name
    root = ET.Element(tag("svg"), {
        "viewBox": f"{-margin} {-margin} {width + 2 * margin} {height + 5 * margin}",
        "width": "1400", "height": "1000", "role": "img",
    })
    ET.SubElement(root, tag("title")).text = "Free space: retained IFC result, plane-local metres"
    ET.SubElement(root, tag("rect"), {"x": str(-margin), "y": str(-margin),
        "width": str(width + 2 * margin), "height": str(height + 5 * margin), "fill": "#f2f4f6"})
    by_target = {item["target"]["identity"]: item for item in serialized["outputs"]}
    for target in manifest["targets"]:
        output = by_target[target["target_id"]]
        observation = output["observation"]
        value, raw_status = observation["value"], observation["raw_status"]
        # Conditional observations remain visually uncertain even when their value is Boolean.
        color = "#4fbf9f" if value is True and raw_status == "established" else (
            "#273449" if value is False and raw_status == "established" else "#e6ae4c")
        group = ET.SubElement(root, tag("g"), {"id": target["svg_element"], "fill": color,
            "data-target": target["target_id"], "data-status": raw_status})
        for fragment_index in target["fragment_indices"]:
            fragment = document["display_fragments"][fragment_index]
            projected = []
            for vertex in fragment["vertices"]:
                delta = [vertex[axis] - plane["origin"][axis] for axis in range(3)]
                local = [sum(delta[axis] * plane["basis"][basis][axis] for axis in range(3)) for basis in (0, 1)]
                projected.append((local[0] - x0, height - (local[1] - y0)))
            for face in fragment["faces"]:
                points = " ".join(f"{projected[index][0]:.9g},{projected[index][1]:.9g}" for index in face)
                ET.SubElement(group, tag("polygon"), {"points": points})
    for index, text in enumerate((
        "Green: established free | Dark: established occupied | Amber: uncertain",
        "Outside / no fragment: blank; blank never establishes free space",
        "Historical retained result | metres | free space does not prove route clearance",
    )):
        ET.SubElement(root, tag("text"), {"x": "0", "y": str(height + (index + 1) * margin),
            "font-size": str(margin * .28), "font-family": "sans-serif", "fill": "#273449"}).text = text
    path.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    ET.parse(path)


def publish_saved_free_space_result(
    source: Path, result_ref: ResultRef, context: ResultReadContext, output_dir: Path,
) -> dict:
    """Publish shared output, contract/status and spatial bindings from exact saved data."""
    started = time.perf_counter()
    source_hash = _file_hash(source)
    document = load_json(source.read_text(encoding="utf-8"))
    snapshot = open_analysis_result([document], result_ref=result_ref, context=context)
    package = evaluate_saved_free_space_package(snapshot)
    serialized = serialize_evidence_package_output(package)
    projection_seconds = time.perf_counter() - started
    manifest = _visualization_manifest(serialized, document, output_dir)
    contract = build_free_space_package_contract(document, visualization_manifest=manifest)
    # An exact retained result is authenticated, but there is no independent live-scene observation.
    status = evaluate_evidence_package_freshness(cached_contract=contract, current_contract=None)
    status.update(read_state="historical", freshness_scope=manifest["freshness_scope"], retained_result_integrity="verified")
    if _file_hash(source) != source_hash:
        raise ValueError("retained input changed during publication")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "free_space_package_output.json"
    _write_json(output_path, serialized)
    _write_plan(serialized, document, manifest, output_dir / "free_space_plan.svg")
    for name, payload in (("visualization_manifest", manifest), ("package_contract", contract), ("package_status", status)):
        _write_json(output_dir / (name + ".json"), payload)
    source_manifest = {
        "source": str(source.resolve()), "source_sha256": source_hash,
        "source_result_ref": manifest["source_result_ref"], "consumer_expected": plain(context.expected),
        "source_channel_count": 1, "derived_channel_names": ["free_space"],
        "output_identity": serialized["output_identity"], "read_state": "historical",
    }
    _write_json(output_dir / "source_manifest.json", source_manifest)
    receipt = {
        "output_identity": serialized["output_identity"], "package_identity": contract["package_identity"],
        "source_result_ref": manifest["source_result_ref"], "target_count": len(serialized["outputs"]),
        "evidence_channel_count": 1, "raw_status_counts": dict(Counter(cell["status"] for cell in document["cells"])),
        "free_space_value_counts": dict(Counter(str(item["observation"]["value"]) for item in serialized["outputs"])),
        "geometry_recomputed": False, "read_state": "historical",
        "authenticated_projection_seconds": projection_seconds, "publication_seconds": time.perf_counter() - started,
        "artifact_hashes": {path.name: _file_hash(path) for path in (
            output_path, output_dir / "free_space_plan.svg", output_dir / "visualization_manifest.json",
            output_dir / "package_contract.json", output_dir / "package_status.json", output_dir / "source_manifest.json")},
    }
    _write_json(output_dir / "publication_receipt.json", receipt)
    return receipt


def main() -> None:
    """Read an explicit reference and independently retained consumer expectations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expectations", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    expectations = load_json(args.expectations.read_text(encoding="utf-8"))
    reference = ResultRef(**expectations["result_ref"])
    context = ResultReadContext(expected=expectations["expected"],
        backend_versions=expectations.get("backend_versions"), allow_historical=True)
    print(json.dumps(publish_saved_free_space_result(args.result, reference, context, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
