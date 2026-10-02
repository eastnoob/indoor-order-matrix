"""Reproduce the bounded polygon source-versus-center-sampling comparison."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, sys, time
from pathlib import Path
from shapely import Point, affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

RESOLUTIONS=(1.0,0.5,0.25,0.125)
ORIGINS=((0.0,0.0),(0.23,0.17))

def component_count(geometry):
    if geometry.is_empty: return 0
    return len(geometry.geoms) if hasattr(geometry,'geoms') else 1

def sample_polygon(geometry, step, origin):
    left, top, right, bottom=geometry.bounds; ox,oy=origin
    cells=[]; ix0=math.floor((left-ox)/step-0.5); ix1=math.ceil((right-ox)/step-0.5)
    iy0=math.floor((top-oy)/step-0.5); iy1=math.ceil((bottom-oy)/step-0.5)
    for iy in range(iy0,iy1+1):
        for ix in range(ix0,ix1+1):
            point=Point(ox+(ix+0.5)*step,oy+(iy+0.5)*step)
            if geometry.covers(point): cells.append((ix,iy))
    remaining=set(cells); components=[]
    while remaining:
        start=remaining.pop(); comp={start}; stack=[start]
        while stack:
            ix,iy=stack.pop()
            for neighbor in ((ix-1,iy),(ix+1,iy),(ix,iy-1),(ix,iy+1)):
                if neighbor in remaining: remaining.remove(neighbor); comp.add(neighbor); stack.append(neighbor)
        components.append(comp)
    return {'sampled_area':len(cells)*step*step,'sampled_components':len(components),'cell_count':len(cells)}

def fixtures():
    """Return only the repaired closed/open wall pair."""
    closed=box(0,0,6,4).difference(box(2.5,0,3.5,4))
    yield {'id':'closed_wall','geometry':closed,'source_area':20.0,'source_components':2,'opening_width':0.0,'notes':'closed full-height wall'}
    wall=box(2.5,0,3.5,4); opening=box(2.5,1.5,3.5,2.5)
    opened=box(0,0,6,4).difference(wall.difference(opening))
    yield {'id':'open_wall','geometry':opened,'source_area':21.0,'source_components':1,'opening_width':1.0,'notes':'positive-area opening through full-height wall'}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',type=Path,required=True); args=parser.parse_args(); out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter(); rows=[]
    for fixture in fixtures():
        for step in RESOLUTIONS:
            for origin in ORIGINS:
                sampled=sample_polygon(fixture['geometry'],step,origin)
                rows.append({'fixture':fixture['id'],'resolution':step,'origin':origin,**sampled})
    report={'schema':'space-field-polygon-baseline-v2','date':'2026-10-01','runtime':{'python':sys.version,'platform':platform.platform(),'elapsed_seconds':round(time.perf_counter()-started,6)},'geometry_backend':{'name':'Shapely','version':'2.1.2','source_polygon_boolean':'exact_for_constructed_polygons','sampled_connectivity':'center-point plus four-neighbor lattice'},'resolutions':RESOLUTIONS,'origins':ORIGINS,'fixtures':[{'id':f['id'],'source_area':f['source_area'],'source_components':f['source_components'],'opening_width':f.get('opening_width'),'notes':f['notes']} for f in fixtures()],'runs':rows,'limitations':['sampled rows are not exact topology guarantees','synthetic units are coordinate units; no production resolution or role threshold']}
    result=out/'polygon_baseline_results.json'; result.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    manifest={'schema':'space-field-polygon-baseline-manifest-v1','command':'pixi run python scripts/design/space_field/run_polygon_baseline.py --output-dir <dir>','runner':'scripts/design/space_field/run_polygon_baseline.py','runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'result_sha256':hashlib.sha256(result.read_bytes()).hexdigest(),'seed':None,'units':'synthetic coordinate units','resolutions':RESOLUTIONS,'origins':ORIGINS}
    (out/'polygon_baseline_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps({'result':'pass','result_path':str(result),'sha256':manifest['result_sha256']}))
if __name__=='__main__': main()
