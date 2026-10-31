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
    _family_representatives,
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


def test_hierarchy_preview_indexes_every_leaf_family_and_cell(tmp_path: Path) -> None:
    """Render complete hierarchy views from retained geometry without altering inputs."""
    replay = Path(__file__).parents[1] / "outputs/design/group_axis_field_hierarchy_ifc/replay_v1"
    before = {path.relative_to(replay).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in replay.rglob("*") if path.is_file()}
    output = run(replay, tmp_path / "preview")
    family_matrix = json.loads((replay / "family_matrix.json").read_text(encoding="utf-8"))["families"]
    view_manifest = json.loads((replay / "view_manifest.json").read_text(encoding="utf-8"))
    page = (output / "index.html").read_text(encoding="utf-8")
    embedded = re.search(r'<script id="preview-data" type="application/json">(.*?)</script>', page, re.S)
    assert embedded is not None
    data = json.loads(embedded.group(1))
    families = data["hierarchy"]["families"]
    definitions = {family["family_id"]: family for family in json.loads((replay / "hierarchy.json").read_text(encoding="utf-8"))["families"]}
    # Strings survive JavaScript JSON.parse even when exact integers exceed 2**53.
    for family in families:
        for key in ("birth_exact", "death_exact"):
            assert family[key] == [str(part) for part in family_matrix[family["id"]][key]]
        for axis, source_axis in zip(family["direction_classes"], definitions[family["id"]]["direction_classes"], strict=True):
            assert axis["theta_exact"] == [str(part) for part in source_axis["theta_exact"]]
    unsafe_family = next(family for family in families if family["id"] == "axis-family:006bce9b8bec07dba043f99a9434c11e5fe827f24458bb9f110a2cf5053c94df")
    assert unsafe_family["birth_exact"][0] == "119673276493035827057"
    assert isinstance(family_matrix[unsafe_family["id"]]["birth_exact"][0], int)
    readme = (output / "README.md").read_text(encoding="utf-8")
    assert "FieldFamily" in readme and "family_matrix.svg" in readme
    assert "没有硬分组、空间势边界、FieldFamily 或 merge" not in readme
    assert len(data["fields"]) == 37
    assert len(families) == len(family_matrix)
    assert {family["id"] for family in families} == set(family_matrix)
    assert sum(len(family["cells"]) for family in families) == sum(len(family["cells"]) for family in family_matrix.values())
    family_svg = ET.parse(output / "family_matrix.svg")
    assert len(family_svg.findall(".//*[@data-family-cell]")) == sum(len(family["cells"]) for family in family_matrix.values())
    assert len(ET.parse(output / "matrix.svg").findall(".//*[@data-value]")) == 1369
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["family_map"]) == len(family_matrix)
    assert len(manifest["leaf_map"]) == 37
    assert len(manifest["target_index"]) == len(view_manifest["target_index"])
    assert {item["target_identity"] for item in manifest["target_index"]} == {item["target_identity"] for item in view_manifest["target_index"]}
    assert all(item["href"].startswith("index.html#") for item in manifest["target_index"])
    assert "family_matrix.svg" in {Path(item["path"]).name for item in manifest["artifacts"]}
    samples = manifest["family_representatives"]
    assert [sample["selection"] for sample in samples] == ["small", "overlap_top_a", "overlap_top_b"]
    assert [next(family["code"] for family in families if family["id"] == sample["family_id"]) for sample in samples] == ["H204", "H159", "H174"]
    selected = [next(family for family in families if family["id"] == sample["family_id"]) for sample in samples]
    assert len(selected[0]["anchor_group_ids"]) == min(len(family["anchor_group_ids"]) for family in families if len(family["anchor_group_ids"]) > 1)
    left, right = (set(family["anchor_group_ids"]) for family in selected[1:])
    assert left & right and left - right and right - left
    assert all(not definitions[family["id"]]["parent_ids"] for family in selected[1:])
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    for sample, family in zip(samples, selected, strict=True):
        tree = ET.parse(output / sample["path"])
        nodes = tree.findall(".//*[@data-support]")
        assert len(nodes) == 37
        assert sample["anchor_group_ids"] == family["anchor_group_ids"]
        assert (output / sample["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert family["id"] in (output / sample["path"]).read_text(encoding="utf-8")
        for node, group, cell in zip(nodes, data["groups"], family["cells"], strict=True):
            anchor = group["id"] in family["anchor_group_ids"]
            assert node.attrib == {"data-group": group["id"], "data-support": str(cell["value"]), "data-self": str(anchor).lower()}
            paths = node.findall("svg:path", namespace)
            assert [path.attrib["d"] for path in paths] == group["paths"]
            assert all(path.attrib["fill"] == _color(cell["value"]) for path in paths)
            assert all(path.attrib["stroke"] == ("#b34900" if anchor else "#526879") for path in paths)
            assert node.find("svg:text", namespace).text == ("* " if anchor else "") + group["code"]
            assert f'{group["code"]} | {_label(cell["value"], 6)} | {cell["status"]}' in "".join(tree.getroot().itertext())
    assert len(list(output.glob("family_representative_*.png"))) == 3
    for item in manifest["artifacts"] + manifest["inputs"] + manifest["hierarchy_inputs"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert before == {path.relative_to(replay).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in replay.rglob("*") if path.is_file()}


def test_family_representatives_skip_unavailable_choices() -> None:
    """Skip missing samples using empty metadata and one retained real top family."""
    assert _family_representatives({"hierarchy": {"families": []}}) == {}
    replay = Path(__file__).parents[1] / "outputs/design/group_axis_field_hierarchy_ifc/replay_v1"
    definition = next(family for family in json.loads((replay / "hierarchy.json").read_text(encoding="utf-8"))["families"] if not family["parent_ids"])
    family = {"id": definition["family_id"], **{key: definition[key] for key in ("anchor_group_ids", "scale_persistence", "parent_ids")}}
    assert _family_representatives({"hierarchy": {"families": [family]}}) == {"small": 0}
