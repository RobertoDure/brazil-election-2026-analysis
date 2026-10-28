
from pathlib import Path
import json, os, unicodedata, zipfile, duckdb, pandas as pd
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient

ROOT = str(Path(__file__).resolve().parents[1]); GEO=f"{ROOT}/data/geo"; OUT=f"{ROOT}/data/cache"
os.makedirs(f"{GEO}/simp", exist_ok=True)

# ---------- candidate registry ----------
consulta_dir = Path(f"{ROOT}/data/source/consulta")
consulta_dir.mkdir(parents=True, exist_ok=True)
zip_path = Path(f"{ROOT}/data/source/consulta_cand_2026.zip")
existing = sorted(consulta_dir.glob("*.csv"))
if not existing:
    if not zip_path.exists():
        raise SystemExit(
            "No candidate registry found (neither data/source/consulta/*.csv nor\n"
            "data/source/consulta_cand_2026.zip).\n"
            "Run Step 0 of 00_data_preprocessing_validation.ipynb (it downloads consulta_cand_2026)."
        )
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.endswith(".csv"):
                with z.open(n) as src, open(consulta_dir / n, "wb") as dst:
                    dst.write(src.read())
if not Path(f"{GEO}/municipios_ibge.json").exists():
    raise SystemExit(
        "data/geo/municipios_ibge.json is missing.\n"
        "Run Step 0 of 00_data_preprocessing_validation.ipynb (it downloads the IBGE meshes)."
    )

con = duckdb.connect(); con.execute("SET memory_limit='2GB'; SET threads=4")
opts = "delim=';', header=true, encoding='latin-1', all_varchar=true, quote='\"'"
con.execute(f"""
COPY (
 SELECT SG_UF, NM_UE, CAST(CD_CARGO AS INT) CD_CARGO, DS_CARGO, SQ_CANDIDATO, NR_CANDIDATO,
        NM_CANDIDATO, NM_URNA_CANDIDATO, NR_PARTIDO, SG_PARTIDO, NM_PARTIDO, TP_AGREMIACAO,
        NM_FEDERACAO, SG_FEDERACAO, DS_COMPOSICAO_FEDERACAO, NM_COLIGACAO,
        DS_GENERO, DS_GRAU_INSTRUCAO, DS_ESTADO_CIVIL, DS_COR_RACA, DS_OCUPACAO,
        TRY_STRPTIME(DT_NASCIMENTO, '%d/%m/%Y')::DATE DT_NASCIMENTO, DS_SIT_TOT_TURNO
 FROM read_csv('{ROOT}/data/source/consulta/consulta_cand_2026_*.csv', {opts}, union_by_name=true)
 WHERE SG_UF <> 'BRASIL'
) TO '{OUT}/cand_registry.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)""")
print("registry", con.execute(f"SELECT count(*), count(DISTINCT SQ_CANDIDATO) FROM '{OUT}/cand_registry.parquet'").fetchall())

# ---------- municipality crosswalk ----------
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s).upper()
    return " ".join(s.split())

ibge = json.load(open(f"{GEO}/municipios_ibge.json"))
rows = []
for m in ibge:
    try: uf = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
    except Exception: uf = m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
    rows.append({"CD_IBGE": str(m["id"]), "UF": uf, "NOME_IBGE": m["nome"], "NORM": norm(m["nome"])})
ibge_df = pd.DataFrame(rows)

tse = con.execute(f"""SELECT DISTINCT SG_UF, LPAD(CD_MUNICIPIO,5,'0') CD_TSE, NM_MUNICIPIO FROM '{OUT}/detalhe_mun.parquet' WHERE SG_UF NOT IN ('ZZ')""").df()
tse["NORM"] = tse["NM_MUNICIPIO"].map(norm)
print("TSE municipalities:", len(tse), "IBGE:", len(ibge_df))

# merge; handle duplicates by name within UF
ibge_df["dup"] = ibge_df.groupby(["UF","NORM"])["CD_IBGE"].transform("count")
merged = tse.merge(ibge_df[["UF","NORM","CD_IBGE","NOME_IBGE","dup"]], left_on=["SG_UF","NORM"], right_on=["UF","NORM"], how="left")
merged["match"] = merged["CD_IBGE"].notna()
print("unmatched:", (~merged.match).sum())
print(merged[~merged.match][["SG_UF","CD_TSE","NM_MUNICIPIO"]].to_string())
print("dups:", (merged.dup>1).sum())
merged.to_parquet(f"{OUT}/crosswalk.parquet", index=False)

# ---------- simplified geojson ----------
UFS = {"AC":12,"AL":27,"AP":16,"AM":13,"BA":29,"CE":23,"DF":53,"ES":32,"GO":52,"MA":21,"MT":51,
       "MS":50,"MG":31,"PA":15,"PB":25,"PR":41,"PE":26,"PI":22,"RJ":33,"RN":24,"RS":43,"RO":11,
       "RR":14,"SC":42,"SP":35,"SE":28,"TO":17}
def simp_geom(g, tol):
    s = shape(g)
    try: s = s.buffer(0)
    except Exception: pass
    s = s.simplify(tol, preserve_topology=True)
    s = orient(s, -1.0)
    d = mapping(s)
    def rnd(c):
        if isinstance(c[0], (int,float)): return [round(c[0],4), round(c[1],4)]
        return [rnd(x) for x in c]
    d["coordinates"] = rnd(d["coordinates"])
    return d

cen = []
for uf, code in UFS.items():
    gj = json.load(open(f"{GEO}/mun_{uf}.geojson"))
    feats = []
    for f in gj["features"]:
        ca = f["properties"].get("codarea") or f["id"]
        g = simp_geom(f["geometry"], 0.006)
        feats.append({"type":"Feature","properties":{"codarea":str(ca)}, "geometry": g})
        c = shape(f["geometry"]).representative_point()
        cen.append({"CD_IBGE":str(ca), "UF":uf, "lon":round(c.x,4), "lat":round(c.y,4)})
    json.dump({"type":"FeatureCollection","features":feats}, open(f"{GEO}/simp/mun_{uf}.geojson","w"))
    print(uf, len(feats), os.path.getsize(f"{GEO}/simp/mun_{uf}.geojson")//1024, "KB")

gj = json.load(open(f"{GEO}/brasil_uf.geojson"))
feats = []
for f in gj["features"]:
    ca = str(f["properties"].get("codarea") or f["id"])
    feats.append({"type":"Feature","properties":{"codarea":ca}, "geometry": simp_geom(f["geometry"], 0.01)})
json.dump({"type":"FeatureCollection","features":feats}, open(f"{GEO}/simp/brasil_uf.geojson","w"))
print("brasil", len(feats), os.path.getsize(f"{GEO}/simp/brasil_uf.geojson")//1024, "KB")
pd.DataFrame(cen).to_parquet(f"{OUT}/centroids.parquet", index=False)
