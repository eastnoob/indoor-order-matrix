"""Canonical live identities and independent structural facts."""

from dataclasses import replace

import pytest

from ..adapters.blender_analysis_capture import CanonicalCaptureInput, digest
from ..adapters.bonsai_live import load_bonsai_capture, StructuralContext
from .test_analysis_requests import _plane, _object


def capture(*roles):
    """Build actual closed geometry with explicit project, GUID and STEP facts."""
    records = []
    for step, role in enumerate(roles or ("wall", "furniture", "plant", "slab"), 1):
        source, mesh = _object(str(step), role=role)
        records.append({"id": f"ifc-object:g{step}", "global_id": f"g{step}",
                        "step_id": step, "project_global_id": "project", "ifc_class":
                        {"wall": "IfcWall", "slab": "IfcSlab", "door": "IfcDoor"}.get(role, "IfcFurniture"),
                        "role": role, "properties": {}, "status": "extracted",
                        "mesh": mesh.to_dict(), "binding_verified": True})
    return CanonicalCaptureInput(identity={"project_global_id": "project", "ifc_source_identity": "source", "schema": "IFC4"},
                                 records=records, diagnostics=(), observation={"scene_token": "session"})


def test_canonical_identity_map_requires_project_guid_step_and_geometry():
    """Only verified complete identities become factual IFC sources."""
    result = load_bonsai_capture(capture(), plane=_plane())
    assert all(source.id == "ifc-object:" + source.source_id for source in result.scene.source_objects)
    assert len(result.scene.source_objects) == 4
    assert result.structural_scene.geometries[0] is result.scene.geometries[0]
    rows = capture().to_dict()["records"]
    rows[0]["binding_verified"] = False
    with pytest.raises(ValueError, match="identity"):
        load_bonsai_capture(replace(capture(), records=rows), plane=_plane())


def test_live_capture_preserves_only_authored_groups_and_binds_membership():
    """Raw explicit membership survives the native handoff and invalidates changed capture identity."""
    data = capture("furniture", "furniture").to_dict()
    original = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert original.scene.authored_groups == ()
    group = {"id": "ifc-group:G", "source_id": "G", "member_refs": ["ifc-object:g1"],
             "group_role": "furniture_group", "provenance": {"method": "ifc4_group_assignment"}}
    data["identity"]["authored_groups"] = [group]
    grouped = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert grouped.scene.authored_groups[0].member_refs == ("ifc-object:g1",)
    assert grouped.full_fingerprint != original.full_fingerprint
    group["member_refs"].append("ifc-object:g2")
    changed = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert changed.full_fingerprint != grouped.full_fingerprint


def test_selected_wall_context_canonicalizes_order_and_changes_frame_identity():
    """Selection order is neutral while a different wall set is a different structural frame."""
    first = StructuralContext.from_plane(
        _plane(), storey_ref="ifc-object:S7",
        selected_wall_refs=("ifc-object:wall-b", "ifc-object:wall-a"))
    reordered = StructuralContext.from_plane(
        _plane(), storey_ref="ifc-object:S7",
        selected_wall_refs=("ifc-object:wall-a", "ifc-object:wall-b"))
    changed = StructuralContext.from_plane(
        _plane(), storey_ref="ifc-object:S7",
        selected_wall_refs=("ifc-object:wall-a", "ifc-object:wall-c"))
    assert first.selected_wall_refs == ("ifc-object:wall-a", "ifc-object:wall-b")
    assert first.structural_frame_key == reordered.structural_frame_key
    assert changed.structural_frame_key != first.structural_frame_key


def test_unbound_floor_remains_occupancy():
    """Absence of explicit support consent excludes no physical floor."""
    result = load_bonsai_capture(capture(), plane=_plane())
    assert result.domain_support_audit["source_id"] is None
    assert any(source.source_role == "slab" for source in result.scene.source_objects)


def test_selected_ifcspace_domain_keeps_source_identity_and_storey():
    """A verified IfcSpace can be exposed as an authored domain without changing inventory."""
    data = capture("space", "slab", "furniture").to_dict()
    data["records"][0].update(
        ifc_class="IfcSpace", role="space", level_ref="ifc-object:storey-1",
        container_refs=["ifc-object:storey-1"], properties={"Name": "Room A"},
    )
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    source = live.scene.source_objects[0]
    assert source.source_role == "space"
    assert source.source_id == "g1"
    assert source.level_ref == "ifc-object:storey-1"
    assert source.container_refs == ("ifc-object:storey-1",)


def test_authored_space_domain_rejects_non_space_or_cross_storey():
    """Domain selection must require the verified IfcSpace role and requested storey."""
    from ..adapters.bonsai_live import authored_space_domain
    live = load_bonsai_capture(capture("furniture", "slab"), plane=_plane())
    with pytest.raises(ValueError, match="IfcSpace"):
        authored_space_domain(live.scene, "g1")
    data = capture("space", "slab").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", role="space", level_ref="ifc-object:storey-1")
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    with pytest.raises(ValueError, match="storey"):
        authored_space_domain(live.scene, "g1", storey_ref="ifc-object:storey-2")


@pytest.mark.parametrize("failure", ["missing_containment", "conflicting_containment", "canonical_id", "disjoint",
                                    "missing_geometry", "open_mesh", "wrong_project"])
def test_authored_space_rejects_ambiguous_native_scope_and_disjoint_projection(failure):
    """An authored Space cannot gain validity from a guessed storey or disconnected footprint."""
    from ..adapters.bonsai_live import authored_space_domain
    from .test_analysis_requests import _object
    data = capture("space").to_dict()
    row = data["records"][0]
    row.update(ifc_class="IfcSpace", level_ref="ifc-object:storey-1", container_refs=["ifc-object:storey-1"])
    if failure == "missing_containment":
        row["container_refs"] = []
    elif failure == "conflicting_containment":
        row["container_refs"].append("ifc-object:storey-2")
    elif failure == "disjoint":
        first = row["mesh"]
        _, second = _object("separate", (4, 0, 0, 5, 1, 1), role="space")
        offset = len(first["vertices"])
        first["vertices"] += second.to_dict()["vertices"]
        first["triangle_indices"] += [[index + offset for index in face] for face in second.triangle_indices]
    elif failure == "missing_geometry":
        row["mesh"] = None
        row["status"] = "missing_geometry"
    elif failure == "open_mesh":
        row["mesh"]["is_closed"] = False
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    scene = live.scene
    if failure == "canonical_id":
        scene = replace(scene, source_objects=(replace(scene.source_objects[0], id="wrong-source"),))
    elif failure == "wrong_project":
        scene = replace(scene, source_objects=(replace(scene.source_objects[0], provenance={
            **scene.source_objects[0].provenance, "project_global_id": "other-project"}),))
    with pytest.raises(ValueError, match="storey|identity|single|projection|geometry"):
        authored_space_domain(scene, "g1", storey_ref="ifc-object:storey-1")


def test_existing_space_domain_preserves_one_hole_without_authoring_inputs():
    """A closed square-ring prism adopts with its complete hole and exact 12 m² support."""
    from ..adapters.blender_analysis_session import evaluate_domain_request
    data = capture("space").to_dict()
    ring = ((0, 0), (4, 0), (4, 4), (0, 4), (1, 1), (3, 1), (3, 3), (1, 3))
    vertices = [(point[0], point[1], height) for height in (0, 3) for point in ring]
    faces = []
    for index in range(4):
        following = (index + 1) % 4
        quads = ((index, following, following + 4, index + 4),
                 (index + 8, index + 12, following + 12, following + 8),
                 (index, index + 8, following + 8, following),
                 (index + 4, following + 4, following + 12, index + 12))
        faces.extend(face for first, second, third, fourth in quads
                     for face in ((first, second, third), (first, third, fourth)))
    row = data["records"][0]
    row.update(ifc_class="IfcSpace", level_ref="ifc-object:storey-1", container_refs=["ifc-object:storey-1"])
    row["mesh"].update(vertices=vertices, triangle_indices=faces)
    scene = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane()).scene
    result = evaluate_domain_request(scene, context=StructuralContext.from_plane(_plane()), prior=None,
        action=None, domain_source_id="g1", storey_ref="ifc-object:storey-1")
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["holes"] == 1
    assert result["candidates"][0]["area_m2"] == pytest.approx(12.0)


def test_space_composition_hashes_actual_geometry_and_ignores_display_name():
    """The existing result binding observes native geometry, never only its reference string."""
    from ..adapters.bonsai_live import authored_space_composition
    data = capture("space").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    scene = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane()).scene
    first = authored_space_composition(scene, "g1", storey_ref="ifc-object:storey-1")
    assert first["space_guid"] == "g1" and first["source_id"] == "ifc-object:g1"
    assert first["origin"] == "adopted" and first["provenance"]["source_step_id"] == 1
    renamed = replace(scene, source_objects=(replace(scene.source_objects[0], factual_properties={"Name": "Renamed"}),))
    assert authored_space_composition(renamed, "g1", storey_ref="ifc-object:storey-1") == first
    moved = replace(scene, geometries=(replace(scene.geometries[0],
        vertices=tuple((point[0] + 2, *point[1:]) for point in scene.geometries[0].vertices)),))
    assert authored_space_composition(moved, "g1", storey_ref="ifc-object:storey-1")["geometry_digest"] != first["geometry_digest"]
    created = {**first, "origin": "created_from_b4", "provenance": {**first["provenance"],
        "authoring": {"candidate_id": "candidate-A", "session_revision": 2, "outline_digest": "a" * 64}}}
    assert authored_space_composition(scene, "g1", storey_ref="ifc-object:storey-1", previous=created) == created
    with pytest.raises(ValueError, match="Space observation changed"):
        authored_space_composition(moved, "g1", storey_ref="ifc-object:storey-1", previous=created)


def test_structural_storey_scope_requires_unique_membership_and_filters_openings():
    """Other-floor facts leave B4 only with unique storey proof and related openings."""
    from ..adapters.bonsai_live import structural_b4_view

    data = capture("wall", "door", "furniture", "wall", "door", "furniture",
                   "wall", "wall", "furniture", "wall", "furniture", "furniture").to_dict()
    for index, storey in enumerate(("S7", "S7", "S7", "S8", "S8", "S8")):
        data["records"][index].update(
            level_ref=f"ifc-object:{storey}", container_refs=[f"ifc-object:{storey}"])
    for index in (2, 5, 10, 11):
        data["records"][index]["ifc_class"] = "IfcOpeningElement"
    data["records"][2]["opening_facts"] = {"host_source_ids": ["g1"], "filling_source_ids": ["g2"]}
    data["records"][5]["opening_facts"] = {"host_source_ids": ["g4"], "filling_source_ids": ["g5"]}
    data["records"][6].update(level_ref="ifc-object:S8", container_refs=["ifc-object:S7"])
    data["records"][7].update(level_ref="ifc-object:S8",
                              container_refs=["ifc-object:S8", "ifc-object:g9"])
    data["records"][8].update(ifc_class="IfcBuilding", mesh=None, status="missing_geometry")
    data["records"][9].update(level_ref="ifc-object:S8",
                              container_refs=["ifc-object:S8", "ifc-object:unknown-container"])
    data["records"][10]["opening_facts"] = {"host_source_ids": ["missing-host"], "filling_source_ids": []}
    data["records"][11].update(level_ref="ifc-object:S7", container_refs=["ifc-object:S7"],
                                opening_facts={"host_source_ids": ["g4"], "filling_source_ids": []})
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    context = StructuralContext.from_plane(_plane(), storey_ref="ifc-object:S7")

    scoped = structural_b4_view(live.scene, context=context)

    assert {source.id for source in scoped.source_objects} == {
        "ifc-object:g1", "ifc-object:g2", "ifc-object:g7", "ifc-object:g10"}
    assert [opening.id for opening in scoped.openings] == [
        "ifc-opening:g3", "ifc-opening:g11", "ifc-opening:g12"]
    assert {"ifc-mesh:g3", "ifc-mesh:g11", "ifc-mesh:g12"} <= {
        mesh.id for mesh in scoped.geometries}
    assert "ifc-mesh:g6" not in {mesh.id for mesh in scoped.geometries}


def test_structural_digest_is_independent_of_furniture_and_capture_volatility():
    """Structural changes invalidate B4, occupancy and capture changes do not."""
    original = load_bonsai_capture(capture(), plane=_plane())
    changed = capture().to_dict()
    changed["records"][1]["mesh"]["vertices"][0][0] += 4
    changed["observation"]["scene_token"] = "another-session"
    other = load_bonsai_capture(CanonicalCaptureInput(**changed), plane=_plane(origin=(0, 0, 99), revision=2, name="renamed"))
    assert original.structural_fingerprint == other.structural_fingerprint
    assert original.capture_fingerprint != other.capture_fingerprint
    assert original.structural_scene.context.analysis_plane == other.structural_scene.context.analysis_plane
    changed["records"][0]["mesh"]["vertices"][0][0] += 1
    structural = load_bonsai_capture(CanonicalCaptureInput(**changed), plane=_plane())
    assert structural.structural_fingerprint != original.structural_fingerprint


def test_duplicate_or_object_only_capture_is_refused():
    """An ordinary Blender mesh cannot claim IFC identity through its name."""
    data = capture("wall").to_dict()
    data["records"].append(dict(data["records"][0]))
    with pytest.raises(ValueError, match="identity"):
        load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    data["records"] = [{"id": "IfcWall_name", "status": "extracted"}]
    with pytest.raises(ValueError, match="identity"):
        load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())


def legacy_bindings(tmp_path, current):
    """Pin a real proxy OBJ and explicitly map two legacy owners to canonical sources."""
    import trimesh
    from hashlib import sha256
    from ..adapters.bonsai_live import LegacySourceBinding, geometry_digest
    proxy = trimesh.creation.box(extents=(2, 2, 3))
    proxy.apply_translation((1, 1, 1.5))
    path = tmp_path / "proxy.obj"
    path.write_text(proxy.export(file_type="obj"), encoding="utf-8")
    target = {"target_id": "proxy:pair", "mesh_id": "proxy-mesh:pair", "represented_source_ids": ["old-1", "old-2"],
              "owner_global_ids": {"old-1": "g1", "old-2": "g2"},
              "obj_ref": {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()},
              "generated_mesh_checks": {"vertex_count": 8, "triangle_count": 12}, "representation_identifier": "GeneratedProxy"}
    scope = {"target": target, "scope_binding": {"source_revision": "historical-source", "frame_id": "historical-frame",
             "request_id": "historical-request", "candidate_identity": "historical-candidate", "acknowledged_conflicts": []},
             "applicability": {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]},
                               "frame": {"kind": "world_xy", "units": "m"},
                               "operation": "free_space", "query": {"kind": "whole_height_projection"}}}
    owners = ("ifc-object:g1", "ifc-object:g2")
    return tuple(LegacySourceBinding(f"old-{step}", step, f"g{step}", "project", "source", f"ifc-object:g{step}",
        source.geometry_refs, geometry_digest(current.scene, source), scope, owners)
        for step, source in enumerate(current.scene.source_objects, 1))


def test_legacy_proxy_validates_exact_owner_coverage(tmp_path):
    """Validated identity remains pending until an exact request-scoped match activates it."""
    from ..features.analysis_requests import execute_analysis_request
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = legacy_bindings(tmp_path, current)
    result = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings)
    scene = replace(result.scene, analysis_domain=_scene().analysis_domain,
                    geometries=result.scene.geometries + _scene().geometries)
    bypass = execute_analysis_request(scene, _request(scene))
    assert bypass.field.evaluate((1, 1), bypass.query).value is None
    assert bypass.field.evaluate((0, 0), bypass.query).value is None
    from ..adapters.blender_analysis_session import execute_live_analysis
    run = execute_live_analysis(result.scene, request=_request(scene), domain_geometries=_scene().geometries)
    assert run.field.evaluate((1, 1), run.query).value is True
    assert run.field.evaluate((1, 1), run.query).source_ids == ("ifc-object:g1", "ifc-object:g2")
    assert len([source for source in result.scene.source_objects if source.source_role == "analysis_substitute"]) == 1
    assert all(row["status"] == "pending_scope_validation" for row in result.diagnostics)
    assert result.scene.analysis_domain is None
    assert result.identity_map["old-1"]["canonical_object_id"] == "ifc-object:g1"


@pytest.mark.parametrize("failure", ["digest", "project", "step", "guid", "refs", "scope", "coverage", "missing_owner", "proxy"])
def test_required_proxy_refusal_never_restores_raw_owner(tmp_path, failure):
    """Failed identity, scope, geometry or proxy validation keeps owners globally unresolved."""
    from ..features.analysis_requests import execute_analysis_request
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = list(legacy_bindings(tmp_path, current))
    changes = {"digest": {"geometry_digest": "stale"}, "project": {"project_global_id": "other"},
               "step": {"legacy_step_id": 99}, "guid": {"global_id": "other"}, "refs": {"geometry_refs": ("wrong",)},
               "scope": {"scope": {}}, "coverage": {"covered_owner_ids": ("ifc-object:g1",)}}
    if failure in changes:
        bindings[0] = replace(bindings[0], **changes[failure])
    elif failure == "proxy":
        (tmp_path / "proxy.obj").write_text("changed", encoding="utf-8")
    else:
        bindings.pop()
    result = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings)
    scene = replace(result.scene, analysis_domain=_scene().analysis_domain, geometries=result.scene.geometries + _scene().geometries)
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((0, 0), run.query).value is None
    assert {"ifc-object:g1", "ifc-object:g2"} <= set(run.snapshot.provenance["unknown_source_ids"])
    assert all(not source.geometry_refs for source in result.scene.source_objects)
    assert all(row["status"] == "rejected_unresolved" for row in result.diagnostics)


def test_unverified_capture_or_role_spoof_cannot_erase_physical_mass():
    """Completeness and native class facts outrank caller-authored role labels."""
    data = capture("furniture").to_dict()
    data["records"][0]["role"] = "space"
    result = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert result.scene.source_objects[0].source_role == "furniture"
    data["capture_complete"] = False
    with pytest.raises(ValueError, match="complete"):
        load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())


def test_invalid_mesh_retains_unresolved_canonical_source():
    """Malformed or unnormalized mesh facts cannot become apparently usable geometry."""
    data = capture("wall").to_dict()
    data["records"][0]["mesh"]["triangle_indices"] = [[0, 1, 999]]
    result = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert result.scene.source_objects[0].geometry_refs == ()
    assert result.scene.source_objects[0].uncertainties[0].code == "missing_geometry"
    data["records"][0]["mesh"]["units"] = "mm"
    result = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert not result.scene.geometries


def test_legacy_duplicate_identity_and_missing_required_owner_are_refused(tmp_path):
    """Ambiguous bridges or disappearing required owners cannot silently reduce inventory."""
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = legacy_bindings(tmp_path, current)
    with pytest.raises(ValueError, match="ambiguous"):
        load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings + bindings[:1])
    data = raw.to_dict()
    data["records"].pop()
    with pytest.raises(ValueError, match="required.*missing"):
        load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane(), legacy_bindings=bindings)


def test_canonical_opening_hosts_fillings_and_geometry_remain_structural():
    """Canonical capture cannot drop authored opening veto facts from structural B4."""
    data = capture("wall", "door", "opening").to_dict()
    data["records"][2]["ifc_class"] = "IfcOpeningElement"
    data["records"][2]["opening_facts"] = {"host_source_ids": ["g1"], "filling_source_ids": ["g2"]}
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    opening = live.scene.openings[0]
    assert opening.id == "ifc-opening:g3" and opening.source_id == "g3"
    assert opening.host_refs == ("ifc-object:g1",)
    assert live.scene.source_objects[1].opening_refs == ("ifc-opening:g3",)
    assert live.structural_scene.openings[0] is opening
    assert next(mesh for mesh in live.structural_scene.geometries if mesh.id == "ifc-mesh:g3") is live.scene.geometries[2]
    data["records"][2]["opening_facts"]["host_source_ids"] = ["g2"]
    drift = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert live.structural_fingerprint != drift.structural_fingerprint


def test_nonmass_inventory_does_not_make_free_cells_unknown():
    """Spatial containers and grids remain inventoried without becoming physical mass."""
    from .test_analysis_requests import _scene, _request
    from ..features.analysis_requests import execute_analysis_request
    data = capture(*(["furniture"] * 4)).to_dict()
    for row, cls in zip(data["records"], ("IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcGrid")):
        row.update(ifc_class=cls, mesh=None, status="missing_geometry")
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert len(live.scene.source_objects) == 4
    scene = replace(live.scene, analysis_domain=_scene().analysis_domain, geometries=_scene().geometries)
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((2, 2), run.query).value is False
    assert not run.snapshot.provenance["unknown_source_ids"]
    data["records"][0]["ifc_class"] = "IfcAnnotation"
    ambiguous = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    scene = replace(ambiguous.scene, analysis_domain=scene.analysis_domain, geometries=scene.geometries)
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((2, 2), run.query).value is None


@pytest.mark.parametrize("invalid", [False, True])
def test_verified_native_camera_is_nonmass_but_retains_source_identity(invalid):
    """A qualified drawing camera is not missing physical mass; other annotations remain unknown."""
    from ..adapters.bonsai_analysis_plane import CameraBinding
    from .test_analysis_requests import _scene, _request
    from ..features.analysis_requests import execute_analysis_request
    data = capture("furniture").to_dict()
    row = data["records"][0]
    row.update(ifc_class="IfcAnnotation", mesh=None, status="native_drawing_camera",
        native_camera=CameraBinding(camera_id="ifc:g1", role="geometry_author", origin=(0, 0, 1.6),
            basis=_plane().basis, display={}, provenance={"project_global_id": "wrong" if invalid else "project",
                "source_ifc_global_id": "g1", "geometry_author_qualified": True}).to_dict())
    if invalid:
        with pytest.raises(ValueError, match="native drawing camera"):
            load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
        return
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert live.scene.source_objects[0].id == "ifc-object:g1"
    assert live.scene.source_objects[0].source_role == "drawing_camera"
    scene = replace(live.scene, analysis_domain=_scene().analysis_domain, geometries=_scene().geometries)
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((2, 2), run.query).value is False
    assert not run.snapshot.provenance["unknown_source_ids"]


def test_explicit_owned_display_inventory_is_audit_only():
    """Only authoritatively tagged analyzer display records leave computational inventory."""
    data = capture("furniture").to_dict()
    row = data["records"][0]
    row.update(ifc_class="IfcAnnotation", mesh=None, status="display_only",
               display_ownership={"om_analysis_owner": "order_analyzer", "om_analysis_role": "display_camera"})
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert not live.scene.source_objects and not live.scene.geometries
    assert live.diagnostics[0]["reason"] == "analyzer_owned_display_only"
    row["display_ownership"] = {}
    untagged = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert len(untagged.scene.source_objects) == 1


def test_full_fact_fingerprint_excludes_plane_display_and_runtime_tokens():
    """A renamed or recaptured unchanged source keeps its stable full identity."""
    first = load_bonsai_capture(capture(), plane=_plane())
    second = load_bonsai_capture(capture(), plane=_plane(name="renamed"))
    assert first.full_fingerprint == second.full_fingerprint
    assert first.capture_fingerprint == second.capture_fingerprint


def test_verified_ifc_subtype_enclosure_and_roles():
    """Real IFC4 ancestry retains subtype enclosure geometry and exact source classes."""
    from .test_blender_analysis_session import enclosed_scene
    from ..adapters.blender_analysis_session import evaluate_domain_request
    data = capture("wall", "wall", "wall", "wall").to_dict()
    walls = [mesh for mesh in enclosed_scene().geometries if mesh.id.startswith("mesh:")]
    for row, mesh in zip(data["records"], walls):
        row.update(ifc_class="IfcWallElementedCase", mesh=mesh.to_dict())
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    result = evaluate_domain_request(live.scene, context=live.structural_context, prior=None, action=None)
    assert result["source_count"] == 4 and len(result["candidates"]) == 1
    assert result["candidates"][0]["area_m2"] == pytest.approx(12.25)
    assert all(source.source_class == "IfcWallElementedCase" and source.source_role == "wall" for source in live.scene.source_objects)
    for cls, role in (("IfcColumnStandardCase", "column"), ("IfcDoorStandardCase", "door"), ("IfcWindowStandardCase", "window")):
        row = capture("furniture").to_dict()
        row["records"][0].update(ifc_class=cls, role="space")
        source = load_bonsai_capture(CanonicalCaptureInput(**row), plane=_plane()).structural_scene.source_objects[0]
        assert source.source_class == cls and source.source_role == role


def test_verified_opening_and_slab_subtypes():
    """Opening relations and explicit support use the same verified ancestry semantics."""
    from ..adapters.bonsai_live import SupportBinding, geometry_digest
    data = capture("furniture", "furniture", "slab").to_dict()
    data["records"][0].update(ifc_class="IfcOpeningStandardCase", opening_facts={"host_source_ids": ["g2"], "filling_source_ids": []})
    data["records"][1]["ifc_class"] = "IfcWallElementedCase"
    data["records"][2]["ifc_class"] = "IfcSlabStandardCase"
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert live.scene.openings[0].opening_kind == "IfcOpeningStandardCase"
    assert live.scene.openings[0].host_refs == ("ifc-object:g2",)
    slab = live.scene.source_objects[2]
    assert slab.source_role == "slab"
    binding = SupportBinding(slab.id, "project", "IfcSlabStandardCase", slab.geometry_refs,
        geometry_digest(live.scene, slab), live.capture_fingerprint, "explicit")
    supported = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane(), support_binding=binding)
    assert supported.domain_support_audit["status"] == "validated"
    assert supported.domain_support_audit["source_id"] == "g3"


def test_schema_ancestry_cannot_be_forged_by_a_caller():
    """Only installed schema ancestry can classify a capture's exact verified class."""
    data = capture("furniture").to_dict()
    data["records"][0].update(ifc_ancestry=["IfcWall"], role="wall")
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    assert not live.structural_scene.source_objects
    data["records"][0]["ifc_class"] = "IfcInventedWall"
    with pytest.raises(ValueError, match="class|schema"):
        load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())


@pytest.mark.parametrize("mutation", ["missing", "distant", "holes", "units", "frame", "operation", "query", "section_height"])
def test_legacy_proxy_scope_mismatch_never_activates_or_restores_raw(tmp_path, mutation):
    """Scope geometry/frame/operation/query is enforced at the actual request boundary."""
    from ..adapters.blender_analysis_capture import plain
    from ..adapters.blender_analysis_session import execute_live_analysis
    from ..features.analysis_requests import GeometryQuery, execute_analysis_request
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = legacy_bindings(tmp_path, current)
    scope = plain(bindings[0].scope)
    applicability = scope["applicability"]
    request_query = GeometryQuery()
    if mutation == "missing":
        scope.pop("applicability")
    elif mutation == "distant":
        applicability["geometry"]["coordinates"] = [[[100, 100], [101, 100], [101, 101], [100, 101], [100, 100]]]
    elif mutation == "holes":
        applicability["geometry"]["coordinates"].append([[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]])
    elif mutation in {"units", "frame"}:
        applicability["frame"]["units" if mutation == "units" else "kind"] = "mm" if mutation == "units" else "plane_local"
    elif mutation == "operation":
        applicability["operation"] = "physical_occupancy"
    elif mutation == "query":
        applicability["query"] = {"kind": "exact_world_xy_section", "world_z_m": 1.6}
    else:
        applicability["query"] = {"kind": "exact_world_xy_section", "world_z_m": 1.5}
        request_query = GeometryQuery("exact_world_xy_section", world_z_m=1.6)
    bindings = tuple(replace(binding, scope=scope) for binding in bindings)
    live = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings)
    domain_scene = replace(live.scene, analysis_domain=_scene().analysis_domain, geometries=live.scene.geometries + _scene().geometries)
    request = _request(domain_scene, geometry_query=request_query)
    for run in (execute_analysis_request(domain_scene, request),
                execute_live_analysis(live.scene, request=request, domain_geometries=_scene().geometries)):
        assert run.field.evaluate((1, 1), run.query).value is None
        assert run.field.evaluate((0, 0), run.query).value is None
        assert set(run.snapshot.provenance["unknown_source_ids"]) == {"ifc-object:g1", "ifc-object:g2"}
    assert all(not source.geometry_refs for source in live.scene.source_objects)


def test_legacy_scope_matching_section_and_historical_tokens_are_audit_only(tmp_path):
    """A matching world geometry/query activates without old/new consent-token equality."""
    from ..adapters.blender_analysis_capture import plain
    from ..adapters.blender_analysis_session import execute_live_analysis
    from ..features.analysis_requests import GeometryQuery
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = legacy_bindings(tmp_path, current)
    scope = plain(bindings[0].scope)
    scope["scope_binding"] = {key: "unrelated-audit-only" for key in ("source_revision", "frame_id", "request_id", "candidate_identity")}
    scope["applicability"]["query"] = {"kind": "exact_world_xy_section", "world_z_m": 1.6}
    bindings = tuple(replace(binding, scope=scope) for binding in bindings)
    live = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings)
    child = replace(live.scene, analysis_domain=_scene().analysis_domain)
    request = _request(child, geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6))
    run = execute_live_analysis(live.scene, request=request, domain_geometries=_scene().geometries)
    assert run.field.evaluate((1, 1), run.query).value is True
    assert run.field.evaluate((1, 1), run.query).source_ids == ("ifc-object:g1", "ifc-object:g2")
    assert all(not source.geometry_refs for source in live.scene.source_objects)
    assert live.scene.analysis_domain is None


def test_legacy_applicability_is_immutable_and_uses_actual_domain_mesh(tmp_path):
    """Frozen declarations cannot drift, and display outline cannot replace actual domain geometry."""
    from ..adapters.blender_analysis_session import execute_live_analysis
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    bindings = legacy_bindings(tmp_path, current)
    with pytest.raises(TypeError):
        bindings[0].scope["applicability"]["geometry"]["coordinates"][0][0][0] = 100
    live = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=bindings)
    proxy = next(source for source in live.scene.source_objects if source.source_role == "analysis_substitute")
    with pytest.raises(TypeError):
        proxy.factual_properties["pending_legacy_occupancy"]["scope"]["applicability"]["operation"] = "physical_occupancy"
    distant = _scene(origin=(100, 100))
    domain = replace(distant.analysis_domain, provenance={"outline": {"type": "Polygon", "coordinates": [[[0,0],[4,0],[4,4],[0,4],[0,0]]]}})
    request = _request(replace(live.scene, analysis_domain=domain))
    run = execute_live_analysis(live.scene, request=request, domain_geometries=distant.geometries)
    assert set(run.snapshot.provenance["unknown_source_ids"]) == {"ifc-object:g1", "ifc-object:g2"}
    assert not any(item.get("selected_source_id") == "proxy:pair" for item in run.snapshot.provenance["physical_source_inventory"])


@pytest.mark.parametrize("changed", ["owner", "proxy"])
def test_pending_proxy_revalidates_exact_geometry_at_activation(tmp_path, changed):
    """Replacing same-ID mesh bytes after qualification cannot activate a pending representation."""
    from ..adapters.blender_analysis_session import execute_live_analysis
    from .test_analysis_requests import _scene, _request
    raw = capture("furniture", "furniture")
    current = load_bonsai_capture(raw, plane=_plane())
    live = load_bonsai_capture(raw, plane=_plane(), legacy_bindings=legacy_bindings(tmp_path, current))
    identifier = "ifc-mesh:g1" if changed == "owner" else "proxy-mesh:pair"
    scene = replace(live.scene, geometries=tuple(replace(mesh, vertices=tuple((x + .125, y, z) for x, y, z in mesh.vertices))
        if mesh.id == identifier else mesh for mesh in live.scene.geometries))
    request = _request(replace(scene, analysis_domain=_scene().analysis_domain))
    run = execute_live_analysis(scene, request=request, domain_geometries=_scene().geometries)
    assert run.field.evaluate((0, 0), run.query).value is None
    assert run.field.evaluate((1, 1), run.query).value is None

