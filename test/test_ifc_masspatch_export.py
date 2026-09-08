import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test" / "bim"))

from export_rhino_source_ifc import write_ifc
from features.rhino_block_mapping import normalize_rhino_blocks


def _source_payload() -> dict[str, object]:
    """Return one compact furniture source for proxy export tests."""
    return {
        "source_name": "proxy-test",
        "objects": [
            {
                "id": "chair-1",
                "kind": "chair",
                "vertices": [
                    [0, 0, 0],
                    [1000, 0, 0],
                    [1000, 1000, 0],
                    [0, 1000, 0],
                ],
                "faces": [[0, 1, 2], [0, 2, 3]],
                "source_ids": ["chair-1"],
            }
        ],
    }


def _substitute_payload() -> dict[str, object]:
    """Return one explicit MassPatch binding in millimetre source coordinates."""
    return {
        "substitutes": [
            {
                "source_global_id": "chair-1",
                "substitute_id": "patch-1",
                "substitute_kind": "MassPatch",
                "analysis_role": "analysis_geometry_substitute",
                "visibility_policy": "analysis_only",
                "vertices": [
                    [0, 0, 0],
                    [1000, 0, 0],
                    [1000, 1000, 0],
                    [0, 1000, 0],
                ],
                "triangle_indices": [[0, 1, 2], [0, 2, 3]],
            }
        ]
    }


def test_source_only_export_has_no_analysis_proxies(tmp_path: Path) -> None:
    """The backward-compatible export path writes only authoritative products."""
    source = tmp_path / "source.json"
    target = tmp_path / "source-only.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")

    report = write_ifc(source, target)

    assert report["proxy_object_count"] == 0
    import ifcopenshell

    model = ifcopenshell.open(str(target))
    assert len(model.by_type("IfcFurniture")) == 1
    assert len(model.by_type("IfcBuildingElementProxy")) == 0


def test_explicit_substitute_is_exported_separately_and_bound_to_source(
    tmp_path: Path,
) -> None:
    """Explicit sidecar mode preserves the traceable compatibility proxy."""
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "with-proxy.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")
    substitutes.write_text(json.dumps(_substitute_payload()), encoding="utf-8")

    report = write_ifc(
        source,
        target,
        substitute_path=substitutes,
        substitute_mode="sidecar",
    )

    assert report["proxy_object_count"] == 1
    import ifcopenshell

    model = ifcopenshell.open(str(target))
    assert len(model.by_type("IfcFurniture")) == 1
    proxies = model.by_type("IfcBuildingElementProxy")
    assert len(proxies) == 1
    proxy = proxies[0]
    assert proxy.ObjectPlacement is not None
    assert proxy.Tag == "patch-1"
    property_sets = [
        relation.RelatingPropertyDefinition
        for relation in proxy.IsDefinedBy
        if relation.RelatingPropertyDefinition.is_a("IfcPropertySet")
    ]
    analysis_set = next(item for item in property_sets if item.Name == "OM_AnalysisProxy")
    values = {
        item.Name: item.NominalValue.wrappedValue
        for item in analysis_set.HasProperties
    }
    assert values["OM_SourceGlobalId"] == "chair-1"
    assert values["OM_ProxyKind"] == "MassPatch"
    assert values["OM_VisibilityPolicy"] == "analysis_only"


def test_exported_proxy_loads_as_analysis_substitute_not_furniture(
    tmp_path: Path,
) -> None:
    """The neutral IFC adapter preserves proxy role separation after export."""
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "with-proxy.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")
    substitutes.write_text(json.dumps(_substitute_payload()), encoding="utf-8")

    write_ifc(
        source,
        target,
        substitute_path=substitutes,
        substitute_mode="sidecar",
    )

    from adapters.ifc_bonsai import load_ifc_neutral_scene

    scene = load_ifc_neutral_scene(target)
    furniture = [item for item in scene.source_objects if item.source_role == "furniture"]
    proxies = [
        item
        for item in scene.source_objects
        if item.source_role == "analysis_substitute"
    ]
    assert len(furniture) == 1
    assert len(proxies) == 1
    assert proxies[0].factual_properties["OM_AnalysisProxy"]["OM_SourceGlobalId"] == "chair-1"


def test_explicit_substitute_defaults_to_same_product_analysis_representation(
    tmp_path: Path,
) -> None:
    """Default export keeps Body and MassPatch on one furniture product."""
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "with-analysis-representation.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")
    substitutes.write_text(json.dumps(_substitute_payload()), encoding="utf-8")

    report = write_ifc(source, target, substitute_path=substitutes)

    import ifcopenshell

    model = ifcopenshell.open(str(target))
    furniture = model.by_type("IfcFurniture")
    assert len(furniture) == 1
    assert len(model.by_type("IfcBuildingElementProxy")) == 0
    representations = furniture[0].Representation.Representations
    assert [item.RepresentationIdentifier for item in representations] == [
        "Body",
        "Analysis",
    ]
    assert len(model.by_type("IfcProductDefinitionShape")) == 1
    assert report["substitute_mode"] == "representation"
    assert report["analysis_representation_count"] == 1
    assert report["proxy_object_count"] == 0
    assert report["analysis_representation_bindings"] == [
        {"source_global_id": "chair-1", "substitute_id": "patch-1"}
    ]
    assert report["proxy_bindings"] == []


def test_analysis_representation_loads_as_separate_analysis_evidence(
    tmp_path: Path,
) -> None:
    """The adapter separates Analysis geometry from visible furniture geometry."""
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "with-analysis-representation.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")
    substitutes.write_text(json.dumps(_substitute_payload()), encoding="utf-8")
    write_ifc(source, target, substitute_path=substitutes)

    from adapters.ifc_bonsai import load_ifc_neutral_scene

    scene = load_ifc_neutral_scene(target)
    furniture = [item for item in scene.source_objects if item.source_role == "furniture"]
    substitutes = [
        item
        for item in scene.source_objects
        if item.source_role == "analysis_substitute"
    ]
    assert len(furniture) == 1
    assert len(furniture[0].geometry_refs) == 1
    assert len(substitutes) == 1
    assert len(substitutes[0].geometry_refs) == 1
    assert substitutes[0].factual_properties["OM_AnalysisRepresentation"][
        "OM_SourceGlobalId"
    ] == "chair-1"


def test_shifted_analysis_representation_preserves_world_coordinates(
    tmp_path: Path,
) -> None:
    """World-authored MassPatch geometry survives product localization."""
    source_payload = _source_payload()
    substitute_payload = _substitute_payload()
    for vertex in source_payload["objects"][0]["vertices"]:
        vertex[0] += 5000
        vertex[1] += 7000
    for vertex in substitute_payload["substitutes"][0]["vertices"]:
        vertex[0] += 5000
        vertex[1] += 7000
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "shifted.ifc"
    source.write_text(json.dumps(source_payload), encoding="utf-8")
    substitutes.write_text(json.dumps(substitute_payload), encoding="utf-8")
    write_ifc(source, target, substitute_path=substitutes)

    from adapters.ifc_bonsai import load_ifc_neutral_scene

    scene = load_ifc_neutral_scene(target)
    analysis_object = next(
        item for item in scene.source_objects if item.source_role == "analysis_substitute"
    )
    analysis_mesh = next(
        mesh for mesh in scene.geometries if mesh.id in analysis_object.geometry_refs
    )
    assert min(vertex[0] for vertex in analysis_mesh.vertices) == pytest.approx(5.0)
    assert min(vertex[1] for vertex in analysis_mesh.vertices) == pytest.approx(7.0)


def test_export_rejects_unknown_substitute_mode(tmp_path: Path) -> None:
    """Reject misspelled modes instead of silently changing IFC semantics."""
    source = tmp_path / "source.json"
    target = tmp_path / "invalid-mode.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="substitute_mode"):
        write_ifc(source, target, substitute_mode="proxy")


def test_substitute_must_bind_to_an_exported_source(tmp_path: Path) -> None:
    """Do not serialize an orphan analysis proxy with an unverifiable source."""
    source = tmp_path / "source.json"
    substitutes = tmp_path / "substitutes.json"
    target = tmp_path / "invalid.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")
    payload = _substitute_payload()
    payload["substitutes"][0]["source_global_id"] = "missing-chair"
    substitutes.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not a source furniture object"):
        write_ifc(source, target, substitute_path=substitutes)


def test_nested_block_mapping_keeps_masspatch_out_of_furniture_count(
    tmp_path: Path,
) -> None:
    """Export one root furniture product while preserving its substitute role."""
    block_report = normalize_rhino_blocks(
        {
            "instances": [
                {
                    "id": "chair-1",
                    "user_text": {
                        "OM.Role": "logical_product",
                        "OM.IfcEntity": "IfcFurniture",
                        "OM.TypeKey": "chair.standard",
                        "OM.InstanceId": "chair-1",
                    },
                    "children": [
                        {
                            "id": "chair-1-geometry",
                            "user_text": {
                                "OM.RepresentationRole": "display_geometry"
                            },
                            "components": [
                                {
                                    "id": "chair-mesh",
                                    "kind": "chair",
                                    "geometry_signature": "chair-v1",
                                    "vertices": [
                                        [0, 0, 0],
                                        [1000, 0, 0],
                                        [1000, 1000, 0],
                                    ],
                                    "faces": [[0, 1, 2]],
                                }
                            ],
                        },
                        {
                            "id": "chair-1-masspatch",
                            "user_text": {
                                "OM.RepresentationRole": "analysis_substitute",
                                "OM.SubstituteKind": "MassPatch",
                                "OM.SourceInstanceId": "chair-1",
                            },
                            "components": [{"id": "patch"}],
                        },
                    ],
                }
            ]
        }
    )
    source = tmp_path / "nested-source.json"
    target = tmp_path / "nested-source.ifc"
    source.write_text(
        json.dumps(
            {
                "source_name": "nested-block-test",
                "objects": block_report["logical_objects"],
            }
        ),
        encoding="utf-8",
    )

    report = write_ifc(source, target)

    assert report["furniture_count"] == 1
    assert len(block_report["representations"]) == 2
    assert block_report["representations"][1]["substitute_kind"] == "MassPatch"
