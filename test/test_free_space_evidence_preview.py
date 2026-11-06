"""Regression checks for the native preview's categorical evidence boundary."""

import pytest

from ..scripts.design.space_field.build_free_space_evidence_preview import category, prepare_preview


@pytest.mark.parametrize("status,value,expected", [
    ("established", False, "established_free"),
    ("established", True, "established_occupied"),
    ("conditional", False, "conditional_free"),
    ("conditional", True, "conditional_occupied"),
    ("unknown", None, "unknown"), ("outside", None, "outside"),
    ("invalid", None, "invalid"), ("not_available", None, "not_available"),
])
def test_preview_retains_six_states_and_boolean_direction(status, value, expected):
    """Unknown and conditional samples cannot acquire established-free color."""
    assert category({"status": status, "value": value}) == expected


@pytest.mark.parametrize("status,value", [("unknown", False), ("outside", True), ("established", None)])
def test_preview_rejects_conflicting_value_status(status, value):
    """Fail closed instead of visually reinterpreting malformed saved evidence."""
    with pytest.raises(ValueError, match="value/status"):
        category({"status": status, "value": value})


def test_preview_binds_exact_raw_cells_and_rejects_display_drift():
    """Authenticate actual fixture output, then reject changed values and fragment locators."""
    from copy import deepcopy
    from ..features.field_core import serialize_evidence_package_output
    from ..features.free_space_evidence_package import build_free_space_evidence_package, build_free_space_source_envelope
    from .test_blender_analysis_session import _compact_document

    _, document = _compact_document()
    package = serialize_evidence_package_output(build_free_space_evidence_package().evaluate(
        (build_free_space_source_envelope(document),)))
    manifest = {"output_identity": package["output_identity"], "channel": "free_space",
                "source_result_ref": {key: document[key] for key in ("kind", "result_id", "digest")},
                "freshness_scope": "historical retained result; live scene not observed", "targets": []}
    for output in package["outputs"]:
        locator = output["observation"]["cell_locator"]
        manifest["targets"].append({"target_id": output["target"]["identity"],
            **{key: locator[key] for key in ("row", "column", "cell_index")},
            "fragment_indices": [index for index, fragment in enumerate(document["display_fragments"])
                                 if fragment["cell_index"] == locator["cell_index"]]})
    retained, counts, depicted = prepare_preview(package, manifest)
    assert retained == document and sum(counts.values()) == len(document["cells"])
    assert sum(depicted.values()) == len({fragment["cell_index"] for fragment in document["display_fragments"]})
    changed = deepcopy(package)
    changed["outputs"][0]["observation"]["value"] = "free"
    with pytest.raises(ValueError, match="differs from raw"):
        prepare_preview(changed, manifest)
    changed_manifest = deepcopy(manifest)
    changed_manifest["targets"][0]["fragment_indices"] = [-1]
    with pytest.raises(ValueError, match="differs from raw"):
        prepare_preview(package, changed_manifest)
