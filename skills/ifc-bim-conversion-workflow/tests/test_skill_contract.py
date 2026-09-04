"""Contract checks for the reusable IFC/BIM conversion workflow skill."""

from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]


def test_skill_and_reference_contract_exists() -> None:
    """Require the skill package and its three routed references."""
    required = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references" / "ifc-standard-links.md",
        SKILL_ROOT / "references" / "bonsai-workflow-links.md",
        SKILL_ROOT / "references" / "software-preflight.md",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    assert not missing, f"missing skill contract files: {missing}"


def test_skill_contains_import_gates_and_phase_boundaries() -> None:
    """Require the decisions that prevent unsafe or unverifiable imports."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    required_phrases = (
        "independently runnable",
        "never silently invokes the next phase",
        "validation failure blocks import",
        "manual",
        "automatic",
        "explicit confirmation",
        "geometry-only",
        "not BIM",
        "discover and reuse",
        "IfcStore",
        "non-zero",
        "ifc_definition_id",
        "read-only",
        "not_available",
        "inspect_ifc.py",
        "validate_ifc.py",
        "verify_bonsai_mapping.py",
        "live MCP verification is session-specific",
        "logical furniture object",
        "global coordinate quadrant",
        "confidence",
        "ask the user to confirm",
        "REQUIRED SUB-SKILL",
        "bim-logical-object-mapping",
        "type_families",
        "geometry_reuse",
    )
    missing = [phrase for phrase in required_phrases if phrase.lower() not in text.lower()]
    assert not missing, f"missing skill contract phrases: {missing}"


def test_skill_describes_actionable_phases_and_importer_boundary() -> None:
    """Require the workflow boundaries for standalone work and mutation safety."""
    text = " ".join((SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower().split())
    required_phrases = (
        "independently actionable",
        "independently reportable",
        "standalone scripts",
        "preprocessing",
        "adapter or user-controlled",
        "does not itself invoke an importer",
        "validation failure or not_available blocks the import step",
        "before any mutation adapter can be called",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"missing phase/importer boundary phrases: {missing}"


def test_skill_defines_optional_output_directory_contract() -> None:
    """Require predictable output defaults without coupling output to import."""
    text = " ".join((SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower().split())
    required_phrases = (
        "output directory is optional",
        "outputs/<model-name>/",
        "do not overwrite existing results",
        "output directory and import target are separate",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"missing output-directory contract phrases: {missing}"


def test_skill_defines_nested_group_boundary_contract() -> None:
    """Prevent nested groups and reusable blocks from becoming false furniture."""
    text = " ".join((SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower().split())
    required_phrases = (
        "strong evidence, not an absolute semantic boundary",
        "object-group relationship graph",
        "not a semantic tree",
        "group names are labels, not identity",
        "source object ids and group ids",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"missing nested-group contract phrases: {missing}"


def test_skill_description_and_source_decision_table_contract() -> None:
    """Require the agent-oriented description and compact source selection table."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    first_line = next(line for line in text.splitlines() if line.startswith("description:"))
    assert first_line.startswith("description: Use when the agent")
    assert "| Source |" in text
    for source in ("Rhino", "Blender", "Other"):
        assert source in text
    for decision in ("native IFC exporter", "IfcOpenShell", "existing project adapter"):
        assert decision in text


def test_documented_commands_point_to_existing_scripts() -> None:
    """Keep every documented command executable from the repository root."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    for script in ("inspect_ifc.py", "validate_ifc.py", "verify_bonsai_mapping.py"):
        assert (SKILL_ROOT / "scripts" / script).is_file()
        assert f"scripts/{script}" in text


def test_references_use_approved_primary_links() -> None:
    """Require the primary documentation links named by the approved design."""
    reference_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SKILL_ROOT / "references").glob("*.md")
    )
    required_links = (
        "https://ifc43-docs.standards.buildingsmart.org/",
        "https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html",
        "https://docs.bonsaibim.org/",
        "https://docs.bonsaibim.org/reference/general/topbar.html",
        "https://www.blender.org/lab/mcp-server/",
    )
    missing = [link for link in required_links if link not in reference_text]
    assert not missing, f"missing approved reference links: {missing}"
