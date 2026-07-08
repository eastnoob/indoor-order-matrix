from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .affordance.profiles import resolve_affordance_profile


def bake_svg_affordance_metadata(source: str | Path, target: str | Path) -> None:
    """Write profile-derived SVG affordance metadata for fixture convenience."""
    tree = ET.parse(source)
    root = tree.getroot()
    for element in root.iter():
        role = element.attrib.get("data-role") or _role_from_id(element.attrib.get("id", ""))
        if not role or _has_affordance_metadata(element):
            continue
        profile = resolve_affordance_profile(f"{role}.default")
        for edge in profile.usable_edges:
            depth = profile.depth_for(edge)
            if depth > 0:
                # The baker stores local furniture intent. The inference layer
                # later maps front to scene side using the object's orientation.
                element.attrib[f"data-affordance-{edge}"] = _format_depth(depth)
    tree.write(target, encoding="unicode")


def _has_affordance_metadata(element: ET.Element) -> bool:
    """Return whether an SVG element already carries authored affordance values."""
    return any(key.startswith("data-affordance-") for key in element.attrib)


def _role_from_id(record_id: str) -> str:
    """Infer fixture roles from id text for SVGs without data-role attributes."""
    lowered = record_id.lower()
    for role in ("armchair", "chair", "sofa", "table", "podium"):
        if role in lowered:
            return role
    return ""


def _format_depth(depth: float) -> str:
    """Serialize numeric SVG metadata without noisy trailing decimals."""
    return str(int(depth)) if float(depth).is_integer() else str(round(depth, 4))
