
from pathlib import Path
import json, glob, os
from shapely.geometry import shape, mapping
ROOT = str(Path(__file__).resolve().parents[1]); GEO=f"{ROOT}/data/geo/simp"
feats=[]
def rnd(c, nd=4):
    if isinstance(c[0], (int,float)): return [round(c[0],nd), round(c[1],nd)]
    return [rnd(x,nd) for x in c]
for f in sorted(glob.glob(f"{GEO}/mun_*.geojson")):
    gj = json.load(open(f))
    for ft in gj["features"]:
        g = shape(ft["geometry"]).simplify(0.012, preserve_topology=True)
        feats.append({"type":"Feature","properties":{"codarea":ft["properties"]["codarea"]},
                      "geometry":{"type":"Polygon","coordinates":rnd(mapping(g)["coordinates"])} if g.geom_type=="Polygon" else {"type":"MultiPolygon","coordinates":rnd(mapping(g)["coordinates"])}})
out={"type":"FeatureCollection","features":feats}
p=f"{GEO}/brasil_mun.geojson"
json.dump(out, open(p,"w"), separators=(",",":"))
print(len(feats), os.path.getsize(p)//1024, "KB")
