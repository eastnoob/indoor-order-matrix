"""Check the output-only renderer against the retained real IFC replay."""

import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.design.group_level.render_group_axis_potential_preview import (
    INPUTS,
    REPLAY,
    _color,
    _label,
    run,
)


def test_preview_preserves_real_ifc_readings_and_scope(tmp_path: Path) -> None:
    """Keep all original values and identities while projecting only source geometry."""
    before = {name: (REPLAY / name).read_bytes() for name in INPUTS}
    output = run(REPLAY, tmp_path)
    page = (output / "index.html").read_text(encoding="utf-8")
    embedded = re.search(r'<script id="preview-data" type="application/json">(.*?)</script>', page, re.S)
    assert embedded is not None
    data = json.loads(embedded.group(1))
    matrix = json.loads(before["field_matrix.json"])["fields"]
    profiles = json.loads(before["field_profiles.json"])["profiles"]
    directions = json.loads(before["field_directions.json"])["directions"]
    geometry = json.loads(before["description.json"])["group_geometry"]
    assert len(data["groups"]) == len(data["fields"]) == 37
    assert {group["id"] for group in data["groups"]} == {group["target_id"] for group in geometry}
    assert sum(len(group["paths"]) for group in data["groups"]) == sum(len(member["polygons"]) for group in geometry for member in group["member_geometry"])
    for field in data["fields"]:
        assert field["cells"] == matrix[field["id"]]["cells"]
        assert field["profile"] == profiles[field["id"]]
        assert field["direction"] == directions[field["id"]]
        assert len(field["cells"]) == 37
        assert sum(cell["self_reference"] for cell in field["cells"]) == 1
    assert sum(len(field["cells"]) for field in data["fields"]) == 1369
    assert [round(data["fields"][index]["angle"]) for index in data["representatives"]] == [0, 90, 128]
    matrix_xml = ET.parse(output / "matrix.svg")
    assert len(matrix_xml.findall(".//*[@data-value]")) == 1369
    for path in output.glob("representative_*.svg"):
        tree = ET.parse(path)
        assert len(tree.findall(".//*[@data-support]")) == 37
        assert len(tree.findall('.//*[@data-self="true"]')) == 1
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cell_count"] == 1369
    assert manifest["analysis_plane"] == json.loads(before["source_manifest.json"])["analysis_plane"]
    for item in manifest["artifacts"] + manifest["inputs"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert before == {name: (REPLAY / name).read_bytes() for name in INPUTS}
    assert _color(None) != _color(0)
    assert _label(None) == "NA" and _label(0) == "0.000"
    assert _color(1) == "#1a4c8b"
    assert len(list(output.glob("*.png"))) == 4
    assert not re.search(r"[\u4e00-\u9fff]", (output / "matrix.svg").read_text(encoding="utf-8"))
