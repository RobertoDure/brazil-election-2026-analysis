
from pathlib import Path
import json, unicodedata, pandas as pd, duckdb
ROOT = str(Path(__file__).resolve().parents[1]); OUT=f"{ROOT}/data/cache"
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s).upper()
    return " ".join(s.split())

ib = []
for m in json.load(open(f"{ROOT}/data/geo/municipios_ibge.json")):
    uf = m['microrregiao']['mesorregiao']['UF']['sigla'] if m.get('microrregiao') else m['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
    ib.append({"CD_IBGE": str(m["id"]), "UF": uf, "NOME_IBGE": m["nome"], "NORM": norm(m["nome"])})
ibd = pd.DataFrame(ib)

con = duckdb.connect(); con.execute("SET memory_limit='2GB'")
tse = con.execute(f"""SELECT DISTINCT SG_UF, LPAD(CD_MUNICIPIO,5,'0') CD_TSE, NM_MUNICIPIO
                      FROM '{OUT}/detalhe_mun.parquet'""").df()
tse["NORM"] = tse["NM_MUNICIPIO"].map(norm)

ALIAS = {("RO","00337"):"1100346", ("RO","00256"):"1100098", ("RR","03158"):"1400605",
         ("PA","04120"):"1502954", ("RN","17035"):"2405306", ("SE","31011"):"2800100",
         ("MG","41092"):"3105509", ("MG","44571"):"3122900", ("MG","53031"):"3165206",
         ("SP","71013"):"3550001", ("PR","77119"):"4116307", ("MT","91553"):"5107800",
         ("GO","92690"):"5203500"}
ibd["key"] = ibd["UF"] + "|" + ibd["NORM"]
tse["key"] = tse["SG_UF"] + "|" + tse["NORM"]
m = tse.merge(ibd[["key","CD_IBGE","NOME_IBGE"]], on="key", how="left")
m["CD_IBGE"] = [ALIAS.get((u,c), b) for u,c,b in zip(m.SG_UF, m.CD_TSE, m.CD_IBGE)]
m["NOME_IBGE"] = m["CD_IBGE"].map(ibd.set_index("CD_IBGE")["NOME_IBGE"])
assert m.CD_IBGE.notna().all(), m[m.CD_IBGE.isna()]
assert m.CD_IBGE.is_unique, "not bijective"
assert len(m) == len(ibd), (len(m), len(ibd))
m.drop(columns=["key","NORM"]).to_parquet(f"{OUT}/crosswalk.parquet", index=False)
print("crosswalk ok:", len(m), "municipalities, unique IBGE codes:", m.CD_IBGE.nunique())
print(m.head(3).to_string())
