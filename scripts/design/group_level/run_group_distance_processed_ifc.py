"""Inspect an explicit pure-distance processed port over authenticated retained IFC evidence."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import html
from itertools import combinations
import json
from pathlib import Path
from typing import Any

from features.field_core import (
    EvidencePackageOutput, EvidenceProcessedOutput, serialize_evidence_package_output,
)
from features.group_distance_evidence_package import (
    SOURCE_CHANNEL, build_euclidean_median_proximity_processor, build_group_distance_evidence_package,
)
from features.package_analysis_context import resolve_package_analysis_context
from scripts.design.group_level import run_group_distance_decay_ifc as retained
from scripts.design.group_level.replay_evidence_package_readback import load_saved_evidence_package


ROOT = Path(__file__).resolve().parents[3]
LIMITS = ("Experimental scope-relative Euclidean proximity: changing scope can change all values. "
          "Freshness covers authenticated retained context only; live scene currentness was not observed. "
          "No physical attenuation or cross-scene calibration is claimed.")


def load_trial(*, bundle_path: Path = retained.BUNDLE_PATH, package_path: Path = retained.PACKAGE_PATH):
    """Reuse retained authentication, then process the actual distance producer publication."""
    inputs = retained.load_experiment_inputs(bundle_path=bundle_path, package_path=package_path)
    raw = load_saved_evidence_package(package_path, expected_sha256=retained.EXPECTED_HASHES["package"])
    if raw.package_id != "group-walk-distance" or inputs.package_freshness != "fresh":
        raise ValueError("the trial requires an authenticated fresh retained distance producer")
    scope = []
    pairs = set()
    sources = {source.target["identity"]: source for source in inputs.source_envelopes}
    raw_identity = raw.output_identity
    # Authentication/readback already checked the publication; index its addresses once for the join.
    raw_channels = {(item.target["identity"], item.channel): item for item in raw.outputs}
    for selected in inputs.outputs:
        if selected.channel != "euclidean_distance" or len(selected.derived_from) != 1:
            raise ValueError("retained selections must be exact Euclidean channel addresses")
        reference = selected.derived_from[0]
        original = raw_channels.get((reference.target_identity, reference.channel))
        if (reference.package_id != raw.package_id or reference.output_identity != raw_identity
                or reference.target_identity != selected.target["identity"] or reference.channel != selected.channel
                or original is None
                or original != replace(selected, derived_from=original.derived_from)):
            raise ValueError("producer raw values or addresses differ from authenticated selected readback")
        identity = original.target["identity"]
        observation = original.observation
        source = sources[identity]
        source_raw = next(record.observation for record in source.value["channels"]
                          if record.channel == SOURCE_CHANNEL)
        group_ids = tuple(observation["group_ids"])
        if (observation["pair_id"] != identity or group_ids != tuple(sorted(set(group_ids)))
                or len(group_ids) != 2 or tuple(source_raw["group_ids"]) != group_ids
                or observation["value"] != source_raw["center_to_center_euclidean"]["value"]
                or source.query != inputs.bundle.query
                or original.provenance.get("analysis_plane") != inputs.bundle.analysis_plane
                or original.provenance.get("query_context") != inputs.bundle.query_context):
            raise ValueError("producer Euclidean reading differs from retained pair/plane/query context")
        scope.append(identity)
        pairs.add(group_ids)
    expected_pairs = set(combinations(sorted(inputs.geometries), 2))
    if len(inputs.geometries) != 37 or len(scope) != len(set(scope)) or len(scope) != 666 or pairs != expected_pairs:
        raise ValueError("the trial requires all 666 unordered pairs of the 37 retained groups")
    # The readback consumer authenticates context; only its upstream producer is processed.
    package = build_group_distance_evidence_package(output_processor=
        build_euclidean_median_proximity_processor(expected_target_ids=scope))
    analysis_context = resolve_package_analysis_context(raw.source_envelopes)
    processed = package.process_output(raw, package_freshness=inputs.package_freshness,
                                       analysis_context=analysis_context)
    if processed.error_code is not None:
        raise ValueError(f"{processed.error_code}: {processed.explanation}")
    return inputs, raw, processed


def build_processed_rows(raw: EvidencePackageOutput, processed: EvidenceProcessedOutput) -> list[dict[str, Any]]:
    """Export actual processed observations beside their unchanged raw metre readings."""
    serialized = serialize_evidence_package_output(raw)
    if (processed.error_code is not None or processed.package_id != raw.package_id
            or processed.raw_output_identity != serialized["output_identity"]
            or processed.raw_payload_fingerprint != serialized["payload_fingerprint"]):
        raise ValueError("usable processed output must belong to the supplied raw producer")
    originals = {item.target["identity"]: item for item in raw.outputs if item.channel == "euclidean_distance"}
    rows = []
    for item in processed.outputs:
        original = originals[item.target["identity"]]
        group_a, group_b = original.observation["group_ids"]
        rows.append({"pair_id": item.target["identity"], "group_a_id": group_a, "group_b_id": group_b,
                     "distance_m": original.observation["value"], "proximity": item.observation,
                     "median_distance_m": item.provenance["median_distance_m"], "status": item.status.value,
                     "processed_channel": item.channel,
                     "raw_channel_ref": retained._plain_reference(next(
                         reference for reference in item.derived_from
                         if reference.target_identity == item.target["identity"])),
                     "lineage_scope": "all_euclidean_raw_channel_refs"})
    return rows


def _draw_union(axes, geometry, *, fill: Any, source: bool) -> None:
    """Draw the retained union with its holes intact and a separate source marker."""
    from matplotlib.path import Path as PlotPath
    from matplotlib.patches import PathPatch
    from shapely.geometry.polygon import orient

    polygons = tuple(geometry.geoms) if geometry.geom_type == "MultiPolygon" else (geometry,)
    for polygon in polygons:
        vertices, codes = [], []
        # Opposite ring winding retains physical union holes in the plan view.
        for ring in (orient(polygon, sign=1).exterior, *orient(polygon, sign=1).interiors):
            coordinates = list(ring.coords)
            vertices.extend(coordinates)
            codes.extend([PlotPath.MOVETO] + [PlotPath.LINETO] * (len(coordinates) - 2) + [PlotPath.CLOSEPOLY])
        axes.add_patch(PathPatch(PlotPath(vertices, codes), facecolor=fill,
                                 edgecolor="#d62728" if source else "#666666",
                                 linewidth=2 if source else 0.5, hatch="///" if source else None))


def _write_overview(inputs, rows: list[dict[str, Any]], output_dir: Path) -> None:
    """Show two source selections and all actual processed values on a fixed ruler."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    group_ids = sorted(inputs.geometries)
    figure, axes = plt.subplots(1, 3, figsize=(20, 8), constrained_layout=True,
                                gridspec_kw={"width_ratios": (1, 1, 0.7)})
    cmap = plt.get_cmap("cividis")
    for axis, source in zip(axes[:2], (group_ids[0], group_ids[-1])):
        selected = {row["group_b_id"] if row["group_a_id"] == source else row["group_a_id"]: row
                    for row in rows if source in (row["group_a_id"], row["group_b_id"])}
        for number, identity in enumerate(group_ids, 1):
            _draw_union(axis, inputs.geometries[identity],
                        fill="white" if identity == source else cmap(selected[identity]["proximity"]),
                        source=identity == source)
            center = inputs.geometries[identity].centroid
            axis.text(center.x, center.y, f"{number:02d}", fontsize=8, ha="center", va="center",
                      color="#c62828" if identity == source else "white",
                      bbox={"facecolor": "white" if identity == source else "#333333", "alpha": 0.8,
                            "pad": 1, "edgecolor": "none"})
        axis.autoscale_view()
        axis.margins(0.05)
        axis.set(aspect="equal", xlabel="Analysis-plane X (m)", ylabel="Analysis-plane Y (m)",
                 title=f"Source {group_ids.index(source) + 1:02d} (red hatch); 36 observed targets")
    figure.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap=cmap), ax=list(axes[:2]),
                    fraction=0.025, pad=0.02, label="Relative proximity [0,1]; larger is closer")
    axes[2].scatter([row["distance_m"] for row in rows], [row["proximity"] for row in rows],
                    c=[row["proximity"] for row in rows], cmap=cmap, vmin=0, vmax=1, s=13)
    axes[2].set(xlabel="Raw Euclidean distance (m)", ylabel="Processed relative proximity",
                title="Actual processed port: all 666 pairs", ylim=(0, 1))
    axes[2].grid(color="#dddddd", linewidth=0.5)
    figure.suptitle(f"Pure Euclidean trial: n=m/(m+d); common median m={rows[0]['median_distance_m']:.6f} m\n"
                   "Actual retained IFC unions; source is separate from observations", fontsize=12)
    figure.text(0.5, -0.025, LIMITS, ha="center", fontsize=9, wrap=True)
    figure.savefig(output_dir / "overview.png", dpi=160, bbox_inches="tight")
    figure.savefig(output_dir / "overview.svg", bbox_inches="tight")
    plt.close(figure)


def _write_viewer(inputs, rows: list[dict[str, Any]], output_dir: Path) -> None:
    """Render supplied observations without recalculating their processing formula."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_hex

    group_ids = sorted(inputs.geometries)
    cmap = plt.get_cmap("cividis")
    records = [{**row, "fill": to_hex(cmap(row["proximity"]))} for row in rows]
    bounds = [geometry.bounds for geometry in inputs.geometries.values()]
    min_x, min_y = min(item[0] for item in bounds), min(item[1] for item in bounds)
    max_x, max_y = max(item[2] for item in bounds), max(item[3] for item in bounds)
    paths = []
    for number, identity in enumerate(group_ids, 1):
        geometry = inputs.geometries[identity]
        polygons = tuple(geometry.geoms) if geometry.geom_type == "MultiPolygon" else (geometry,)
        commands = []
        for polygon in polygons:
            for ring in (polygon.exterior, *polygon.interiors):
                commands.append("M" + "L".join(f"{x},{-y}" for x, y in ring.coords) + "Z")
        center = geometry.centroid
        escaped = html.escape(identity, quote=True)
        paths.append(f'<g data-group="{escaped}" tabindex="0" role="button" aria-label="Select source {number:02d}">'
                     f'<path d="{" ".join(commands)}" fill-rule="evenodd" stroke="#555" stroke-width="0.025"/>'
                     f'<title></title><text x="{center.x}" y="{-center.y}" text-anchor="middle" '
                     f'dominant-baseline="middle" font-size="0.19" fill="white" stroke="#333" '
                     f'stroke-width=".04" paint-order="stroke" pointer-events="none">{number:02d}</text></g>')
    options = "".join(f'<option value="{html.escape(identity, quote=True)}">{number:02d} — {html.escape(identity)}</option>'
                      for number, identity in enumerate(group_ids, 1))
    table = "".join(f'<tr><td>{html.escape(row["pair_id"])}</td><td>{html.escape(row["group_a_id"])}</td>'
                    f'<td>{html.escape(row["group_b_id"])}</td><td>{row["distance_m"]:.12g}</td>'
                    f'<td>{row["proximity"]:.12g}</td></tr>' for row in rows)
    payload = json.dumps(records, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    document = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Pure Euclidean processed-port IFC trial</title>
<style>body{{font:15px system-ui;margin:24px;color:#222}}main{{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}}
svg{{width:100%;height:70vh;background:#f7f7f7}}g[role=button]{{cursor:pointer}}g:focus path{{stroke:#ed00ff;stroke-width:.09}}
table{{border-collapse:collapse;font-size:13px;width:100%}}td,th{{padding:5px;text-align:left;border-bottom:1px solid #ddd}}
.scroll{{max-height:65vh;overflow:auto}}.legend{{height:18px;background:linear-gradient(to right,#00224e,#575d6d,#a69b75,#fee838)}}
@media(max-width:900px){{main{{display:block}}}}</style>
<h1>Pure Euclidean relative proximity</h1><p>n=m/(m+d); m={rows[0]['median_distance_m']:.12g} m across all 666 pairs.
Larger means closer. Every source uses the same [0,1] ruler.</p><p>{html.escape(LIMITS)}</p>
<label for="source">Source group</label> <select id="source">{options}</select>
<p id="source-note"></p><main><section><svg viewBox="{min_x-0.4} {-max_y-0.4} {max_x-min_x+0.8} {max_y-min_y+0.8}"
aria-label="Retained actual IFC group unions"><defs><pattern id="source-hatch" patternUnits="userSpaceOnUse" width=".15" height=".15">
<rect width=".15" height=".15" fill="white"/><path d="M0,0L.15,.15" stroke="#d62728" stroke-width=".025"/>
</pattern></defs>{''.join(paths)}</svg><div class="legend"></div><p>0: far limit ← relative proximity → 1: zero distance.
Red hatch marks the selected source separately; there is no self-distance observation.</p></section>
<section><h2>36 selected targets</h2><div class="scroll"><table><thead><tr><th>Target</th><th>Raw metres</th>
<th>Processed [0,1]</th></tr></thead><tbody id="targets"></tbody></table></div></section></main>
<p><a href="pairs.csv">Complete 666-pair CSV</a> · <a href="pairs.json">JSON</a> · <a href="manifest.json">Lineage and identity manifest</a></p>
<details><summary>All 666 unordered pairs: raw metres beside processed proximity</summary><div class="scroll"><table>
<thead><tr><th>Pair address</th><th>Group A</th><th>Group B</th><th>Raw metres</th><th>Processed [0,1]</th></tr></thead>
<tbody>{table}</tbody></table></div></details><script id="rows" type="application/json">{payload}</script>
<script>
const rows=JSON.parse(document.getElementById('rows').textContent), selector=document.getElementById('source');
/** Paint only supplied processed observations for the selected source. */
function render(){{
 const source=selector.value, selected=rows.filter(row=>row.group_a_id===source||row.group_b_id===source);
 const byTarget=new Map(selected.map(row=>[row.group_a_id===source?row.group_b_id:row.group_a_id,row]));
 document.querySelectorAll('[data-group]').forEach(group=>{{
  const identity=group.dataset.group, row=byTarget.get(identity), path=group.querySelector('path');
  path.setAttribute('fill',identity===source?'url(#source-hatch)':row.fill);
  path.setAttribute('stroke',identity===source?'#d62728':'#555');
  group.querySelector('title').textContent=identity===source?'Source; no self observation':
   identity+' | '+row.distance_m+' m | proximity '+row.proximity+' | '+row.pair_id;
 }});
 const body=document.getElementById('targets'); body.replaceChildren();
 [...byTarget].sort((a,b)=>a[1].distance_m-b[1].distance_m).forEach(([identity,row])=>{{
  const tr=document.createElement('tr');
  [identity,row.distance_m.toPrecision(12),row.proximity.toPrecision(12)].forEach(value=>{{
   const td=document.createElement('td');td.textContent=value;tr.append(td);
  }});body.append(tr);
 }});
 document.getElementById('source-note').textContent='Source '+source+'; '+selected.length+' observed targets; common median unchanged.';
}}
selector.addEventListener('change',render);
document.querySelectorAll('[data-group]').forEach(group=>{{
 /** Select a real group as the source without adding a self observation. */
 function select(){{selector.value=group.dataset.group;render();}}
 group.addEventListener('click',select);group.addEventListener('keydown',event=>{{
  if(event.key==='Enter'||event.key===' '){{event.preventDefault();select();}}
 }});
}});render();
</script></html>'''
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def run_trial(output_dir: Path) -> dict[str, Any]:
    """Write a new trial directory while preserving all prior outputs and raw caches."""
    inputs, raw, processed = load_trial()
    rows = build_processed_rows(raw, processed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "pairs.json").write_text(json.dumps(rows, indent=2, allow_nan=False), encoding="utf-8")
    with (output_dir / "pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows({**row, "raw_channel_ref": json.dumps(row["raw_channel_ref"])} for row in rows)
    _write_overview(inputs, rows, output_dir)
    _write_viewer(inputs, rows, output_dir)
    # This trial-local manifest stores the shared complete lineage once, without a persistence schema change.
    manifest = {
        "trial": "euclidean-median-relative-proximity/1", "limits": LIMITS,
        "group_count": 37, "pair_count": len(rows), "raw_package_id": raw.package_id,
        "raw_output_identity": processed.raw_output_identity,
        "raw_payload_fingerprint": processed.raw_payload_fingerprint,
        "processing_identity": processed.processing_identity,
        "processor_id": processed.processor_id, "processor_version": processed.processor_version,
        "parameters": retained._json_safe(processed.parameters),
        "median_distance_m": rows[0]["median_distance_m"], "retained_context_freshness": inputs.package_freshness,
        "input_hashes": dict(inputs.input_hashes), "source_binding": retained._json_safe(inputs.source_binding),
        "all_euclidean_raw_channel_refs": [retained._plain_reference(ref) for ref in processed.outputs[0].derived_from],
        "scale": {"range": [0, 1], "meaning": processed.outputs[0].scale.meaning,
                  "normalization_method": processed.outputs[0].scale.normalization_method},
        "artifacts": {name: retained.file_hash(output_dir / name) for name in
                      ("pairs.json", "pairs.csv", "overview.png", "overview.svg", "index.html")},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    return manifest


def main() -> None:
    """Run the bounded retained trial through the project's Pixi environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/design/group_distance_processed_ifc/run_20261112_median_v1")
    args = parser.parse_args()
    manifest = run_trial(args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "pair_count": manifest["pair_count"],
                      "median_distance_m": manifest["median_distance_m"],
                      "processing_identity": manifest["processing_identity"]}))


if __name__ == "__main__":
    main()
