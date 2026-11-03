"""Render recorded distances and routes only; never calculate or infer a route."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from html import escape
import json
from pathlib import Path

from scripts.design.group_level.run_group_distance_ifc import domain_candidate_id, file_hash, read_json, write_json


def polygon_markup(components: list, color: str, opacity: float, stroke: str = "none") -> str:
    """Draw recorded exterior and hole rings with SVG's even-odd fill rule."""
    markup = []
    for component in components or ():
        path = " ".join("M " + " L ".join(f"{x:.7f},{-y:.7f}" for x, y in ring) + " Z"
                        for ring in (component["exterior"], *component.get("holes", ())) if ring)
        markup.append(f'<path d="{path}" fill="{color}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width=".018" fill-rule="evenodd"/>')
    return "".join(markup)


def view_bounds(geometry: dict) -> list:
    """Frame all supplied group and confirmed-domain rings."""
    points = [point for record in [geometry["domain"], *geometry["groups"]]
              for component in record.get("components") or () for point in component["exterior"]]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    return [xmin - .4, -ymax - .4, xmax - xmin + .8, ymax - ymin + .8]


def base_svg(geometry: dict, manifest: dict, aliases: dict) -> str:
    """Draw same-view occupancy, unknown samples, domain rings and authored group IDs."""
    candidate = escape(domain_candidate_id(geometry["domain"]))
    layers = [polygon_markup(geometry["domain"]["components"], "#eaf6ea", 1, "#238543")]
    for record in geometry["physical_occupancy"]:
        layers.append(polygon_markup(record["geometry_components"], "#475569", .48))
    layers.append(polygon_markup(geometry["domain"]["components"], "none", 1, "#238543"))
    domain_points = [p for component in geometry["domain"]["components"] for p in component["exterior"]]
    layers.append(f'<text x="{min(p[0] for p in domain_points)+.12}" y="{-max(p[1] for p in domain_points)+.3}" font-size=".22" fill="#166534">{candidate} confirmed domain</text>')
    grid = manifest["grid"]
    spacing = grid["spacing"]
    for sample in manifest["cell_samples"]:
        if sample["status"] not in {"unknown", "invalid", "not_available", "conditional"}:
            continue
        color = "#f59e0b" if sample["status"] == "unknown" else "#a855f7" if sample["status"] == "conditional" else "#e11d48"
        x, y = sample["center"]
        layers.append(f'<rect x="{x-spacing/2:.7f}" y="{-y-spacing/2:.7f}" width="{spacing}" height="{spacing}" fill="{color}" opacity=".28"><title>{escape(sample["status"])}</title></rect>')
    for group in geometry["groups"]:
        layers.append(f'<g><title>{escape(group["group_id"])}</title>' + polygon_markup(group.get("components"), "#0891b2", .10, "#0e7490") + "</g>")
        points = [point for component in group.get("components") or () for point in component["exterior"]]
        if points:
            # Label placement is display-only; metric centroids come exclusively from observations.
            x, y = points[0]
            layers.append(f'<text x="{x:.7f}" y="{-y:.7f}" font-size=".17" fill="#0c4a6e">{aliases[group["group_id"]]}</text>')
    return '<g id="base">' + "".join(layers) + "</g>"


def display_value(reading: dict) -> str:
    """Keep null values visibly unavailable instead of formatting them as zero."""
    return "—" if reading["value"] is None else f'{reading["value"]:.5f}'


def html_document(manifest: dict, observations: list, geometry: dict, aliases: dict, base: str) -> str:
    """Create one indexed route locator per pair and complete metric tables."""
    rows = []
    options = []
    for observation in observations:
        identity = observation["pair_id"]
        a, b = observation["group_ids"]
        euclidean, hybrid = observation["center_to_center_euclidean"], observation["centroid_free_space_hybrid"]
        label = f'{aliases[a]} ↔ {aliases[b]} · {hybrid["status"]}'
        options.append(f'<option value="{identity}">{escape(label)}</option>')
        rows.append(f'<tr id="row-{identity}"><td><a href="#{identity}">{escape(label)}</a></td><td>{display_value(euclidean)}</td><td>{display_value(hybrid)}</td><td>{escape(hybrid["status"])}</td></tr>')
    by_pair = {tuple(item["group_ids"]): item for item in observations}
    ids = manifest["group_ids"]
    matrices = []
    for channel in ("center_to_center_euclidean", "centroid_free_space_hybrid"):
        matrix_rows = []
        for a in ids:
            cells = []
            for b in ids:
                item = by_pair.get(tuple(sorted((a, b))))
                cells.append('<td title="null/not_applicable">—</td>' if a == b else
                    f'<td><a href="#{item["pair_id"]}" title="{escape(item[channel]["status"])}">{display_value(item[channel])}</a></td>')
            matrix_rows.append(f'<tr><th>{aliases[a]}</th>{"".join(cells)}</tr>')
        matrices.append(f'<h2>{channel} (m)</h2><div class="scroll"><table class="matrix"><tr><th></th>{"".join("<th>"+aliases[a]+"</th>" for a in ids)}</tr>{"".join(matrix_rows)}</table></div>')
    mapping = "".join(f'<tr><th>{alias}</th><td>{escape(identity)}</td></tr>' for identity, alias in aliases.items())
    states = Counter(item["centroid_free_space_hybrid"]["status"] for item in observations)
    state_summary = ", ".join(f"{status}={count}" for status, count in sorted(states.items()))
    data = json.dumps({"observations": observations, "bounds": view_bounds(geometry), "aliases": aliases, "spacing": manifest["grid"]["spacing"]}, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
    script = r"""
const data=JSON.parse(document.getElementById('data').textContent);
const byId=new Map(data.observations.map(o=>[o.pair_id,o]));
const picker=document.getElementById('pair'); const overlay=document.getElementById('overlay');
const viewer=document.getElementById('view'); const ns='http://www.w3.org/2000/svg';
/** Draw only a recorded point sequence; no distance or route inference. */
function line(points,color,width,dash){const e=document.createElementNS(ns,'polyline');e.setAttribute('points',points.map(p=>p[0]+','+(-p[1])).join(' '));e.setAttribute('fill','none');e.setAttribute('stroke',color);e.setAttribute('stroke-width',width);if(dash)e.setAttribute('stroke-dasharray',dash);overlay.append(e);}
/** Show the recorded free access cell, shared edge and midpoint proxy. */
function accessMarker(access,color){const [x,y]=access.cell_center,s=data.spacing;let square=document.createElementNS(ns,'rect');for(const [key,value] of Object.entries({x:x-s/2,y:-y-s/2,width:s,height:s,fill:'none',stroke:color,'stroke-width':.045}))square.setAttribute(key,value);overlay.append(square);line(access.shared_edge,'#16a34a',.065);let proxy=document.createElementNS(ns,'circle');for(const [key,value] of Object.entries({cx:access.proxy_point[0],cy:-access.proxy_point[1],r:.055,fill:color}))proxy.setAttribute(key,value);overlay.append(proxy);}
/** Display one stored observation and its fixed endpoints. */
function show(){const o=byId.get(location.hash.slice(1))||data.observations.find(o=>o.route)||data.observations[0];picker.value=o.pair_id;overlay.replaceChildren();
const audits=o.group_ids.map(id=>o.geometry_audit[id]);let points=audits.filter(a=>a.centroid).map(a=>a.centroid);
if(points.length===2){line(points,'#737373',.035);points.forEach((p,i)=>{let e=document.createElementNS(ns,'circle');e.setAttribute('cx',p[0]);e.setAttribute('cy',-p[1]);e.setAttribute('r',.065);e.setAttribute('fill',i?'#be123c':'#1d4ed8');overlay.append(e);});}
const r=o.route;if(r){line(r.points,'#dc2626',.065);for(const [centroid,access,color] of [[r.source_centroid,r.source_access,'#1d4ed8'],[r.target_centroid,r.target_access,'#be123c']]){line([centroid,access.proxy_point,access.cell_center],'#7c3aed',.045,'.1 .07');accessMarker(access,color);}points.push(...r.points);}
let bounds=data.bounds;if(document.getElementById('zoom').checked&&points.length){let xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);let x=Math.min(...xs)-.8,y=Math.min(...ys)-.8,w=Math.max(...xs)-x+.8,h=Math.max(...ys)-y+.8;bounds=[x,-y-h,Math.max(w,1.6),Math.max(h,1.6)];}viewer.setAttribute('viewBox',bounds.join(' '));
document.getElementById('summary').textContent=o.group_ids.map(id=>data.aliases[id]+' '+id).join(' ↔ ')+' | Euclidean '+(o.center_to_center_euclidean.value??'null')+' m | Hybrid '+(o.centroid_free_space_hybrid.value??'null')+' m | '+o.centroid_free_space_hybrid.status+' | '+(o.centroid_free_space_hybrid.reason||'');
document.getElementById('details').textContent=JSON.stringify({pair_id:o.pair_id,euclidean:o.center_to_center_euclidean,hybrid:o.centroid_free_space_hybrid,geometry_audit:o.geometry_audit,route:r?{source_access:r.source_access,target_access:r.target_access,cell_count:r.cell_keys.length,arithmetic:r.arithmetic}:null},null,2);}
picker.onchange=()=>{location.hash=picker.value;};window.onhashchange=show;document.getElementById('zoom').onchange=show;show();
"""
    candidate = escape(domain_candidate_id(geometry["domain"]))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>IFC group distance · {candidate}</title>
<style>body{{font:14px system-ui;margin:20px;color:#172033}}select{{max-width:90%;padding:8px}}svg{{width:100%;height:700px;background:#fff;border:1px solid #bbb}}table{{border-collapse:collapse}}td,th{{padding:5px;border:1px solid #ddd;text-align:right}}.scroll{{overflow:auto}}.matrix{{font-size:10px}}pre{{overflow:auto;max-height:400px;background:#f1f5f9;padding:12px}}#summary{{overflow-wrap:anywhere}}a{{color:#075985}}</style>
<h1>IFC group distance · confirmed {candidate} camera plane</h1><p>37 authored groups · 666 unordered pairs · metres · {manifest["grid"]["spacing"]} m cells · four-neighbor discrete approximation. Matrix diagonal: null/not_applicable.</p>
<p>Observed hybrid states: {state_summary}. Recorded routes: {sum(item["route"] is not None for item in observations)}. Source/domain combinations without a route retain their status and null hybrid distance.</p>
<p>Green: {candidate} domain. Gray fill: physical occupancy. Orange: unknown. Purple fill: conditional. Cyan outlines: authored groups. Gray straight line: fixed centroid Euclidean distance. Red: recorded free-cell route. Purple dashed: endpoint offsets; these are distinct from the free-space route. Blue/rose squares: source/target access cells; green shared edges and dot proxies mark their recorded interfaces.</p>
<label>Pair <select id="pair">{"".join(options)}</select></label> <label><input type="checkbox" id="zoom">Fit selected pair</label><p id="summary"></p>
<svg id="view" xmlns="http://www.w3.org/2000/svg" viewBox="{' '.join(map(str, view_bounds(geometry)))}">{base}<g id="overlay"></g></svg>
<details><summary>Selected pair audit</summary><pre id="details"></pre></details>
<h2>Complete unordered pair list</h2><table><tr><th>Pair / route locator</th><th>Euclidean (m)</th><th>Hybrid (m)</th><th>Hybrid status</th></tr>{"".join(rows)}</table>
{"".join(matrices)}<h2>Group identifiers</h2><table>{mapping}</table>
<p>Source SHA-256: {manifest["source_identity"]["sha256"]}. User visual review pending. No-route pairs remain selectable and have no invented route.</p>
<script type="application/json" id="data">{data}</script><script>{script}</script></html>'''


def representative_png(output: Path, geometry: dict, manifest: dict, observations: list, aliases: dict) -> list[str]:
    """Plot two recorded representative observations with installed Matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    selected = [max((o for o in observations if o["route"]), key=lambda o: len(o["route"]["cell_keys"]), default=observations[0])]
    selected.append(max((o for o in observations if o["route"] is None and o["pair_id"] != selected[0]["pair_id"]), key=lambda o: o["center_to_center_euclidean"]["value"] or -1, default=observations[-1]))
    paths = []
    for index, observation in enumerate(selected, 1):
        figure, axes = plt.subplots(figsize=(12, 9))
        for record, color, alpha in [(geometry["domain"], "#d9f0d9", 1)]:
            for component in record["components"]:
                axes.add_patch(Patch(component["exterior"], facecolor=color, edgecolor="#238543", alpha=alpha))
        for record in geometry["physical_occupancy"]:
            for component in record["geometry_components"]:
                axes.add_patch(Patch(component["exterior"], facecolor="#64748b", alpha=.45))
                for hole in component.get("holes", ()):
                    axes.add_patch(Patch(hole, facecolor="white"))
        for component in geometry["domain"]["components"]:
            axes.add_patch(Patch(component["exterior"], facecolor="none", edgecolor="#238543", linewidth=2))
        domain_points = [p for component in geometry["domain"]["components"] for p in component["exterior"]]
        axes.text(min(p[0] for p in domain_points)+.12, max(p[1] for p in domain_points)-.3,
                  domain_candidate_id(geometry["domain"]) + " confirmed domain", color="#166534", fontsize=10)
        spacing = manifest["grid"]["spacing"]
        for sample in manifest["cell_samples"]:
            if sample["status"] in {"unknown", "conditional"}:
                x, y = sample["center"]
                axes.add_patch(plt.Rectangle((x-spacing/2,y-spacing/2),spacing,spacing, facecolor="#f59e0b" if sample["status"] == "unknown" else "#a855f7",alpha=.25))
        for group in geometry["groups"]:
            for component in group.get("components") or ():
                axes.add_patch(Patch(component["exterior"], facecolor="none", edgecolor="#0891b2", linewidth=.5))
        points = [observation["geometry_audit"][identity]["centroid"] for identity in observation["group_ids"] if "centroid" in observation["geometry_audit"][identity]]
        if len(points) == 2:
            axes.plot(*zip(*points), color="#737373", marker="o", label="fixed centroid Euclidean")
            for identity, point in zip(observation["group_ids"], points):
                axes.annotate(aliases[identity], point, xytext=(5,5), textcoords="offset points")
        route = observation["route"]
        if route:
            axes.plot(*zip(*route["points"]), color="#dc2626", linewidth=2, label="free-cell route")
            for centroid, access, color in ((route["source_centroid"], route["source_access"], "#1d4ed8"), (route["target_centroid"], route["target_access"], "#be123c")):
                axes.plot(*zip(centroid, access["proxy_point"], access["cell_center"]), color="#7c3aed", linestyle="--", label="endpoint offset")
                x, y = access["cell_center"]
                axes.add_patch(plt.Rectangle((x-spacing/2, y-spacing/2), spacing, spacing, facecolor="none", edgecolor=color, linewidth=2, label="access cell"))
                axes.plot(*zip(*access["shared_edge"]), color="#16a34a", linewidth=3, label="shared edge")
                axes.scatter(*access["proxy_point"], color=color, marker="o", s=30, label="proxy")
            points.extend(route["points"])
        if route and points:
            axes.set_xlim(min(p[0] for p in points)-.8,max(p[0] for p in points)+.8)
            axes.set_ylim(min(p[1] for p in points)-.8,max(p[1] for p in points)+.8)
        else:
            x, negative_y, width, height = view_bounds(geometry)
            axes.set_xlim(x, x + width)
            axes.set_ylim(-negative_y-height, -negative_y)
        axes.set_aspect("equal")
        axes.set_xlabel("camera-plane X + view offset (m)")
        axes.set_ylabel("camera-plane Y + view offset (m)")
        hybrid = observation["centroid_free_space_hybrid"]
        axes.set_title(f'{" ↔ ".join(aliases[i] for i in observation["group_ids"])} · {hybrid["status"]}\nEuclidean {display_value(observation["center_to_center_euclidean"])} m · hybrid {display_value(hybrid)} m · grid {spacing} m')
        axes.legend(loc="upper right")
        figure.tight_layout()
        path = output / f"representative_{index:02d}.png"
        figure.savefig(path, dpi=140)
        plt.close(figure)
        paths.append(path.name)
    return paths


def render(run_dir: Path, output: Path) -> dict:
    """Reconcile every stored pair with one readable indexed route view."""
    if output.resolve() != (run_dir / "preview").resolve():
        raise ValueError("use RUN_DIR/preview to preserve the published pair locators")
    output.mkdir(parents=True, exist_ok=False)
    manifest, observations = read_json(run_dir / "run_manifest.json"), read_json(run_dir / "observations.json")
    geometry, index = read_json(run_dir / "scene_geometry.json"), read_json(run_dir / "pair_index.json")
    expected = set(manifest["expected_pair_ids"])
    if len(observations) != len(expected) or len(index) != len(expected) or {item["pair_id"] for item in observations} != expected or {item["pair_id"] for item in index} != expected:
        raise ValueError("renderer pair scope is not the manifest bijection")
    coverage = read_json(run_dir / "coverage_report.json")
    for name, checksum in coverage["output_hashes"].items():
        if file_hash(run_dir / name) != checksum:
            raise ValueError(f"runner output changed before rendering: {name}")
    aliases = {identity: f"G{number:02d}" for number, identity in enumerate(manifest["group_ids"], 1)}
    base = base_svg(geometry, manifest, aliases)
    (output / "index.html").write_text(html_document(manifest, observations, geometry, aliases, base), encoding="utf-8")
    (output / "source_plan.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="{" ".join(map(str, view_bounds(geometry)))}">{base}</svg>', encoding="utf-8")
    with (output / "distance_rows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("pair_id", "group_a", "group_b", "euclidean_m", "euclidean_status", "hybrid_m", "hybrid_status", "route_locator"))
        for item in observations:
            writer.writerow((item["pair_id"], *item["group_ids"], item["center_to_center_euclidean"]["value"], item["center_to_center_euclidean"]["status"],
                             item["centroid_free_space_hybrid"]["value"], item["centroid_free_space_hybrid"]["status"], "index.html#" + item["pair_id"]))
    pngs = representative_png(output, geometry, manifest, observations, aliases)
    locators = [{"pair_id": item["pair_id"], "observation_locator": item["observation_locator"], "route_view_locator": "index.html#" + item["pair_id"]} for item in index]
    write_json(output / "pair_views.json", locators)
    html = (output / "index.html").read_text(encoding="utf-8")
    if any(f'value="{identity}"' not in html or f'href="#{identity}"' not in html for identity in expected):
        raise ValueError("an expected pair has no selectable route locator")
    view_report = {"pair_set_bijection": True, "locator_count": len(locators), "pair_ids": sorted(expected), "distance_recomputed": False,
                   "representative_pngs": pngs, "user_visual_review": "pending", "output_hashes": {path.name: file_hash(path) for path in output.iterdir() if path.is_file()}}
    write_json(output / "coverage_report.json", view_report)
    relative_html = (output / "index.html").relative_to(run_dir).as_posix() if output.is_relative_to(run_dir) else None
    if relative_html is None or any(item["route_view_locator"] != relative_html + "#" + item["pair_id"] for item in index):
        raise ValueError("preview location differs from the runner's published locators; use RUN_DIR/preview")
    coverage.update(route_view_count=len(locators), route_view_pair_set_bijection=True, readable_locators=True,
                    preview_coverage_report=str((output / "coverage_report.json").resolve()))
    write_json(run_dir / "coverage_report.json", coverage)
    return {"preview": str((output / "index.html").resolve()), "locator_count": len(locators), "representative_pngs": pngs}


def main() -> None:
    """Render an existing complete package into its published preview location."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.run_dir, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
