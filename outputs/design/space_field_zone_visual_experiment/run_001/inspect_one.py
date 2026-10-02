
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import ifcopenshell, ifcopenshell.geom
from adapters.ifc_bonsai import _native_source_id
p=Path("outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc")
f=ifcopenshell.open(str(p))
g=next(x for x in f.by_type("IfcGroup") if getattr(x,"ObjectType",None)=="furniture_group")
rel=next(iter(getattr(g,"IsGroupedBy",()) or ()))
e=next(iter(getattr(rel,"RelatedObjects",()) or ()))
out={"group":_native_source_id(g),"member":_native_source_id(e),"class":e.is_a(),"reprs":[]}
for r in getattr(getattr(e,"Representation",None),"Representations",()) or ():
  out["reprs"].append({"id":r.id(),"identifier":getattr(r,"RepresentationIdentifier",None),"type":getattr(r,"RepresentationType",None),"items":len(getattr(r,"Items",()) or ())})
for name in ["Analysis","Body"]:
  r=next((r for r in getattr(getattr(e,"Representation",None),"Representations",()) or () if getattr(r,"RepresentationIdentifier",None)==name),None)
  try:
    s=ifcopenshell.geom.settings(); s.set(s.USE_WORLD_COORDS,True)
    sh=ifcopenshell.geom.create_shape(s,e,r) if r else None
    out[name]={"ok":bool(sh),"verts":len(sh.geometry.verts) if sh else 0,"faces":len(sh.geometry.faces) if sh else 0}
  except Exception as ex:
    out[name]={"error":repr(ex)}
print(json.dumps(out,indent=2))

