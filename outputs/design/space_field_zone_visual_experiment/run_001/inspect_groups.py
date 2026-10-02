
import sys, json, math
from pathlib import Path
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
import ifcopenshell
import ifcopenshell.geom
from adapters.ifc_bonsai import _native_length_unit, _native_mesh_record, _native_source_id
from shapely.geometry import MultiPoint
from shapely.ops import unary_union

source_path=ROOT/"outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
source=ifcopenshell.open(str(source_path))
units,scale,explicit,meta=_native_length_unit(source)
def rep(e,name):
    pr=getattr(e,"Representation",None)
    return next((r for r in getattr(pr,"Representations",()) or () if getattr(r,"RepresentationIdentifier",None)==name),None)
def mesh(e,name):
    r=rep(e,name)
    if r is None:return None
    m,u=_native_mesh_record(e,f"{_native_source_id(e)}:{name.lower()}",units,ifcopenshell,r)
    return m
def poly(m):
    pts=[(float(v[0]),float(v[1])) for v in m.vertices]
    return MultiPoint(pts).convex_hull if len(pts)>=3 else None
groups=[]
for g in source.by_type("IfcGroup"):
    if getattr(g,"ObjectType",None)!="furniture_group": continue
    members=[]
    for rel in getattr(g,"IsGroupedBy",()) or ():
        members += list(getattr(rel,"RelatedObjects",()) or ())
    mpolys=[]; zs=[]; ms=[]
    for e in members:
        m=mesh(e,"Analysis") or mesh(e,"Body")
        if m:
            p=poly(m)
            if p and not p.is_empty:
                mpolys.append(p); ms.append((e,m,p))
                zs += [float(v[2]) for v in m.vertices]
    geom=unary_union(mpolys) if mpolys else None
    c=geom.centroid if geom else None
    groups.append({"id":_native_source_id(g),"name":getattr(g,"Name",None),"member_count":len(members),"usable":len(ms),
                   "area":float(geom.area) if geom else None,"centroid":[float(c.x),float(c.y)] if c else None,
                   "bounds":list(map(float,geom.bounds)) if geom else None,
                   "z":[min(zs),max(zs)] if zs else None})
groups.sort(key=lambda x:x["id"])
pairs=[]
for i,a in enumerate(groups):
  for b in groups[i+1:]:
    if not a["centroid"] or not b["centroid"]: continue
    pa=MultiPoint([(a["bounds"][0],a["bounds"][1]),(a["bounds"][0],a["bounds"][3]),(a["bounds"][2],a["bounds"][1]),(a["bounds"][2],a["bounds"][3])]).convex_hull
    pb=MultiPoint([(b["bounds"][0],b["bounds"][1]),(b["bounds"][0],b["bounds"][3]),(b["bounds"][2],b["bounds"][1]),(b["bounds"][2],b["bounds"][3])]).convex_hull
    gap=float(pa.distance(pb))
    cd=math.dist(a["centroid"],b["centroid"])
    pairs.append({"a":a["id"],"b":b["id"],"gap":gap,"centroid_distance":cd,"norm_gap":gap/max(math.sqrt(min(a["area"],b["area"])),1e-9),
                   "overlap":float(pa.intersection(pb).area)>1e-9})
print(json.dumps({"units": {"token":units,"scale":scale},"groups":groups,"pairs":sorted(pairs,key=lambda x:x["gap"])},indent=2))

