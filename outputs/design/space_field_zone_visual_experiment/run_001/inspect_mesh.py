
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import ifcopenshell, ifcopenshell.geom
from adapters.ifc_bonsai import _native_length_unit, _native_mesh_record, _native_source_id
p=Path("outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc")
f=ifcopenshell.open(str(p)); units,scale,*_= _native_length_unit(f)
g=next(x for x in f.by_type("IfcGroup") if getattr(x,"ObjectType",None)=="furniture_group")
e=next(iter(next(iter(getattr(g,"IsGroupedBy",()) or ())).RelatedObjects))
r=next(r for r in getattr(e.Representation,"Representations",()) if r.RepresentationIdentifier=="Analysis")
m,u=_native_mesh_record(e,f"{_native_source_id(e)}:analysis",units,ifcopenshell,r)
out={"units":units,"mesh":None if m is None else m.to_dict(),"uncertainty":None if u is None else u.to_dict()}
print(json.dumps(out,indent=2,default=str))

