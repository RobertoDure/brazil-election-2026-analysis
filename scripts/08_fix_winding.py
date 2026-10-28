
from pathlib import Path
import json, glob, os
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient

def fix(path):
    gj = json.load(open(path))
    for f in gj["features"]:
        g = shape(f["geometry"])
        if g.geom_type in ("Polygon", "MultiPolygon"):
            g = orient(g, -1.0)  # GeoJSON/Plotly expect clockwise exterior rings
        f["geometry"] = mapping(g)
    json.dump(gj, open(path, "w"), separators=(",", ":"))
    return len(gj["features"])

for p in sorted(glob.glob(str(Path(__file__).resolve().parents[1] / "data" / "geo" / "simp" / "*.geojson"))):
    n = fix(p)
    print(os.path.basename(p), n, os.path.getsize(p)//1024, "KB")
