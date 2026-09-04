"""Read-only, JSON-safe validation of an IFC file."""

from __future__ import annotations

import argparse
import json
import warnings
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _version(ifcopenshell: Any) -> str | None:
    """Return the installed IfcOpenShell version when exposed by the module."""
    value = getattr(ifcopenshell, "version", None)
    return value if isinstance(value, str) else None


def _json_safe(value: Any) -> object:
    """Recursively convert logger values into JSON-safe primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    # Preserve the useful identity of IfcOpenShell entities without serializing the entity object.
    entity: dict[str, object] = {}
    entity_id = getattr(value, "id", None)
    if callable(entity_id):
        try:
            entity["id"] = entity_id()
        except Exception:
            pass
    entity_type = getattr(value, "is_a", None)
    if callable(entity_type):
        try:
            entity["type"] = entity_type()
        except Exception:
            pass
    global_id = getattr(value, "GlobalId", None)
    if global_id is not None:
        entity["global_id"] = str(global_id)
    return entity or str(value)


def _statement(level: str, statement: Any) -> dict[str, object]:
    """Convert an IfcOpenShell logger statement into JSON-safe fields."""
    if isinstance(statement, Mapping):
        result = {str(key): _json_safe(value) for key, value in statement.items()}
        result["message"] = str(statement.get("message", statement))
        result["level"] = level
        return result
    return {"level": level, "message": str(statement)}


def _report(path: Path) -> dict[str, object]:
    """Create the stable empty report returned before parsing starts."""
    return {
        "status": "not_available",
        "path": str(path),
        "schema": None,
        "validator_version": None,
        "errors": [],
        "warnings": [],
        "counts": {},
        "reason": None,
    }


def _has_step_envelope(path: Path) -> bool:
    """Check the required STEP header and closing marker before parsing."""
    with path.open("rb") as stream:
        content = stream.read()
    return content.startswith(b"ISO-10303-21;") and content.rstrip().endswith(
        b"END-ISO-10303-21;"
    )


def validate_ifc(path: Path, express_rules: bool = True) -> dict[str, object]:
    """Validate an IFC path without modifying the source file or model."""
    path = Path(path)
    result = _report(path)
    if not path.is_file():
        result["reason"] = "IFC file does not exist"
        return result

    try:
        import ifcopenshell
        import ifcopenshell.validate
    except ImportError:
        result["reason"] = "ifcopenshell is not installed"
        return result

    result["validator_version"] = _version(ifcopenshell)
    try:
        if not _has_step_envelope(path):
            raise ValueError("missing ISO-10303-21 header or END-ISO-10303-21 marker")
        model = ifcopenshell.open(str(path), readonly=True)
    except OSError as exc:
        result.update({"status": "failed", "reason": f"IFC file unreadable: {exc}"})
        return result
    except (ValueError, RuntimeError, ifcopenshell.Error) as exc:
        result.update({"status": "failed", "reason": f"IFC parse failure: {exc}"})
        return result

    result.update(
        {
            "schema": model.schema,
            "counts": dict(Counter(entity.is_a() for entity in model)),
        }
    )
    logger = ifcopenshell.validate.json_logger()
    try:
        with warnings.catch_warnings():
            # IfcOpenShell 0.8.5's EXPRESS rule loader leaks this third-party warning during validation.
            warnings.filterwarnings(
                "ignore",
                category=ResourceWarning,
                module=r"^ifcopenshell\.express\.rule_executor$",
                message=r"^unclosed file .*ifcopenshell[\\/]express[\\/]rules[\\/].*\.py.*$",
            )
            ifcopenshell.validate.validate(str(path), logger, express_rules=express_rules)
    except Exception as exc:
        result.update({"status": "failed", "reason": f"IFC validation failure: {exc}"})
        return result

    errors = [_statement("error", item) for item in logger.statements if item.get("level") == "error"]
    warning_items = [
        _statement("warning", item)
        for item in logger.statements
        if item.get("level") != "error"
    ]
    # Keep errors separate from warnings because validation errors block import and are not advisory.
    result["errors"] = errors
    result["warnings"] = warning_items
    result["status"] = "failed" if errors else "passed"
    result["reason"] = "IFC validation errors reported" if errors else None
    # The import gate must not downgrade validator failures merely because warnings are also present.
    return result


def main() -> None:
    """Parse CLI arguments and print the validation report as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to an IFC file")
    parser.add_argument(
        "--express-rules",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable EXPRESS rule validation (default: enabled)",
    )
    args = parser.parse_args()
    print(json.dumps(validate_ifc(args.path, express_rules=args.express_rules), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
