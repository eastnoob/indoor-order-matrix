"""Retained publication binds the exact source, targets and visible fragments."""

import json
from xml.etree import ElementTree as ET

import pytest

from .test_blender_analysis_session import _compact_document
from scripts.design.space_field import run_free_space_evidence_package as runner


def test_retained_publication_preserves_source_and_historical_status(tmp_path):
    """Publishing reuses exact saved readings and never asserts live freshness."""
    _, document = _compact_document()
    source = tmp_path / "source.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    ref = runner.ResultRef(document["kind"], document["result_id"], document["digest"])
    context = runner.ResultReadContext(expected={"plane_uuid": document["plane_uuid"]}, allow_historical=True)
    receipt = runner.publish_saved_free_space_result(source, ref, context, tmp_path / "published")
    output = json.loads((tmp_path / "published/free_space_package_output.json").read_text())
    manifest = json.loads((tmp_path / "published/visualization_manifest.json").read_text())
    status = json.loads((tmp_path / "published/package_status.json").read_text())
    assert len(output["outputs"]) == len(document["cells"]) == receipt["target_count"]
    assert {item["channel"] for item in output["outputs"]} == {"free_space"}
    assert output["source_envelopes"][0]["value"]["channels"][0]["observation"]["document"] == document
    assert status["freshness"] == "unavailable" and status["read_state"] == "historical"
    assert status["recompute_required"] is True
    assert receipt["geometry_recomputed"] is False
    assert {item["target_id"] for item in manifest["targets"]} == {item["target"]["identity"] for item in output["outputs"]}
    ET.parse(tmp_path / "published/free_space_plan.svg")
    assert runner.publish_saved_free_space_result(source, ref, context, tmp_path / "replay")["output_identity"] == receipt["output_identity"]


def test_publication_rejects_wrong_retained_identity_before_writing(tmp_path):
    """A supplied reference must authenticate bytes before an output is published."""
    _, document = _compact_document()
    source = tmp_path / "source.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    ref = runner.ResultRef(document["kind"], document["result_id"], "0" * 64)
    context = runner.ResultReadContext(expected={"plane_uuid": document["plane_uuid"]}, allow_historical=True)
    with pytest.raises(ValueError, match="ResultRef"):
        runner.publish_saved_free_space_result(source, ref, context, tmp_path / "published")
    assert not (tmp_path / "published").exists()
