"""Tests for the standalone IFC validation script."""

from __future__ import annotations

import builtins
import json
import shutil
import sys
import warnings
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import validate_ifc as validate_ifc_module
from validate_ifc import validate_ifc


@pytest.fixture
def valid_ifc_path() -> Path:
    """Return the repository's repaired IFC fixture."""
    path = Path(__file__).parents[3] / "test" / "output" / "4chair1table-bim-test.ifc"
    if not path.is_file():
        pytest.skip(f"valid IFC fixture is unavailable: {path}")
    return path


def test_valid_ifc_returns_passed(valid_ifc_path: Path) -> None:
    """Accept the repaired IFC when no validator errors are reported."""
    result = validate_ifc(valid_ifc_path)

    assert result["status"] == "passed"
    assert result["errors"] == []
    assert result["schema"] == "IFC4"


def test_duplicate_guid_fixture_returns_failed(valid_ifc_path: Path, tmp_path: Path) -> None:
    """Keep duplicate GlobalId validation errors as blocking failures."""
    import ifcopenshell

    invalid_path = tmp_path / "duplicate-guid.ifc"
    shutil.copyfile(valid_ifc_path, invalid_path)
    model = ifcopenshell.open(str(invalid_path))
    furniture = model.by_type("IfcFurniture")
    furniture[1].GlobalId = furniture[0].GlobalId
    model.write(str(invalid_path))

    result = validate_ifc(invalid_path)

    assert result["status"] == "failed"
    duplicate_errors = [item for item in result["errors"] if "GlobalId" in item["message"]]
    assert duplicate_errors
    metadata = duplicate_errors[0]["instance"]
    assert metadata["id"] == furniture[0].id()
    assert metadata["type"] == "IfcFurniture"
    assert metadata["global_id"] == furniture[0].GlobalId
    json.dumps(result)


def test_warning_only_validation_passes_with_advisory_reason(
    valid_ifc_path: Path, monkeypatch
) -> None:
    """Treat warning-only validator output as passed without a failure reason."""
    import ifcopenshell.validate

    def warning_validate(path, logger, **kwargs):
        """Emit one advisory statement for the status-semantics regression test."""
        logger.statements.append({"level": "warning", "message": "advisory only"})

    monkeypatch.setattr(ifcopenshell.validate, "validate", warning_validate)

    result = validate_ifc(valid_ifc_path)

    assert result["status"] == "passed"
    assert result["reason"] is None
    assert result["errors"] == []
    assert result["warnings"] == [{"level": "warning", "message": "advisory only"}]


def test_ifcopenshell_resource_warning_is_ignored_under_strict_warnings(
    valid_ifc_path: Path, monkeypatch
) -> None:
    """Ignore only the known IfcOpenShell ResourceWarning during validation."""
    import ifcopenshell.validate

    def warning_validate(path, logger, **kwargs):
        """Reproduce the EXPRESS loader warning with its third-party module identity."""
        warnings.warn_explicit(
            "unclosed file <_io.TextIOWrapper name='ifcopenshell/express/rules/IFC4.py' mode='r' encoding='utf-8'>",
            ResourceWarning,
            __file__,
            1,
            module="ifcopenshell.express.rule_executor",
        )

    monkeypatch.setattr(ifcopenshell.validate, "validate", warning_validate)

    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        result = validate_ifc(valid_ifc_path)

        with pytest.raises(ResourceWarning, match="unrelated IfcOpenShell resource"):
            warnings.warn(
                "unrelated IfcOpenShell resource",
                ResourceWarning,
                stacklevel=1,
            )

    assert result["status"] == "passed"


def test_unrelated_ifcopenshell_resource_warning_is_not_ignored(
    valid_ifc_path: Path, monkeypatch
) -> None:
    """Keep unrelated IfcOpenShell ResourceWarnings visible during validation."""
    import ifcopenshell.validate

    def warning_validate(path, logger, **kwargs):
        """Emit a ResourceWarning unrelated to the known rule-file leak."""
        warnings.warn_explicit(
            "unclosed file <_io.TextIOWrapper name='other.py' mode='r' encoding='utf-8'>",
            ResourceWarning,
            __file__,
            1,
            module="ifcopenshell.express.rule_executor",
        )

    monkeypatch.setattr(ifcopenshell.validate, "validate", warning_validate)

    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        result = validate_ifc(valid_ifc_path)
        assert result["status"] == "failed"
        assert "other.py" in result["reason"]

        with pytest.raises(ResourceWarning, match=r"unrelated IfcOpenShell resource"):
            warnings.warn("unrelated IfcOpenShell resource", ResourceWarning)


def test_validator_exception_returns_actionable_failure(
    valid_ifc_path: Path, monkeypatch
) -> None:
    """Expose validator exceptions as failed reports with the original cause."""
    import ifcopenshell.validate

    def failing_validate(path, logger, **kwargs):
        """Raise a representative validator failure."""
        raise RuntimeError("schema service unavailable")

    monkeypatch.setattr(ifcopenshell.validate, "validate", failing_validate)

    result = validate_ifc(valid_ifc_path)

    assert result["status"] == "failed"
    assert result["reason"] == "IFC validation failure: schema service unavailable"


@pytest.mark.parametrize(
    ("arguments", "expected_express_rules"),
    [
        (["validate_ifc.py", "model.ifc"], True),
        (["validate_ifc.py", "--no-express-rules", "model.ifc"], False),
    ],
)
def test_cli_prints_json_and_parses_express_rules(
    arguments: list[str], expected_express_rules: bool, monkeypatch, capsys
) -> None:
    """Parse CLI arguments and print the validator report as JSON."""
    observed = {}

    def fake_validate(path, express_rules=True):
        """Capture parsed CLI values and return a JSON-shaped report."""
        observed["path"] = path
        observed["express_rules"] = express_rules
        return {"status": "passed", "path": str(path), "express_rules": express_rules}

    monkeypatch.setattr(validate_ifc_module, "validate_ifc", fake_validate)
    monkeypatch.setattr(sys, "argv", arguments)

    validate_ifc_module.main()

    assert observed["path"] == Path("model.ifc")
    assert observed["express_rules"] is expected_express_rules
    assert json.loads(capsys.readouterr().out) == {
        "express_rules": expected_express_rules,
        "path": "model.ifc",
        "status": "passed",
    }


def test_validation_forwards_disabled_express_rules(valid_ifc_path: Path, monkeypatch) -> None:
    """Forward an explicitly disabled EXPRESS-rule flag to IfcOpenShell."""
    import ifcopenshell.validate

    observed = {}
    original_validate = ifcopenshell.validate.validate

    def recording_validate(path, logger, **kwargs):
        """Record validator options while retaining the real validation behavior."""
        observed.update(kwargs)
        return original_validate(path, logger, **kwargs)

    monkeypatch.setattr(ifcopenshell.validate, "validate", recording_validate)
    validate_ifc(valid_ifc_path, express_rules=False)

    assert observed["express_rules"] is False


def test_validation_preserves_source_bytes(valid_ifc_path: Path) -> None:
    """Keep validation read-only by preserving the source bytes exactly."""
    before = valid_ifc_path.read_bytes()

    validate_ifc(valid_ifc_path)

    assert valid_ifc_path.read_bytes() == before


def test_missing_file_is_not_available(tmp_path: Path) -> None:
    """Report a missing input distinctly from parser and validator failures."""
    result = validate_ifc(tmp_path / "missing.ifc")

    assert result["status"] == "not_available"
    assert result["reason"] == "IFC file does not exist"
    assert result["errors"] == []


def test_missing_ifcopenshell_is_explicitly_unavailable(monkeypatch, tmp_path: Path) -> None:
    """Report optional IfcOpenShell absence without pretending validation passed."""
    path = tmp_path / "model.ifc"
    path.write_text("ISO-10303-21;", encoding="ascii")
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        """Block only the optional IfcOpenShell import for this test."""
        if name == "ifcopenshell":
            raise ImportError("test: unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    result = validate_ifc(path)

    assert result["status"] == "not_available"
    assert result["reason"] == "ifcopenshell is not installed"


def test_unreadable_ifc_is_failed(tmp_path: Path) -> None:
    """Report malformed IFC input as a parsing failure."""
    path = tmp_path / "malformed.ifc"
    path.write_bytes(b"not an IFC file")

    result = validate_ifc(path)

    assert result["status"] == "failed"
    assert "parse" in result["reason"].lower()


def test_result_is_json_serializable(valid_ifc_path: Path) -> None:
    """Keep every report value safe for direct JSON encoding."""
    json.dumps(validate_ifc(valid_ifc_path))
